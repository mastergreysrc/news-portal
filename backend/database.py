"""SQLite database layer — schema, connection, initialization."""

import aiosqlite
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "news_portal.db"

SCHEMA = """
-- ============================================================
-- CATEGORIES (generic — add more without code changes)
-- ============================================================
CREATE TABLE IF NOT EXISTS categories (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL UNIQUE,
    slug        TEXT NOT NULL UNIQUE,
    description TEXT,
    icon        TEXT DEFAULT '📰',
    sort_order  INTEGER DEFAULT 0,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- SOURCES (per category, per type)
-- ============================================================
CREATE TABLE IF NOT EXISTS sources (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    category_id INTEGER NOT NULL REFERENCES categories(id) ON DELETE CASCADE,
    type        TEXT NOT NULL,
    name        TEXT NOT NULL,
    config      TEXT NOT NULL DEFAULT '{}',
    enabled     INTEGER NOT NULL DEFAULT 1,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- NEWS ITEMS (individual articles/posts)
-- ============================================================
CREATE TABLE IF NOT EXISTS news_items (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    title           TEXT NOT NULL,
    title_pl        TEXT,
    summary         TEXT,
    summary_pl      TEXT,
    url             TEXT NOT NULL,
    url_normalized  TEXT NOT NULL,
    source_id       INTEGER NOT NULL REFERENCES sources(id),
    category_id     INTEGER NOT NULL REFERENCES categories(id),
    published_at    TIMESTAMP,
    fetched_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    popularity_raw  REAL DEFAULT 0,
    metadata        TEXT DEFAULT '{}',
    UNIQUE(url_normalized, source_id)
);

CREATE INDEX IF NOT EXISTS idx_news_category ON news_items(category_id, fetched_at DESC);
CREATE INDEX IF NOT EXISTS idx_news_published ON news_items(published_at DESC);
CREATE INDEX IF NOT EXISTS idx_news_popularity ON news_items(popularity_raw DESC);

-- ============================================================
-- NEWS CLUSTERS (same story, multiple sources)
-- ============================================================
CREATE TABLE IF NOT EXISTS news_clusters (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    canonical_title TEXT,
    canonical_summary TEXT,
    category_id     INTEGER NOT NULL REFERENCES categories(id),
    popularity_score REAL DEFAULT 0,
    source_count    INTEGER DEFAULT 1,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS cluster_items (
    cluster_id  INTEGER NOT NULL REFERENCES news_clusters(id) ON DELETE CASCADE,
    news_item_id INTEGER NOT NULL REFERENCES news_items(id) ON DELETE CASCADE,
    PRIMARY KEY (cluster_id, news_item_id)
);

-- ============================================================
-- FULL-TEXT SEARCH (FTS5)
-- ============================================================
CREATE VIRTUAL TABLE IF NOT EXISTS news_fts USING fts5(
    title_pl,
    summary_pl,
    content='news_items',
    content_rowid='id'
);

-- Triggers to keep FTS in sync
DROP TRIGGER IF EXISTS news_ai;
CREATE TRIGGER news_ai AFTER INSERT ON news_items BEGIN
    INSERT INTO news_fts(rowid, title_pl, summary_pl)
    VALUES (new.id, new.title_pl, new.summary_pl);
END;

DROP TRIGGER IF EXISTS news_ad;
CREATE TRIGGER news_ad AFTER DELETE ON news_items BEGIN
    INSERT INTO news_fts(news_fts, rowid, title_pl, summary_pl)
    VALUES ('delete', old.id, old.title_pl, old.summary_pl);
END;

DROP TRIGGER IF EXISTS news_au;
CREATE TRIGGER news_au AFTER UPDATE ON news_items BEGIN
    INSERT INTO news_fts(news_fts, rowid, title_pl, summary_pl)
    VALUES ('delete', old.id, old.title_pl, old.summary_pl);
    INSERT INTO news_fts(rowid, title_pl, summary_pl)
    VALUES (new.id, new.title_pl, new.summary_pl);
END;

-- ============================================================
-- USERS & FAVORITES
-- ============================================================
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS favorites (
    user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    cluster_id  INTEGER NOT NULL REFERENCES news_clusters(id) ON DELETE CASCADE,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, cluster_id)
);

-- ============================================================
-- COLLECTION LOG (for debugging / avoiding re-runs)
-- ============================================================
CREATE TABLE IF NOT EXISTS collection_runs (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at    TIMESTAMP NOT NULL,
    finished_at   TIMESTAMP,
    items_fetched INTEGER DEFAULT 0,
    items_new     INTEGER DEFAULT 0,
    source_id     INTEGER REFERENCES sources(id),
    status        TEXT DEFAULT 'running',
    error_msg     TEXT
);
"""


async def get_db() -> aiosqlite.Connection:
    """Return a connection with row_factory set for dict-like access."""
    db = await aiosqlite.connect(str(DB_PATH))
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA journal_mode=WAL")
    await db.execute("PRAGMA foreign_keys=ON")
    return db


async def init_db(db: aiosqlite.Connection | None = None) -> None:
    """Initialize database schema and seed categories."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    close_after = db is None
    if db is None:
        db = await get_db()

    await db.executescript(SCHEMA)
    await db.commit()

    if close_after:
        await db.close()
