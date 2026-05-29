# 🎮 Gaming News PL

Polish-language gaming news aggregator — collects from Reddit, X/Twitter, YouTube, RSS, and scraped websites twice daily. Translates to Polish via Groq, deduplicates across sources, and serves a mobile-responsive web portal.

**[Live demo → http://localhost:8000](http://localhost:8000)**

## Features

- **Multi-source collection**: Reddit (7 subreddits), X/Twitter, YouTube, RSS feeds, scraped websites
- **Polish translation + summarization**: Groq free tier (llama-3.1-8b-instant) handles both in a single API call
- **Smart deduplication**: 3-pass dedup — exact URL, domain+slug, TF-IDF title similarity
- **Source clustering**: Same story from 5 different sources → one card with all source links
- **Popularity scoring**: Fire emoji (🔥) with color-coded tiers based on aggregated engagement
- **Full-text search**: SQLite FTS5 — search all historical news instantly
- **User profiles**: JWT auth, save favorites, personalized feed
- **On-demand refresh**: Manual collection trigger from the web UI
- **Mobile responsive**: SvelteKit + Tailwind CSS, grid adapts 1→2→3 columns
- **Dark mode**: System preference detection
- **Zero budget**: Every component uses free tiers/free methods — no paid APIs required

## Architecture

```
Collectors (8 sources)  →  Dedup (3-pass)  →  Groq (translate + summarize)
                                                      │
                                                      ▼
                           SQLite + FTS5  ←  Score + Cluster
                                 │
                    ┌────────────┼────────────┐
                    ▼                         ▼
            FastAPI REST API          Hermes cron → Telegram
                    │
                    ▼
          SvelteKit SPA (served as static files)
```

## Prerequisites

| Component | Requirement | Why |
|-----------|------------|-----|
| Groq API key | Free from [console.groq.com](https://console.groq.com) | Translation + summarization |
| Docker (optional) | Rootless or standard | Containerized deployment |

**No other API keys required.** All collectors use free/no-auth methods:
- Reddit → PRAW read-only mode
- Twitter/X → `ntscraper` (anonymous search)
- YouTube → `yt-dlp` search
- RSS → `feedparser`
- Web scraping → `httpx` + `BeautifulSoup4`

## Quick Start (Docker)

```bash
# 1. Clone
git clone https://github.com/mastergreysrc/news-portal.git
cd news-portal

# 2. Configure
cp .env.example .env
# Edit .env — set GROQ_API_KEY, SECRET_KEY, ADMIN_KEY

# 3. Start (rootless Docker — no sudo needed)
docker compose up -d

# 4. Verify
curl http://localhost:8000/api/health

# 5. Trigger first collection
curl -X POST http://localhost:8000/api/admin/collect?category=gaming \
  -H "X-Admin-Key: your-admin-key"

# 6. Open browser → http://localhost:8000

# Other commands
docker compose logs -f    # follow logs
docker compose restart    # restart after config changes
docker compose down       # stop and remove containers
```

## Manual Installation

```bash
# 1. Clone
git clone https://github.com/mastergreysrc/news-portal.git
cd news-portal

# 2. Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 3. Install dependencies
pip install -r backend/requirements.txt

# 4. Configure
cp .env.example .env
# Edit .env — set GROQ_API_KEY, SECRET_KEY, ADMIN_KEY

# 5. Build frontend
cd frontend
npm install
npm run build
cd ..

# 6. Start
cd backend
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# 7. Open browser → http://localhost:8000
```

## Configuration

All settings in `config.yaml`:

```yaml
schedule:
  times: ["08:00", "20:00"]     # CET — change for more frequent runs
  timezone: "Europe/Warsaw"

summarization:
  model: "llama-3.1-8b-instant" # swap to mixtral-8x7b for better PL

categories:
  - name: "Gaming"
    sources:
      - type: reddit
        config:
          subreddit: "GamingLeaksAndRumours"
          limit: 25
      # ... add more categories or sources anytime
```

### Adding a new category

Add a block to `config.yaml` — no code changes needed:

```yaml
categories:
  - name: "Tech"
    slug: "tech"
    icon: "💻"
    sources:
      - type: rss
        name: "Example Tech Blog"
        config:
          url: "https://example.com/rss"
```

### Adding a new Reddit source

```yaml
- type: reddit
  name: "r/YourSubreddit"
  config:
    subreddit: "YourSubreddit"
    limit: 25
    sort: "hot"   # or "new"
```

### Adding a scraped source

```yaml
- type: scrape
  name: "Site Name"
  config:
    url: "https://site.com/news/"
    article_selector: "article"
    title_selector: "h3 a"
    link_selector: "h3 a"
    summary_selector: "p.description"  # optional
    limit: 15
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/health` | Health check |
| `GET` | `/api/categories` | List categories |
| `GET` | `/api/news` | Paginated feed (filter by category, date, sort) |
| `GET` | `/api/news/{id}` | Single cluster detail with all sources |
| `GET` | `/api/news/daily/{date}` | News of the day digest |
| `GET` | `/api/news/search?q=...` | Full-text search |
| `GET` | `/api/news/popular` | Trending (last 24h) |
| `POST` | `/api/users/register` | Create account |
| `POST` | `/api/users/login` | Login (returns JWT) |
| `GET` | `/api/users/me/favorites` | Saved favorites |
| `POST` | `/api/users/me/favorites/{id}` | Toggle favorite |
| `POST` | `/api/admin/collect` | On-demand refresh (needs X-Admin-Key) |
| `GET` | `/api/admin/collect/status` | Collection run status |

## Telegram Integration (Separate Setup)

Telegram delivery uses a separate Hermes cron job that reads the API and sends formatted digests:

```
Schedule: 08:05, 20:05 CET (5 min after each collection)
Pattern: Fetches GET /api/news/daily/today → formats → send_message → Telegram
```

## Fire Tiers (🔥)

| Tier | Score | Icon | Color | Meaning |
|------|-------|------|-------|---------|
| 0 | 0–10 | 🔥 | Gray | Low engagement |
| 1 | 10–30 | 🔥 | Orange | Moderate |
| 2 | 30–60 | 🔥 | Red | Hot |
| 3 | 60–100 | 🔥🔥 | Crimson | Blazing |
| 4 | 100+ | 🔥🔥🔥 | Purple | Viral |

Score combines upvotes/retweets/views across sources, weighted by source type, boosted by the number of sources reporting the same story.

## Project Structure

```
news-portal/
├── backend/
│   ├── main.py                    # FastAPI app
│   ├── config.py                  # Settings from YAML + env
│   ├── database.py                # SQLite schema + connection
│   ├── auth.py                    # JWT + bcrypt
│   ├── scheduler.py              # APScheduler (2x daily)
│   ├── models.py                  # Pydantic request/response models
│   ├── collectors/                # Source collectors
│   │   ├── reddit.py              # PRAW (read-only, no key)
│   │   ├── twitter.py             # ntscraper (anonymous)
│   │   ├── youtube.py             # yt-dlp search
│   │   ├── rss.py                 # feedparser
│   │   └── scraper.py             # httpx + BeautifulSoup
│   ├── pipeline/                  # Processing
│   │   ├── normalizer.py          # URL normalization
│   │   ├── deduplicator.py        # 3-pass dedup
│   │   ├── clusterer.py           # Group items → clusters
│   │   ├── scorer.py              # Popularity + fire tiers
│   │   ├── translator.py          # Groq translate + summarize
│   │   └── orchestrator.py        # Full pipeline runner
│   └── api/                       # REST endpoints
├── frontend/                      # SvelteKit + Tailwind
│   └── src/
│       ├── lib/api.ts             # API client
│       ├── lib/components/        # UI components
│       └── routes/                # Pages
├── config.yaml                    # All source + schedule config
├── Dockerfile                     # Multi-stage build
├── docker-compose.yml             # Single-service deployment
└── .github/workflows/build.yml    # CI: Docker build + smoke test
```

## Tech Stack

| Layer | Technology | Rationale |
|-------|-----------|-----------|
| Backend | Python 3.12, FastAPI | Async, typed, auto OpenAPI docs |
| Database | SQLite + FTS5 | Zero setup, built-in full-text search |
| Frontend | SvelteKit, Tailwind CSS | Smallest bundle, mobile-first |
| Scheduler | APScheduler | In-process, no Redis/Celery |
| Translation | Groq (llama-3.1-8b-instant) | Free tier, single call does both |
| Dedup | TF-IDF + cosine similarity | Tunable, lightweight |
| Auth | JWT (python-jose + bcrypt) | Stateless, no session server |
| Deployment | Docker (multi-stage) | Single container, ~200MB |

## License

MIT
