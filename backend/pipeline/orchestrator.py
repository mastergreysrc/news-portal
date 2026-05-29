"""Pipeline orchestrator — runs the full collect → process → store flow."""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Optional

import aiosqlite
from database import get_db
from config import get_settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Category & source seeding
# ---------------------------------------------------------------------------

async def ensure_categories_and_sources(db: aiosqlite.Connection) -> None:
    """Seed categories and sources from config.yaml into DB if missing."""
    settings = get_settings()

    for cat in settings.categories:
        # Upsert category
        cursor = await db.execute(
            "SELECT id FROM categories WHERE slug = ?",
            (cat.slug,),
        )
        row = await cursor.fetchone()
        if row:
            category_id = row[0]
        else:
            cursor = await db.execute(
                "INSERT INTO categories (name, slug, icon) VALUES (?, ?, ?)",
                (cat.name, cat.slug, cat.icon),
            )
            category_id = cursor.lastrowid

        # Upsert sources
        for src in cat.sources:
            cursor = await db.execute(
                "SELECT id FROM sources WHERE category_id = ? AND type = ? AND name = ?",
                (category_id, src.type, src.name),
            )
            row = await cursor.fetchone()
            if not row:
                await db.execute(
                    """INSERT INTO sources (category_id, type, name, config)
                       VALUES (?, ?, ?, ?)""",
                    (category_id, src.type, src.name, json.dumps(src.config)),
                )

    await db.commit()


async def get_sources_for_category(
    db: aiosqlite.Connection, slug: str
) -> list[dict]:
    """Get all enabled sources for a category."""
    cursor = await db.execute(
        """SELECT s.*, c.id as cat_id, c.name as cat_name
           FROM sources s
           JOIN categories c ON c.id = s.category_id
           WHERE c.slug = ? AND s.enabled = 1""",
        (slug,),
    )
    return [dict(row) for row in await cursor.fetchall()]


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

async def run_pipeline(category_slug: str = "gaming") -> dict:
    """
    Run the full collection pipeline for a category.

    Phases:
      1. Seed categories/sources from config
      2. Collect raw items from all enabled sources (concurrently)
      3. For each item: normalize URL, check duplicates, translate,
         score, insert, cluster
      4. Log the collection run

    Returns a summary dict with keys:
      items_fetched, items_new, items_duplicate, status, [error]
    """
    from collectors import COLLECTOR_REGISTRY
    from .normalizer import normalize_url
    from .deduplicator import find_duplicate
    from .translator import translate_and_summarize
    from .clusterer import create_singleton_cluster, add_to_cluster

    settings = get_settings()
    started_at = datetime.now(timezone.utc).isoformat()

    db: Optional[aiosqlite.Connection] = None
    try:
        db = await get_db()

        # ---- Phase 0: Seed categories + sources ----
        await ensure_categories_and_sources(db)
        sources = await get_sources_for_category(db, category_slug)

        if not sources:
            logger.warning("No enabled sources for category: %s", category_slug)
            return {
                "items_fetched": 0,
                "items_new": 0,
                "items_duplicate": 0,
                "status": "no_sources",
            }

        # ---- Phase 1: Collect (all sources concurrently) ----
        collector_tasks = []

        for src_row in sources:
            collector_cls = COLLECTOR_REGISTRY.get(src_row["type"])
            if not collector_cls:
                logger.warning("No collector registered for type: %s", src_row["type"])
                continue

            # Bridge: DB row → object with .name / .config attributes
            # (collectors expect a Pydantic SourceConfig-like object)
            raw_config = src_row["config"]
            if isinstance(raw_config, str):
                raw_config = json.loads(raw_config)

            class _SourceBridge:
                pass

            src_cfg = _SourceBridge()
            src_cfg.name = src_row["name"]
            src_cfg.config = raw_config

            collector = collector_cls(src_cfg, src_row["cat_id"], src_row["cat_name"])
            collector_tasks.append(collector.collect())

        results = await asyncio.gather(*collector_tasks, return_exceptions=True)

        # Tag each collected item with its source metadata for later phases
        tagged_items: list[tuple] = []  # (RawNewsItem, source_id, category_id)
        total_fetched = 0

        for src_row, result in zip(sources, results):
            source_id = src_row["id"]
            cat_id = src_row["cat_id"]

            if isinstance(result, Exception):
                logger.error(
                    "Collector '%s' (%s) failed: %s",
                    src_row["name"], src_row["type"], result,
                )
                continue

            if not isinstance(result, list):
                continue

            total_fetched += len(result)
            for item in result:
                tagged_items.append((item, source_id, cat_id))

        logger.info(
            "Collected %d items from %d sources for category '%s'",
            total_fetched, len(collector_tasks), category_slug,
        )

        # ---- Phase 2: Process each item ----
        new_count = 0
        dup_count = 0

        for item, source_id, category_id in tagged_items:
            norm_url = normalize_url(item.url)

            # Check for duplicates (3-pass: URL, domain+slug, TF-IDF)
            existing_cluster_id: Optional[int] = None
            try:
                existing_cluster_id = await find_duplicate(
                    item.title, item.url, category_id, source_id,
                )
            except Exception as e:
                logger.warning("Dedup check failed for '%s': %s", item.title, e)

            # Translate title + generate Polish summary (single Groq call)
            title_pl, summary_pl = await translate_and_summarize(
                item.title,
                item.summary or "",
            )

            # Insert into news_items
            cursor = await db.execute(
                """INSERT OR IGNORE INTO news_items
                   (title, title_pl, summary, summary_pl, url, url_normalized,
                    source_id, category_id, published_at, popularity_raw, metadata)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    item.title,
                    title_pl,
                    item.summary or "",
                    summary_pl,
                    item.url,
                    norm_url,
                    source_id,
                    category_id,
                    item.published_at.isoformat() if item.published_at else None,
                    item.popularity_raw,
                    json.dumps(item.metadata),
                ),
            )

            if cursor.rowcount == 0:
                # Already exists (unique constraint on url_normalized + source_id)
                dup_count += 1
                continue

            news_item_id = cursor.lastrowid

            # Build item dict for clusterer (expects raw popularity — it computes
            # the score internally via compute_item_score)
            item_dict = {
                "news_item_id": news_item_id,
                "title_pl": title_pl,
                "summary_pl": summary_pl,
                "category_id": category_id,
                "popularity_raw": item.popularity_raw,
                "source_type": item.source_type,
            }

            if existing_cluster_id:
                await add_to_cluster(db, existing_cluster_id, item_dict)
                dup_count += 1
            else:
                await create_singleton_cluster(db, item_dict)
                new_count += 1

        await db.commit()

        # ---- Phase 3: Log collection run ----
        finished_at = datetime.now(timezone.utc).isoformat()
        await db.execute(
            """INSERT INTO collection_runs
               (started_at, finished_at, items_fetched, items_new, status)
               VALUES (?, ?, ?, ?, ?)""",
            (started_at, finished_at, total_fetched, new_count, "success"),
        )
        await db.commit()

        logger.info(
            "Pipeline done for '%s': %d fetched, %d new, %d duplicates",
            category_slug, total_fetched, new_count, dup_count,
        )

        return {
            "items_fetched": total_fetched,
            "items_new": new_count,
            "items_duplicate": dup_count,
            "status": "success",
        }

    except Exception as e:
        logger.exception("Pipeline failed for category '%s'", category_slug)
        # Try to log the failure if we still have a DB connection
        if db is not None:
            try:
                await db.execute(
                    """INSERT INTO collection_runs
                       (started_at, finished_at, status, error_msg)
                       VALUES (?, ?, ?, ?)""",
                    (
                        started_at,
                        datetime.now(timezone.utc).isoformat(),
                        "error",
                        str(e),
                    ),
                )
                await db.commit()
            except Exception:
                pass
        return {
            "items_fetched": 0,
            "items_new": 0,
            "items_duplicate": 0,
            "status": "error",
            "error": str(e),
        }

    finally:
        if db is not None:
            await db.close()
