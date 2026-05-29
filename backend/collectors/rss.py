"""RSS collector — fetches and parses RSS/Atom feeds."""

import asyncio
import logging
import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

import httpx

from .base import BaseCollector, RawNewsItem

logger = logging.getLogger(__name__)

# Regex to strip HTML tags from summary text
_HTML_TAG_RE = re.compile(r"<[^>]+>")


class RSSCollector(BaseCollector):
    """Collect articles from an RSS/Atom feed."""

    source_type: str = "rss"

    async def collect(self) -> list[RawNewsItem]:
        """Fetch the RSS feed URL and return parsed entries."""
        url: str = self.config.get("url", "")

        if not url:
            logger.warning("RSS collector %r: no URL configured", self.source_name)
            return []

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, follow_redirects=True)
                response.raise_for_status()
                raw_xml = response.text
        except httpx.HTTPError as exc:
            logger.warning("RSS collector %r: HTTP error fetching %s: %s", self.source_name, url, exc)
            return []
        except Exception:
            logger.exception("RSS collector %r: failed to fetch %s", self.source_name, url)
            return []

        # feedparser.parse is sync but fast — run in thread
        try:
            feed = await asyncio.to_thread(self._parse_feed, raw_xml)
        except Exception:
            logger.exception("RSS collector %r: failed to parse feed %s", self.source_name, url)
            return []

        items: list[RawNewsItem] = []
        seen_urls: set[str] = set()

        for entry in feed.get("entries", []):
            link = entry.get("link", "")
            if not link:
                continue
            if link in seen_urls:
                continue
            seen_urls.add(link)

            title = entry.get("title", "") or ""
            raw_summary = entry.get("summary", "") or entry.get("description", "") or ""
            # Strip HTML tags
            summary = _HTML_TAG_RE.sub("", raw_summary).strip()[:500]

            # Parse date — feedparser may return a time.struct_time or string
            published_at = _parse_entry_date(entry)

            items.append(RawNewsItem(
                title=title,
                url=link,
                summary=summary,
                source_type=self.source_type,
                source_name=self.source_name,
                published_at=published_at,
                popularity_raw=15.0,  # fixed baseline for RSS
                metadata={
                    "author": entry.get("author", ""),
                    "feed_title": feed.get("feed", {}).get("title", ""),
                },
            ))

        return items

    # ------------------------------------------------------------------
    @staticmethod
    def _parse_feed(xml_text: str) -> dict:
        """Parse RSS/Atom XML; runs inside asyncio.to_thread()."""
        try:
            import feedparser
        except ImportError:
            logger.error("feedparser not installed — install with: pip install feedparser")
            return {"entries": []}

        return feedparser.parse(xml_text)


def _parse_entry_date(entry: dict) -> datetime | None:
    """Extract a publication datetime from a feed entry."""
    date_str = entry.get("published", "") or entry.get("updated", "")
    if not date_str:
        return None

    # feedparser may store parsed dates in published_parsed / updated_parsed
    parsed = entry.get("published_parsed") or entry.get("updated_parsed")
    if parsed and isinstance(parsed, (tuple, list)) and len(parsed) >= 6:
        try:
            return datetime(*parsed[:6], tzinfo=timezone.utc)
        except Exception:
            pass

    # Try email.utils.parsedate_to_datetime for RFC 2822 dates
    try:
        dt = parsedate_to_datetime(str(date_str))
        return dt.astimezone(timezone.utc) if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except Exception:
        pass

    # Try ISO 8601
    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"):
        try:
            dt = datetime.strptime(str(date_str).strip(), fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            continue

    return None
