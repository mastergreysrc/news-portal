"""Category endpoints."""

from fastapi import APIRouter
from database import get_db
from models import CategoryOut

router = APIRouter(tags=["categories"])


@router.get("/categories", response_model=list[CategoryOut])
async def list_categories():
    """List all categories."""
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT id, name, slug, icon FROM categories ORDER BY sort_order, id"
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        await db.close()
