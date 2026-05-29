"""User endpoints — register, login, favorites."""

from fastapi import APIRouter, HTTPException, Depends
import aiosqlite
from database import get_db
from models import UserRegisterIn, UserLoginIn, TokenOut, UserOut, NewsClusterOut
from auth import hash_password, verify_password, create_access_token, get_current_user

router = APIRouter(tags=["users"])


@router.post("/users/register", response_model=TokenOut)
async def register(data: UserRegisterIn):
    """Register a new user. Returns JWT token."""
    if len(data.username) < 3 or len(data.password) < 4:
        raise HTTPException(400, "Username min 3 chars, password min 4 chars")
    
    db = await get_db()
    try:
        try:
            cursor = await db.execute(
                "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                (data.username, hash_password(data.password)),
            )
            await db.commit()
            user_id = cursor.lastrowid
        except aiosqlite.IntegrityError:
            raise HTTPException(409, "Username already taken")
        
        token = create_access_token(user_id)
        return {"access_token": token, "token_type": "bearer"}
    finally:
        await db.close()


@router.post("/users/login", response_model=TokenOut)
async def login(data: UserLoginIn):
    """Login. Returns JWT token."""
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT id, password_hash FROM users WHERE username = ?",
            (data.username,),
        )
        row = await cursor.fetchone()
        if not row or not verify_password(data.password, row["password_hash"]):
            raise HTTPException(401, "Invalid username or password")
        
        token = create_access_token(row["id"])
        return {"access_token": token, "token_type": "bearer"}
    finally:
        await db.close()


@router.get("/users/me", response_model=UserOut)
async def get_me(user_id: int | None = Depends(get_current_user)):
    """Get current user profile."""
    if not user_id:
        raise HTTPException(401, "Not authenticated")
    
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT id, username, created_at FROM users WHERE id = ?",
            (user_id,),
        )
        row = await cursor.fetchone()
        if not row:
            raise HTTPException(404, "User not found")
        return dict(row)
    finally:
        await db.close()


@router.get("/users/me/favorites")
async def get_favorites(user_id: int | None = Depends(get_current_user)):
    """Get user's favorited news clusters."""
    if not user_id:
        raise HTTPException(401, "Not authenticated")
    
    db = await get_db()
    try:
        cursor = await db.execute(
            """SELECT nc.* FROM news_clusters nc
               JOIN favorites f ON f.cluster_id = nc.id
               WHERE f.user_id = ?
               ORDER BY f.created_at DESC""",
            (user_id,),
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        await db.close()


@router.post("/users/me/favorites/{cluster_id}")
async def toggle_favorite(
    cluster_id: int,
    user_id: int | None = Depends(get_current_user),
):
    """Toggle favorite status: add if not exists, remove if exists."""
    if not user_id:
        raise HTTPException(401, "Not authenticated")
    
    db = await get_db()
    try:
        # Check if cluster exists
        cursor = await db.execute(
            "SELECT id FROM news_clusters WHERE id = ?", (cluster_id,),
        )
        if not await cursor.fetchone():
            raise HTTPException(404, "News cluster not found")
        
        # Check if already favorited
        cursor = await db.execute(
            "SELECT 1 FROM favorites WHERE user_id = ? AND cluster_id = ?",
            (user_id, cluster_id),
        )
        if await cursor.fetchone():
            # Remove
            await db.execute(
                "DELETE FROM favorites WHERE user_id = ? AND cluster_id = ?",
                (user_id, cluster_id),
            )
            await db.commit()
            return {"favorited": False}
        else:
            # Add
            await db.execute(
                "INSERT INTO favorites (user_id, cluster_id) VALUES (?, ?)",
                (user_id, cluster_id),
            )
            await db.commit()
            return {"favorited": True}
    finally:
        await db.close()
