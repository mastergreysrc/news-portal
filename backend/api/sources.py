"""Source endpoints."""

from fastapi import APIRouter, Query
from database import get_db
from models import SourceOut

router = APIRouter(tags=["sources"])


@router.get("/sources", response_model=list[SourceOut])
async def list_sources(category: str = Query(default=None, description="Filter by category slug")):
    """List sources, optionally filtered by category slug."""
    db = await get_db()
    try:
        if category:
            cursor = await db.execute(
                """SELECT s.id, s.type, s.name, s.enabled
                   FROM sources s
                   JOIN categories c ON c.id = s.category_id
                   WHERE c.slug = ?
                   ORDER BY s.id""",
                (category,),
            )
        else:
            cursor = await db.execute(
                "SELECT id, type, name, enabled FROM sources ORDER BY id"
            )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        await db.close()
