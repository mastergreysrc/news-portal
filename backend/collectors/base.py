"""Base collector classes — abstract collector and raw item model."""

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class RawNewsItem:
    """Raw news item collected from a source, before processing/dedup."""

    title: str
    url: str
    summary: str = ""
    source_type: str = ""
    source_name: str = ""
    published_at: Optional[datetime] = None
    popularity_raw: float = 0.0
    metadata: dict = field(default_factory=dict)


class BaseCollector(ABC):
    """Abstract base for all source-type collectors."""

    source_type: str = "generic"

    def __init__(self, source_config, category_id: int, category_name: str):
        self.source_config = source_config  # SourceConfig from config.py
        self.category_id = category_id
        self.category_name = category_name
        self.source_name = source_config.name
        self.config: dict = source_config.config  # shortcut to source-specific config

    @abstractmethod
    async def collect(self) -> list[RawNewsItem]:
        """Fetch and return raw news items from this source."""
        ...
