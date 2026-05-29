"""Reddit collector — uses PRAW (free read-only mode, no API key needed)."""

import asyncio
import logging
from datetime import datetime
from typing import Optional

from .base import BaseCollector, RawNewsItem

logger = logging.getLogger(__name__)


class RedditCollector(BaseCollector):
    """Collects posts from a subreddit using PRAW."""

    source_type = "reddit"

    async def collect(self) -> list[RawNewsItem]:
        """Fetch hot/new posts from the configured subreddit."""
        subreddit = self.config.get("subreddit", "")
        limit = self.config.get("limit", 25)
        sort = self.config.get("sort", "hot")

        if not subreddit:
            logger.warning("RedditCollector: no subreddit configured")
            return []

        try:
            reddit = await self._get_reddit_client()
            sub = await asyncio.to_thread(reddit.subreddit, subreddit)

            if sort == "new":
                submissions = await asyncio.to_thread(lambda: list(sub.new(limit=limit)))
            else:
                submissions = await asyncio.to_thread(lambda: list(sub.hot(limit=limit)))

            items = []
            for submission in submissions:
                if submission.stickied:
                    continue  # skip pinned posts

                published_at = datetime.fromtimestamp(submission.created_utc)
                items.append(
                    RawNewsItem(
                        title=submission.title,
                        url=f"https://reddit.com{submission.permalink}",
                        summary=(submission.selftext or "")[:500] or None,
                        source_type="reddit",
                        source_name=self.source_name,
                        published_at=published_at,
                        popularity_raw=float(submission.score + submission.num_comments),
                        metadata={
                            "score": submission.score,
                            "num_comments": submission.num_comments,
                            "author": str(submission.author) if submission.author else "[deleted]",
                            "subreddit": subreddit,
                        },
                    )
                )

            logger.info(
                "Reddit: fetched %d items from r/%s (sort=%s)",
                len(items), subreddit, sort,
            )
            return items

        except Exception as e:
            logger.error("RedditCollector failed for r/%s: %s", subreddit, e)
            return []

    async def _get_reddit_client(self):
        """Create PRAW Reddit instance — read-only mode if no credentials."""
        import praw

        # Try to get credentials from settings
        try:
            from config import get_settings
            settings = get_settings()
            client_id = settings.reddit_client_id
            client_secret = settings.reddit_client_secret
            user_agent = settings.reddit_user_agent
        except Exception:
            client_id = ""
            client_secret = ""
            user_agent = "GamingNewsPL/1.0"

        if client_id and client_secret:
            return praw.Reddit(
                client_id=client_id,
                client_secret=client_secret,
                user_agent=user_agent,
            )
        else:
            logger.debug("Reddit: no credentials — using read-only mode")
            return praw.Reddit(user_agent=user_agent, read_only=True)
