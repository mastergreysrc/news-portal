"""Clustering — group raw news items into clusters (singletons or merged).

Typical call-site flow::

    from pipeline.deduplicator import find_duplicate
    from pipeline.clusterer import create_singleton_cluster, add_to_cluster

    existing_cluster_id = await find_duplicate(title, url, category_id, source_id)
    if existing_cluster_id is None:
        cluster_id = await create_singleton_cluster(db, news_item_dict)
    else:
        await add_to_cluster(db, existing_cluster_id, news_item_dict)
"""

import logging
from datetime import datetime, timezone

import aiosqlite
from database import get_db

from pipeline.scorer import compute_cluster_score, compute_item_score

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _fetch_cluster_rows(
    db: aiosqlite.Connection,
    cluster_id: int,
) -> list[aiosqlite.Row]:
    """Return all news-item rows that belong to *cluster_id*, joined with their source type."""
    cursor = await db.execute(
        """SELECT ni.title_pl, ni.summary_pl, ni.popularity_raw,
                  s.type AS source_type
           FROM cluster_items ci
           JOIN news_items ni ON ni.id = ci.news_item_id
           JOIN sources s ON s.id = ni.source_id
           WHERE ci.cluster_id = ?""",
        (cluster_id,),
    )
    return await cursor.fetchall()


async def _recalculate_cluster(db: aiosqlite.Connection, cluster_id: int) -> None:
    """Refresh popularity_score, source_count, canonical_title, and updated_at."""
    rows = await _fetch_cluster_rows(db, cluster_id)

    if not rows:
        return

    # Build the list-of-dicts expected by scorer
    items = [
        {
            "source_type": row["source_type"],
            "popularity_raw": row["popularity_raw"],
        }
        for row in rows
    ]

    score = compute_cluster_score(items)
    source_count = len(items)

    # Canonical title: pick the longest Polish title
    titles = [r["title_pl"] or "" for r in rows]
    best_title = max(titles, key=len) if titles else ""

    await db.execute(
        """UPDATE news_clusters
           SET popularity_score = ?,
               source_count = ?,
               canonical_title = ?,
               updated_at = ?
           WHERE id = ?""",
        (score, source_count, best_title, datetime.now(timezone.utc).isoformat(), cluster_id),
    )
    await db.commit()

    logger.debug(
        "Cluster %d recalculated: score=%.1f, source_count=%d",
        cluster_id, score, source_count,
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def create_singleton_cluster(
    db: aiosqlite.Connection,
    item: dict,
) -> int:
    """Create a new cluster containing a single news item.

    Parameters
    ----------
    db : aiosqlite.Connection
        An **open** connection (caller is responsible for lifecycle).
    item : dict
        Must include at least:
        - **title_pl** (str)
        - **summary_pl** (str, optional)
        - **category_id** (int)
        - **popularity_raw** (float)
        - **source_type** (str)
        - **news_item_id** (int) — the id of the already-inserted ``news_items`` row.

    Returns
    -------
    int
        The newly created ``news_clusters.id``.
    """
    # Insert the cluster row
    cursor = await db.execute(
        """INSERT INTO news_clusters (canonical_title, canonical_summary, category_id)
           VALUES (?, ?, ?)""",
        (item["title_pl"], item.get("summary_pl"), item["category_id"]),
    )
    cluster_id = cursor.lastrowid

    # Compute the initial score from the single item
    score = compute_item_score(
        item["source_type"],
        item["popularity_raw"],
    )

    await db.execute(
        "UPDATE news_clusters SET popularity_score = ?, source_count = 1 WHERE id = ?",
        (score, cluster_id),
    )

    # Link the item to the cluster
    await db.execute(
        "INSERT INTO cluster_items (cluster_id, news_item_id) VALUES (?, ?)",
        (cluster_id, item["news_item_id"]),
    )
    await db.commit()

    logger.info(
        "Created singleton cluster %d for item %d (score=%.1f)",
        cluster_id, item["news_item_id"], score,
    )
    return cluster_id


async def add_to_cluster(
    db: aiosqlite.Connection,
    cluster_id: int,
    item: dict,
) -> None:
    """Add a news item to an existing cluster.

    After linking the item, the cluster's aggregated popularity score,
    source count, and canonical title are recalculated automatically.

    Parameters
    ----------
    db : aiosqlite.Connection
        Open DB connection.
    cluster_id : int
        Target ``news_clusters.id``.
    item : dict
        Same shape as for :func:`create_singleton_cluster`.  Only
        ``news_item_id`` is strictly required here; the rest comes from
        the already-persisted rows when re-aggregating.
    """
    # 1. Link item → cluster
    await db.execute(
        "INSERT INTO cluster_items (cluster_id, news_item_id) VALUES (?, ?)",
        (cluster_id, item["news_item_id"]),
    )

    # 2. Re-aggregate all items in the cluster
    await _recalculate_cluster(db, cluster_id)

    logger.info(
        "Added item %d to existing cluster %d",
        item["news_item_id"], cluster_id,
    )
