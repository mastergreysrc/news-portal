"""YouTube collector — uses yt-dlp (no API key, free)."""

import asyncio
import logging
from datetime import datetime, timezone

from .base import BaseCollector, RawNewsItem

logger = logging.getLogger(__name__)


class YouTubeCollector(BaseCollector):
    """Collect YouTube videos via yt-dlp search."""

    source_type: str = "youtube"

    async def collect(self) -> list[RawNewsItem]:
        """Search YouTube for each configured keyword and return matching videos."""
        keywords: list[str] = self.config.get("keywords", [])
        limit: int = self.config.get("limit", 20)

        if not keywords:
            logger.warning("YouTube collector %r: no keywords configured", self.source_name)
            return []

        results: list[RawNewsItem] = []

        try:
            items = await asyncio.to_thread(self._run_searches, keywords, limit)
            results.extend(items)
        except Exception:
            logger.exception("YouTube collector %r: search failed", self.source_name)

        return results

    # ------------------------------------------------------------------
    def _run_searches(self, keywords: list[str], limit: int) -> list[RawNewsItem]:
        """Synchronous portion — runs inside asyncio.to_thread()."""
        try:
            import yt_dlp
        except ImportError:
            logger.error("yt-dlp not installed — install with: pip install yt-dlp")
            return []

        items: list[RawNewsItem] = []
        seen_urls: set[str] = set()

        ydl_opts = {
            "quiet": True,
            "extract_flat": False,
            "no_warnings": True,
            "skip_download": True,
            "playlistend": limit,
        }

        for keyword in keywords:
            if len(items) >= limit:
                break

            query = f"ytsearch{limit}:{keyword}"

            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(query, download=False)
            except Exception:
                logger.warning("YouTube search for %r failed, skipping", keyword)
                continue

            if not info:
                continue

            entries = info.get("entries", [])
            if not entries:
                continue

            for entry in entries:
                if entry is None:
                    continue

                url = entry.get("webpage_url", "") or entry.get("url", "")
                if not url:
                    continue
                if url in seen_urls:
                    continue
                seen_urls.add(url)

                title = entry.get("title", "") or ""
                description = entry.get("description", "") or ""
                summary = description[:500]

                # Parse upload date (YT returns YYYYMMDD string)
                published_at = _parse_upload_date(entry.get("upload_date", ""))

                view_count = entry.get("view_count") or entry.get("view_count_approx") or 0
                try:
                    view_count = int(view_count)
                except (ValueError, TypeError):
                    view_count = 0

                popularity = float(view_count)

                items.append(RawNewsItem(
                    title=title,
                    url=url,
                    summary=summary,
                    source_type=self.source_type,
                    source_name=self.source_name,
                    published_at=published_at,
                    popularity_raw=popularity,
                    metadata={
                        "views": view_count,
                        "channel": entry.get("channel", "") or entry.get("uploader", "") or "",
                        "duration": entry.get("duration", 0) or 0,
                        "like_count": entry.get("like_count", 0) or 0,
                    },
                ))

                if len(items) >= limit:
                    break

        return items[:limit]


def _parse_upload_date(date_str: str) -> datetime | None:
    """Convert YYYYMMDD (or other common formats) to datetime."""
    if not date_str:
        return None

    # yt-dlp returns YYYYMMDD
    if len(date_str) == 8 and date_str.isdigit():
        try:
            return datetime(
                year=int(date_str[0:4]),
                month=int(date_str[4:6]),
                day=int(date_str[6:8]),
                tzinfo=timezone.utc,
            )
        except (ValueError, IndexError):
            pass

    # Fallback: ISO format
    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"):
        try:
            dt = datetime.strptime(date_str.strip(), fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            continue

    return None
