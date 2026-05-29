"""Deduplication — three-pass: exact URL, domain+slug, TF-IDF similarity."""

import asyncio
import math
import re
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional
from urllib.parse import urlparse

import aiosqlite
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from .normalizer import normalize_url
from database import get_db
from config import get_settings

logger = logging.getLogger(__name__)


def extract_slug(url: str) -> str:
    """Extract the last meaningful path segment as a slug."""
    path = urlparse(url).path.rstrip('/')
    parts = [p for p in path.split('/') if p]
    if not parts:
        return ""
    # Take last part, strip file extension
    slug = parts[-1]
    slug = re.sub(r'\.[a-zA-Z0-9]+$', '', slug)
    return slug.lower()


async def find_duplicate(title: str, url: str, category_id: int, source_id: int) -> Optional[int]:
    """
    Three-pass dedup. Returns existing cluster_id if duplicate found, else None.
    """
    settings = get_settings()
    norm_url = normalize_url(url)
    threshold = settings.dedup_title_similarity_threshold
    lookback = settings.dedup_lookback_days
    cutoff = (datetime.now(timezone.utc) - timedelta(days=lookback)).isoformat()
    
    db = await get_db()
    try:
        # Pass 1: Exact URL match
        cursor = await db.execute(
            """SELECT ci.cluster_id FROM news_items ni
               JOIN cluster_items ci ON ci.news_item_id = ni.id
               WHERE ni.url_normalized = ? AND ni.category_id = ?""",
            (norm_url, category_id),
        )
        row = await cursor.fetchone()
        if row:
            logger.debug("Dedup Pass 1 (exact URL): matched cluster %s", row[0])
            return row[0]
        
        # Pass 2: Domain + slug match within lookback window
        slug = extract_slug(url)
        if slug:
            domain = urlparse(url).netloc.lower()
            cursor = await db.execute(
                """SELECT ci.cluster_id FROM news_items ni
                   JOIN cluster_items ci ON ci.news_item_id = ni.id
                   WHERE ni.url_normalized LIKE ?
                   AND ni.category_id = ?
                   AND ni.fetched_at > ?""",
                (f"%{domain}%{slug}%", category_id, cutoff),
            )
            row = await cursor.fetchone()
            if row:
                logger.debug("Dedup Pass 2 (domain+slug): matched cluster %s", row[0])
                return row[0]
        
        # Pass 3: TF-IDF title similarity
        cursor = await db.execute(
            """SELECT nc.id, nc.canonical_title FROM news_clusters nc
               WHERE nc.category_id = ? AND nc.created_at > ?""",
            (category_id, cutoff),
        )
        existing = await cursor.fetchall()
        
        if existing:
            titles = [row[1] or "" for row in existing]
            try:
                vectorizer = TfidfVectorizer(stop_words='english')
                all_titles = [title] + titles
                vectors = vectorizer.fit_transform(all_titles)
                similarities = cosine_similarity(vectors[0:1], vectors[1:]).flatten()
                best_idx = int(similarities.argmax())
                if similarities[best_idx] >= threshold:
                    logger.debug(
                        "Dedup Pass 3 (TF-IDF %.3f): matched cluster %s",
                        similarities[best_idx], existing[best_idx][0],
                    )
                    return existing[best_idx][0]
            except Exception as e:
                logger.warning("TF-IDF dedup failed: %s", e)
        
        return None
    finally:
        await db.close()
