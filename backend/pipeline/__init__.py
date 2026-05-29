"""Pipeline package — collect, normalize, deduplicate, translate, cluster, score."""

from .normalizer import normalize_url
from .deduplicator import find_duplicate
from .translator import translate_and_summarize
from .clusterer import create_singleton_cluster, add_to_cluster
from .scorer import compute_item_score, compute_cluster_score, get_fire_tier
from .orchestrator import run_pipeline, ensure_categories_and_sources, get_sources_for_category

__all__ = [
    "normalize_url",
    "find_duplicate",
    "translate_and_summarize",
    "create_singleton_cluster",
    "add_to_cluster",
    "compute_item_score",
    "compute_cluster_score",
    "get_fire_tier",
    "run_pipeline",
    "ensure_categories_and_sources",
    "get_sources_for_category",
]
