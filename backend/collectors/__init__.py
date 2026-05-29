"""Collectors package — one module per source type."""

from .base import BaseCollector, RawNewsItem
from .reddit import RedditCollector
from .twitter import TwitterCollector
from .youtube import YouTubeCollector
from .rss import RSSCollector
from .scraper import ScraperCollector

__all__ = [
    "BaseCollector",
    "RawNewsItem",
    "RedditCollector",
    "TwitterCollector",
    "YouTubeCollector",
    "RSSCollector",
    "ScraperCollector",
]

# Registry: map source type string → collector class
COLLECTOR_REGISTRY: dict[str, type[BaseCollector]] = {
    "reddit": RedditCollector,
    "twitter": TwitterCollector,
    "youtube": YouTubeCollector,
    "rss": RSSCollector,
    "scrape": ScraperCollector,
}
