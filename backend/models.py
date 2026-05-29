"""Pydantic models for API request/response schemas."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel


# ---- Category ----

class CategoryOut(BaseModel):
    id: int
    name: str
    slug: str
    icon: str = "📰"

    class Config:
        from_attributes = True


# ---- Source ----

class SourceOut(BaseModel):
    id: int
    type: str
    name: str
    enabled: bool

    class Config:
        from_attributes = True


class SourceRef(BaseModel):
    """Lightweight source reference inside a news response."""
    type: str
    name: str
    url: str


# ---- News ----

class NewsClusterOut(BaseModel):
    id: int
    canonical_title: str
    canonical_summary: Optional[str] = None
    popularity_score: float = 0.0
    fire_tier: int = 0
    source_count: int = 1
    sources: list[SourceRef] = []
    published_at: Optional[datetime] = None
    category: Optional[CategoryOut] = None
    is_favorited: bool = False
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class NewsFeedResponse(BaseModel):
    items: list[NewsClusterOut]
    pagination: dict


class NewsDetailOut(NewsClusterOut):
    items: list[dict] = []  # individual news_items with full metadata


# ---- Users ----

class UserRegisterIn(BaseModel):
    username: str
    password: str


class UserLoginIn(BaseModel):
    username: str
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: int
    username: str
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ---- Admin ----

class CollectTriggerOut(BaseModel):
    status: str
    category: str


class CollectStatusOut(BaseModel):
    running: bool
    last_run: Optional[datetime] = None
    last_status: Optional[str] = None
