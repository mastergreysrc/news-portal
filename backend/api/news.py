"""News API endpoints — feed, detail, daily, search, popular."""

from datetime import date, datetime, timedelta, timezone
from fastapi import APIRouter, HTTPException, Query
from database import get_db
from models import (
    NewsClusterOut,
    NewsFeedResponse,
    NewsDetailOut,
    SourceRef,
    CategoryOut,
)
from pipeline.scorer import get_fire_tier

router = APIRouter(tags=["news"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _fetch_sources_for_clusters(
    db, cluster_ids: list[int]
) -> dict[int, list[SourceRef]]:
    """Batch-fetch SourceRef lists keyed by cluster_id."""
    if not cluster_ids:
        return {}

    placeholders = ",".join("?" for _ in cluster_ids)
    cursor = await db.execute(
        f"""SELECT ci.cluster_id, s.type, s.name, ni.url
            FROM cluster_items ci
            JOIN news_items ni ON ni.id = ci.news_item_id
            JOIN sources s ON s.id = ni.source_id
            WHERE ci.cluster_id IN ({placeholders})
            ORDER BY ci.cluster_id, ni.id""",
        cluster_ids,
    )
    rows = await cursor.fetchall()

    result: dict[int, list[SourceRef]] = {cid: [] for cid in cluster_ids}
    for row in rows:
        cid = row["cluster_id"]
        result[cid].append(SourceRef(type=row["type"], name=row["name"], url=row["url"]))
    return result


async def _fetch_published_at_for_clusters(
    db, cluster_ids: list[int]
) -> dict[int, datetime | None]:
    """Batch-fetch the earliest published_at per cluster."""
    if not cluster_ids:
        return {}

    placeholders = ",".join("?" for _ in cluster_ids)
    cursor = await db.execute(
        f"""SELECT ci.cluster_id, MIN(ni.published_at) as published_at
            FROM cluster_items ci
            JOIN news_items ni ON ni.id = ci.news_item_id
            WHERE ci.cluster_id IN ({placeholders})
            GROUP BY ci.cluster_id""",
        cluster_ids,
    )
    rows = await cursor.fetchall()
    return {row["cluster_id"]: row["published_at"] for row in rows}


async def _rows_to_clusters(rows: list[dict], db) -> list[NewsClusterOut]:
    """Convert raw DB rows into NewsClusterOut objects with sources + fire_tier."""
    if not rows:
        return []

    cluster_ids = [row["id"] for row in rows]
    sources_map = await _fetch_sources_for_clusters(db, cluster_ids)
    published_map = await _fetch_published_at_for_clusters(db, cluster_ids)

    clusters = []
    for row in rows:
        cid = row["id"]
        score = row.get("popularity_score", 0) or 0
        clusters.append(
            NewsClusterOut(
                id=cid,
                canonical_title=row.get("canonical_title") or "",
                canonical_summary=row.get("canonical_summary"),
                popularity_score=score,
                fire_tier=get_fire_tier(score),
                source_count=row.get("source_count", 1),
                sources=sources_map.get(cid, []),
                published_at=published_map.get(cid),
                category=CategoryOut(
                    id=row["cat_id"],
                    name=row["cat_name"],
                    slug=row["cat_slug"],
                    icon=row.get("cat_icon", "📰"),
                ),
                is_favorited=False,
                created_at=row.get("created_at"),
            )
        )
    return clusters


def _parse_date(value: str | None) -> date | None:
    """Parse an ISO date string, return None if invalid or missing."""
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except (ValueError, TypeError):
        return None


# ---------------------------------------------------------------------------
# GET /api/news — paginated news feed
# ---------------------------------------------------------------------------

@router.get("/news", response_model=NewsFeedResponse)
async def news_feed(
    category: str | None = Query(default=None, description="Filter by category slug"),
    date_str: str | None = Query(default=None, alias="date", description="ISO date (default today)"),
    sort: str = Query(default="popularity", description="Sort: popularity, newest, oldest"),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
):
    """Paginated news feed with optional category and date filters."""
    target_date = _parse_date(date_str) or date.today()

    # Build ORDER BY
    sort_column = "nc.popularity_score"
    sort_dir = "DESC"
    if sort == "newest":
        sort_column = "published_at"
        sort_dir = "DESC"
    elif sort == "oldest":
        sort_column = "published_at"
        sort_dir = "ASC"

    offset = (page - 1) * per_page
    db = await get_db()
    try:
        # Build WHERE clause
        where_clauses = []
        params: list = []

        if category:
            where_clauses.append("c.slug = ?")
            params.append(category)

        # Date filter: clusters whose earliest item is on target_date
        where_clauses.append(
            "DATE((SELECT MIN(ni.published_at) FROM cluster_items ci2 "
            "JOIN news_items ni ON ni.id = ci2.news_item_id "
            "WHERE ci2.cluster_id = nc.id)) = ?"
        )
        params.append(target_date.isoformat())

        where_sql = " AND ".join(where_clauses)

        # Count total
        count_cursor = await db.execute(
            f"""SELECT COUNT(*) as cnt
                FROM news_clusters nc
                JOIN categories c ON c.id = nc.category_id
                WHERE {where_sql}""",
            params,
        )
        total = (await count_cursor.fetchone())["cnt"]

        # Fetch page
        cursor = await db.execute(
            f"""SELECT nc.*, c.name as cat_name, c.slug as cat_slug, c.id as cat_id, c.icon as cat_icon,
                       (SELECT MIN(ni.published_at) FROM cluster_items ci2
                        JOIN news_items ni ON ni.id = ci2.news_item_id
                        WHERE ci2.cluster_id = nc.id) as published_at
                FROM news_clusters nc
                JOIN categories c ON c.id = nc.category_id
                WHERE {where_sql}
                ORDER BY {sort_column} {sort_dir}
                LIMIT ? OFFSET ?""",
            params + [per_page, offset],
        )
        rows = await cursor.fetchall()
        clusters = await _rows_to_clusters([dict(r) for r in rows], db)

        return NewsFeedResponse(
            items=clusters,
            pagination={
                "page": page,
                "per_page": per_page,
                "total": total,
                "total_pages": max(1, (total + per_page - 1) // per_page),
            },
        )
    finally:
        await db.close()


# ---------------------------------------------------------------------------
# GET /api/news/daily/{date} — top stories by day
# ---------------------------------------------------------------------------

@router.get("/news/daily/{date_str}", response_model=dict[str, list[NewsClusterOut]])
async def daily_top(date_str: str):
    """Top 8 stories per category for a given date, sorted by popularity_score."""
    target_date = _parse_date(date_str)
    if target_date is None:
        raise HTTPException(status_code=422, detail="Invalid date format. Use YYYY-MM-DD.")

    db = await get_db()
    try:
        # Fetch all categories
        cat_cursor = await db.execute(
            "SELECT id, name, slug, icon FROM categories ORDER BY sort_order, id"
        )
        categories = [dict(row) for row in await cat_cursor.fetchall()]

        result: dict[str, list[NewsClusterOut]] = {}

        for cat in categories:
            cursor = await db.execute(
                """SELECT nc.*, c.name as cat_name, c.slug as cat_slug, c.id as cat_id, c.icon as cat_icon,
                          (SELECT MIN(ni.published_at) FROM cluster_items ci2
                           JOIN news_items ni ON ni.id = ci2.news_item_id
                           WHERE ci2.cluster_id = nc.id) as published_at
                   FROM news_clusters nc
                   JOIN categories c ON c.id = nc.category_id
                   WHERE nc.category_id = ?
                     AND DATE((SELECT MIN(ni.published_at) FROM cluster_items ci2
                               JOIN news_items ni ON ni.id = ci2.news_item_id
                               WHERE ci2.cluster_id = nc.id)) = ?
                   ORDER BY nc.popularity_score DESC
                   LIMIT 8""",
                (cat["id"], target_date.isoformat()),
            )
            rows = await cursor.fetchall()
            clusters = await _rows_to_clusters([dict(r) for r in rows], db)
            result[cat["slug"]] = clusters

        return result
    finally:
        await db.close()


# ---------------------------------------------------------------------------
# GET /api/news/search — FTS5 full-text search
# ---------------------------------------------------------------------------

@router.get("/news/search", response_model=NewsFeedResponse)
async def search_news(
    q: str = Query(..., min_length=1, description="Search query string"),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
):
    """Full-text search across news items using FTS5, returning clusters."""
    offset = (page - 1) * per_page
    db = await get_db()
    try:
        # Count total matching clusters (distinct)
        count_cursor = await db.execute(
            """SELECT COUNT(DISTINCT nc.id) as cnt
               FROM news_fts
               JOIN news_items ni ON ni.id = news_fts.rowid
               JOIN cluster_items ci ON ci.news_item_id = ni.id
               JOIN news_clusters nc ON nc.id = ci.cluster_id
               WHERE news_fts MATCH ?""",
            (q,),
        )
        total = (await count_cursor.fetchone())["cnt"]

        # Search with rank ordering and snippet
        cursor = await db.execute(
            """SELECT DISTINCT nc.*, c.name as cat_name, c.slug as cat_slug, c.id as cat_id, c.icon as cat_icon,
                   snippet(news_fts, 0, '<mark>', '</mark>', '...', 32) as snippet,
                   rank
            FROM news_fts
            JOIN news_items ni ON ni.id = news_fts.rowid
            JOIN cluster_items ci ON ci.news_item_id = ni.id
            JOIN news_clusters nc ON nc.id = ci.cluster_id
            JOIN categories c ON c.id = nc.category_id
            WHERE news_fts MATCH ?
            ORDER BY rank
            LIMIT ? OFFSET ?""",
            (q, per_page, offset),
        )
        rows = await cursor.fetchall()
        clusters = await _rows_to_clusters([dict(r) for r in rows], db)

        return NewsFeedResponse(
            items=clusters,
            pagination={
                "page": page,
                "per_page": per_page,
                "total": total,
                "total_pages": max(1, (total + per_page - 1) // per_page),
            },
        )
    finally:
        await db.close()


# ---------------------------------------------------------------------------
# GET /api/news/popular — trending
# ---------------------------------------------------------------------------

@router.get("/news/popular", response_model=NewsFeedResponse)
async def popular_news(
    per_page: int = Query(default=20, ge=1, le=100),
):
    """Top clusters from last 24 hours sorted by popularity_score DESC."""
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
    db = await get_db()
    try:
        # Count total trending clusters
        count_cursor = await db.execute(
            """SELECT COUNT(*) as cnt
               FROM news_clusters nc
               WHERE nc.updated_at >= ?""",
            (cutoff,),
        )
        total = (await count_cursor.fetchone())["cnt"]

        cursor = await db.execute(
            """SELECT nc.*, c.name as cat_name, c.slug as cat_slug, c.id as cat_id, c.icon as cat_icon,
                      (SELECT MIN(ni.published_at) FROM cluster_items ci2
                       JOIN news_items ni ON ni.id = ci2.news_item_id
                       WHERE ci2.cluster_id = nc.id) as published_at
               FROM news_clusters nc
               JOIN categories c ON c.id = nc.category_id
               WHERE nc.updated_at >= ?
               ORDER BY nc.popularity_score DESC
               LIMIT ?""",
            (cutoff, per_page),
        )
        rows = await cursor.fetchall()
        clusters = await _rows_to_clusters([dict(r) for r in rows], db)

        return NewsFeedResponse(
            items=clusters,
            pagination={
                "page": 1,
                "per_page": per_page,
                "total": total,
                "total_pages": max(1, (total + per_page - 1) // per_page),
            },
        )
    finally:
        await db.close()


# ---------------------------------------------------------------------------
# GET /api/news/{cluster_id} — single cluster detail
# ---------------------------------------------------------------------------

@router.get("/news/{cluster_id}", response_model=NewsDetailOut)
async def news_detail(cluster_id: int):
    """Single cluster detail with all source items."""
    db = await get_db()
    try:
        # Fetch cluster
        cursor = await db.execute(
            """SELECT nc.*, c.name as cat_name, c.slug as cat_slug, c.id as cat_id, c.icon as cat_icon
               FROM news_clusters nc
               JOIN categories c ON c.id = nc.category_id
               WHERE nc.id = ?""",
            (cluster_id,),
        )
        row = await cursor.fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Cluster not found")

        cluster_dict = dict(row)

        # Fetch all items in the cluster
        items_cursor = await db.execute(
            """SELECT ni.id, ni.title, ni.title_pl, ni.summary, ni.summary_pl,
                      ni.url, ni.published_at, ni.popularity_raw, ni.fetched_at,
                      s.type as source_type, s.name as source_name
               FROM cluster_items ci
               JOIN news_items ni ON ni.id = ci.news_item_id
               JOIN sources s ON s.id = ni.source_id
               WHERE ci.cluster_id = ?
               ORDER BY ni.published_at DESC""",
            (cluster_id,),
        )
        item_rows = await items_cursor.fetchall()
        items = [dict(r) for r in item_rows]

        # Build sources
        sources = [
            SourceRef(type=it["source_type"], name=it["source_name"], url=it["url"])
            for it in items
        ]

        # Published at = earliest item
        published_at = None
        if items:
            published_vals = [it.get("published_at") for it in items if it.get("published_at")]
            if published_vals:
                published_at = min(published_vals)

        score = cluster_dict.get("popularity_score", 0) or 0

        return NewsDetailOut(
            id=cluster_dict["id"],
            canonical_title=cluster_dict.get("canonical_title") or "",
            canonical_summary=cluster_dict.get("canonical_summary"),
            popularity_score=score,
            fire_tier=get_fire_tier(score),
            source_count=cluster_dict.get("source_count", 1),
            sources=sources,
            published_at=published_at,
            category=CategoryOut(
                id=cluster_dict["cat_id"],
                name=cluster_dict["cat_name"],
                slug=cluster_dict["cat_slug"],
                icon=cluster_dict.get("cat_icon", "📰"),
            ),
            is_favorited=False,
            created_at=cluster_dict.get("created_at"),
            items=items,
        )
    finally:
        await db.close()


# ---------------------------------------------------------------------------
# Admin — on-demand collection
# ---------------------------------------------------------------------------

from fastapi import BackgroundTasks, Header
from config import get_settings


@router.post("/admin/collect")
async def trigger_collection(
    category: str = "gaming",
    x_admin_key: str = Header(None, alias="X-Admin-Key"),
    background_tasks: BackgroundTasks = None,
):
    """Trigger an on-demand collection run. Requires X-Admin-Key header."""
    settings = get_settings()
    if x_admin_key != settings.admin_key:
        raise HTTPException(status_code=403, detail="Invalid admin key")

    from pipeline.orchestrator import run_pipeline

    background_tasks.add_task(run_pipeline, category)
    return {"status": "started", "category": category}


@router.get("/admin/collect/status")
async def collection_status(category: str = "gaming"):
    """Check if a collection is currently running for a category."""
    db = await get_db()
    try:
        cursor = await db.execute(
            """SELECT started_at, finished_at, status, error_msg
               FROM collection_runs
               WHERE source_id IN (
                   SELECT s.id FROM sources s
                   JOIN categories c ON c.id = s.category_id
                   WHERE c.slug = ?
               )
               ORDER BY started_at DESC LIMIT 1""",
            (category,),
        )
        row = await cursor.fetchone()
        if not row:
            return {"running": False, "last_run": None, "last_status": None}

        return {
            "running": row["status"] == "running" and row["finished_at"] is None,
            "last_run": row["started_at"],
            "last_status": row["status"],
            "error": row["error_msg"] if row["status"] == "error" else None,
        }
    finally:
        await db.close()
