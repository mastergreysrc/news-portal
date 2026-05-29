"""Twitter/X collector — uses ntscraper (Nitter, no auth required)."""

import asyncio
import logging
from datetime import datetime, timezone

from .base import BaseCollector, RawNewsItem

logger = logging.getLogger(__name__)


class TwitterCollector(BaseCollector):
    """Collect tweets via ntscraper / Nitter proxy."""

    source_type: str = "twitter"

    async def collect(self) -> list[RawNewsItem]:
        """Search Twitter via Nitter for each configured keyword."""
        keywords: list[str] = self.config.get("keywords", [])
        limit: int = self.config.get("limit", 50)

        if not keywords:
            logger.warning("Twitter collector %r: no keywords configured", self.source_name)
            return []

        results: list[RawNewsItem] = []

        try:
            items = await asyncio.to_thread(self._run_scraper, keywords, limit)
            results.extend(items)
        except Exception:
            logger.exception("Twitter collector %r: scraping failed", self.source_name)

        return results

    # ------------------------------------------------------------------
    def _run_scraper(self, keywords: list[str], limit: int) -> list[RawNewsItem]:
        """Synchronous portion — runs inside asyncio.to_thread()."""
        # Lazy import so the module loads even when ntscraper is missing
        try:
            from ntscraper import Nitter
        except ImportError:
            logger.error("ntscraper not installed — install with: pip install ntscraper")
            return []

        scraper = Nitter(log_level=1)

        items: list[RawNewsItem] = []
        seen_urls: set[str] = set()

        for keyword in keywords:
            try:
                raw = scraper.search_terms(keyword)
            except Exception:
                logger.warning("Twitter search for %r failed, skipping", keyword)
                continue

            if not raw or "tweets" not in raw:
                continue

            for tweet in raw["tweets"]:
                if len(items) >= limit:
                    break

                text = tweet.get("text", "") or tweet.get("content", "") or ""
                link = tweet.get("link", "") or ""
                if not link:
                    continue
                if link in seen_urls:
                    continue
                seen_urls.add(link)

                title = text[:200]
                summary = text[:500]

                # Compute popularity: likes + retweets + replies
                likes = int(tweet.get("likes", 0) or tweet.get("like_count", 0) or 0)
                retweets = int(tweet.get("retweets", 0) or tweet.get("retweet_count", 0) or 0)
                replies = int(tweet.get("replies", 0) or tweet.get("reply_count", 0) or 0)
                popularity = float(likes + retweets + replies)

                # Parse date if present
                published_at = None
                dt_raw = tweet.get("date", "") or tweet.get("created_at", "")
                if dt_raw:
                    try:
                        published_at = _parse_twitter_date(dt_raw)
                    except Exception:
                        published_at = None

                items.append(RawNewsItem(
                    title=title,
                    url=link,
                    summary=summary,
                    source_type=self.source_type,
                    source_name=self.source_name,
                    published_at=published_at,
                    popularity_raw=popularity,
                    metadata={
                        "likes": likes,
                        "retweets": retweets,
                        "replies": replies,
                        "user": tweet.get("user", {}).get("username", "") if isinstance(tweet.get("user"), dict) else "",
                    },
                ))

            if len(items) >= limit:
                break

        return items[:limit]


def _parse_twitter_date(date_str: str) -> datetime:
    """Try common Twitter date formats, return datetime (UTC)."""
    # ntscraper often returns something like "2h ago" or "May 29, 2026 · 10:30 AM UTC"
    for fmt in ("%b %d, %Y · %I:%M %p %Z", "%Y-%m-%dT%H:%M:%S", "%a %b %d %H:%M:%S %z %Y"):
        try:
            dt = datetime.strptime(date_str.strip(), fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            continue

    # Relative strings like "2h ago" — just return current time
    return datetime.now(tz=timezone.utc)
