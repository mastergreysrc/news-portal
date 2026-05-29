"""Config-driven web scraper for sites without RSS feeds.

Uses httpx (async) for HTTP requests and BeautifulSoup4 for HTML parsing.
Supports CSS selectors for article containers, titles, links, and summaries.
"""

import random
import httpx
from bs4 import BeautifulSoup
from urllib.parse import urljoin

from .base import BaseCollector, RawNewsItem

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
]


class ScraperCollector(BaseCollector):
    """Generic config-driven web scraper using httpx + BeautifulSoup4.

    Source config keys (in config.yaml under the source's config dict):
        url              — page URL to scrape
        article_selector — CSS selector for each article container
        title_selector   — CSS selector for the title element (within article)
        link_selector    — CSS selector for the link element (within article)
        summary_selector — optional CSS selector for summary text
        limit            — max articles to return (default: 15)
    """

    source_type = "scrape"

    async def collect(self) -> list[RawNewsItem]:
        """Fetch and parse articles from the configured URL.

        Returns an empty list on any HTTP or parsing failure — never raises.
        """
        url = self.config["url"]
        article_sel = self.config["article_selector"]
        title_sel = self.config["title_selector"]
        link_sel = self.config["link_selector"]
        summary_sel = self.config.get("summary_selector")
        limit = self.config.get("limit", 15)

        headers = {"User-Agent": random.choice(USER_AGENTS)}

        try:
            async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
                response = await client.get(url, headers=headers)
                response.raise_for_status()
        except httpx.HTTPError:
            return []

        soup = BeautifulSoup(response.text, "html.parser")
        articles = soup.select(article_sel)[:limit]

        items: list[RawNewsItem] = []
        for article in articles:
            title_el = article.select_one(title_sel)
            link_el = article.select_one(link_sel)

            if not title_el or not link_el:
                continue

            title = title_el.get_text(strip=True)
            href = link_el.get("href", "")
            article_url = urljoin(url, href)

            summary = ""
            if summary_sel:
                summary_el = article.select_one(summary_sel)
                if summary_el:
                    summary = summary_el.get_text(strip=True)[:500]

            items.append(RawNewsItem(
                title=title,
                url=article_url,
                summary=summary,
                source_name=self.source_name,
                source_type="scrape",
                popularity_raw=15.0,
            ))

        return items
