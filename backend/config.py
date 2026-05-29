"""Configuration — load from config.yaml + .env via Pydantic."""

import os
import copy
from pathlib import Path
from typing import Optional
from functools import lru_cache

import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings


# ---- Source & Category models ----

class SourceConfig(BaseModel):
    type: str  # reddit, twitter, youtube, rss, scrape
    name: str
    config: dict = Field(default_factory=dict)


class CategoryConfig(BaseModel):
    name: str
    slug: str
    icon: str = "📰"
    sources: list[SourceConfig] = Field(default_factory=list)


# ---- Settings ----

class Settings(BaseSettings):
    """Application settings loaded from config.yaml then .env."""

    # App
    app_name: str = "News Portal"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    app_secret_key: str = "change-me"

    # Database
    database_url: str = ""

    # Schedule
    schedule_runs_per_day: int = 2
    schedule_times: list[str] = Field(default_factory=lambda: ["08:00", "20:00"])
    schedule_timezone: str = "Europe/Warsaw"

    # Translation
    translation_provider: str = "groq"
    translation_source_lang: str = "EN"
    translation_target_lang: str = "PL"

    # Summarization (Groq)
    summarization_enabled: bool = True
    summarization_provider: str = "groq"
    summarization_endpoint: str = "https://api.groq.com/openai/v1"
    summarization_api_key: str = ""
    summarization_model: str = "llama-3.1-8b-instant"

    # Telegram
    telegram_push_enabled: bool = False
    telegram_chat_id: str = ""
    telegram_push_mode: str = "digest"

    # Deduplication
    dedup_title_similarity_threshold: float = 0.75
    dedup_lookback_days: int = 3

    # Popularity weights
    pop_reddit_weight: float = 1.0
    pop_twitter_weight: float = 0.9
    pop_youtube_weight: float = 0.8
    pop_rss_weight: float = 0.5
    pop_scrape_weight: float = 0.5

    # Admin
    admin_key: str = "change-me"

    # Categories (from config.yaml)
    categories: list[CategoryConfig] = Field(default_factory=list)

    # API keys (from .env)
    groq_api_key: str = ""
    reddit_client_id: str = ""
    reddit_client_secret: str = ""
    reddit_user_agent: str = "GamingNewsPL/1.0"

    @property
    def popularity_weights(self) -> dict[str, float]:
        return {
            "reddit": self.pop_reddit_weight,
            "twitter": self.pop_twitter_weight,
            "youtube": self.pop_youtube_weight,
            "rss": self.pop_rss_weight,
            "scrape": self.pop_scrape_weight,
        }

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


def _load_config_yaml(yaml_path: str | None = None) -> dict:
    """Load config.yaml and return a flat dict of settings."""
    if yaml_path is None:
        # Look for config.yaml relative to the project root (one level above backend/)
        yaml_path = Path(__file__).resolve().parent.parent / "config.yaml"

    if not Path(yaml_path).exists():
        return {}

    with open(yaml_path) as f:
        raw = yaml.safe_load(f) or {}

    flat: dict = {}

    # Flatten nested keys: app.name → app_name
    for section, values in raw.items():
        if isinstance(values, dict):
            for k, v in values.items():
                flat[f"{section}_{k}"] = v
        elif section == "categories" and isinstance(values, list):
            flat["categories"] = values
        else:
            flat[section] = values

    # Handle env-var references like "${GROQ_API_KEY}"
    for k, v in flat.items():
        if isinstance(v, str) and v.startswith("${") and v.endswith("}"):
            env_var = v[2:-1]
            flat[k] = os.getenv(env_var, "")

    return flat


@lru_cache()
def get_settings() -> Settings:
    """Return cached Settings instance (loads config.yaml once)."""
    yaml_data = _load_config_yaml()

    # Build category models
    categories_raw = yaml_data.pop("categories", [])
    categories = []
    for cat_raw in categories_raw:
        sources = []
        for src_raw in cat_raw.get("sources", []):
            sources.append(SourceConfig(**src_raw))
        categories.append(CategoryConfig(
            name=cat_raw["name"],
            slug=cat_raw.get("slug", cat_raw["name"].lower()),
            icon=cat_raw.get("icon", "📰"),
            sources=sources,
        ))

    # Merge env overrides on top of YAML
    settings = Settings(
        categories=categories,
        **{k: v for k, v in yaml_data.items() if k in Settings.model_fields},
    )
    return settings
