"""Popularity scoring — raw scores per source type, cluster aggregation, fire tiers.

Standalone module: no database or external I/O dependencies.
Importable from clusterer and from any other pipeline stage.
"""

import math
from config import get_settings


# ---------------------------------------------------------------------------
# Source-type weight lookup — defaults for each source type
# ---------------------------------------------------------------------------
SOURCE_WEIGHTS: dict[str, float] = {
    "reddit": 1.0,
    "twitter": 0.9,
    "youtube": 0.8,
    "rss": 0.5,
    "scrape": 0.5,
}


def _get_source_weights() -> dict[str, float]:
    """Merge config-driven popularity weights with hard-coded defaults."""
    try:
        settings = get_settings()
        cfg = settings.popularity_weights  # dict[str, float]
    except Exception:
        cfg = {}
    merged = dict(SOURCE_WEIGHTS)
    merged.update(cfg)
    return merged


def normalize_raw_score(source_type: str, raw_value: float) -> float:
    """Normalize a raw popularity score from any source to 0-100 range.

    For text-heavy sources (rss, scrape) we use a fixed baseline because
    there is no meaningful engagement metric.  For social sources we apply
    a log scale that compresses large numbers into the 0-100 band.
    """
    if raw_value <= 0:
        return 0.0

    if source_type in ("rss", "scrape"):
        return 15.0  # fixed baseline

    # Logarithmic compression – e.g. 10 → ~21, 100 → ~40, 1000 → ~60, 100k → 100
    return min(100.0, math.log10(raw_value + 1) * 20)


def compute_item_score(source_type: str, raw_popularity: float) -> float:
    """Compute the weighted popularity score for a single news item.

    Returns a float in roughly the 0-100 range (can slightly exceed 100 for
    extremely popular items on high-weight sources).
    """
    normalized = normalize_raw_score(source_type, raw_popularity)
    weights = _get_source_weights()
    weight = weights.get(source_type, 0.5)
    return normalized * weight


def compute_cluster_score(items: list[dict]) -> float:
    """Aggregate scores across all items in a cluster.

    Each *item* dict is expected to have at least:
        source_type    – str  (e.g. 'reddit', 'twitter', …)
        popularity_raw – float (raw metric: upvotes, likes, views, etc.)

    The raw sum of per-item scores is boosted by the number of distinct
    sources reporting the story, on the theory that more sources = more
    signal / higher real-world interest.
    """
    if not items:
        return 0.0

    total = sum(
        compute_item_score(item["source_type"], item["popularity_raw"])
        for item in items
    )

    # Diversity boost – logarithmic so the first few extra sources matter most
    return total * math.log(1 + len(items))


def get_fire_tier(score: float) -> int:
    """Map a cluster popularity score to a discrete *fire tier* (0-4).

    =====  =============  ==============================
    Tier   Score range    Visual / UX meaning
    =====  =============  ==============================
    4      ≥ 100          🔥🔥🔥🔥  breaking / viral
    3      60 – 99.99     🔥🔥🔥    very hot
    2      30 – 59.99     🔥🔥      trending
    1      10 – 29.99     🔥        warming up
    0      < 10           —        normal / cold
    =====  =============  ==============================
    """
    if score >= 100:
        return 4
    if score >= 60:
        return 3
    if score >= 30:
        return 2
    if score >= 10:
        return 1
    return 0
