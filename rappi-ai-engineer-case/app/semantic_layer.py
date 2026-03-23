"""
semantic_layer.py — Business entity resolution and metric alias matching.
This is the "dictionary" between user language and structured data.
No LLM needed here — all deterministic lookup logic.
"""

import re
from difflib import get_close_matches
from utils import load_metric_dictionary

_DICT = None


def _get_dict():
    global _DICT
    if _DICT is None:
        _DICT = load_metric_dictionary()
    return _DICT


# ──────────────────────────────────────────────
# Metric resolution
# ──────────────────────────────────────────────
def resolve_metric(raw: str) -> str | None:
    """
    Given a user-provided metric name (possibly fuzzy), return the canonical metric name.
    Returns None if no match found.
    """
    if not raw:
        return None
    d = _get_dict()
    raw_lower = raw.lower().strip()

    # Direct canonical match
    for canonical in d["metrics"]:
        if raw_lower == canonical.lower():
            return canonical

    # Alias match
    for canonical, info in d["metrics"].items():
        for alias in info.get("aliases", []):
            if raw_lower == alias.lower():
                return canonical

    # Partial/fuzzy — check if raw appears inside canonical or alias
    for canonical, info in d["metrics"].items():
        if raw_lower in canonical.lower():
            return canonical
        for alias in info.get("aliases", []):
            if raw_lower in alias.lower() or alias.lower() in raw_lower:
                return canonical

    # Last resort: fuzzy match against all aliases
    all_aliases = []
    alias_to_canonical = {}
    for canonical, info in d["metrics"].items():
        for alias in info.get("aliases", []):
            all_aliases.append(alias)
            alias_to_canonical[alias] = canonical

    matches = get_close_matches(raw_lower, all_aliases, n=1, cutoff=0.6)
    if matches:
        return alias_to_canonical[matches[0]]

    return None


# ──────────────────────────────────────────────
# Country resolution
# ──────────────────────────────────────────────
def resolve_country(raw: str) -> str | None:
    """Returns 2-letter country code or None."""
    if not raw:
        return None
    d = _get_dict()
    raw_lower = raw.lower().strip()
    for code, aliases in d["countries"].items():
        if raw_lower in aliases or raw_lower == code.lower():
            return code
    return None


# ──────────────────────────────────────────────
# Zone type resolution
# ──────────────────────────────────────────────
def resolve_zone_type(raw: str) -> str | None:
    if not raw:
        return None
    d = _get_dict()
    raw_lower = raw.lower().strip()
    for canonical, aliases in d["zone_types"].items():
        if raw_lower in aliases:
            return canonical
    # partial
    if "wealthy" in raw_lower and "non" not in raw_lower:
        return "Wealthy"
    if "non" in raw_lower or "no" in raw_lower:
        return "Non Wealthy"
    return None


# ──────────────────────────────────────────────
# Zone prioritization resolution
# ──────────────────────────────────────────────
def resolve_prioritization(raw: str) -> str | None:
    if not raw:
        return None
    d = _get_dict()
    raw_lower = raw.lower().strip()
    for canonical, aliases in d["zone_prioritization"].items():
        if raw_lower in aliases:
            return canonical
    if "high" in raw_lower:
        return "High Priority"
    if "not" in raw_lower or "sin" in raw_lower or "no " in raw_lower:
        return "Not Prioritized"
    if "priorit" in raw_lower:
        return "Prioritized"
    return None


# ──────────────────────────────────────────────
# Week scope resolution
# ──────────────────────────────────────────────
def resolve_week_scope(raw: str) -> dict:
    """
    Returns {"type": "single"|"range", "week": "L0W"} or {"type": "range", "start": "L5W", "end": "L0W"}
    Default: current week (L0W)
    """
    if not raw:
        return {"type": "single", "week": "L0W"}

    raw_lower = raw.lower()

    # "last N weeks" / "últimas N semanas"
    m = re.search(r"(?:last|últimas?|ultimas?)\s*(\d+)\s*(?:weeks?|semanas?)", raw_lower)
    if m:
        n = int(m.group(1))
        n = min(n, 8)
        start_label = f"L{n}W"
        return {"type": "range", "start": start_label, "end": "L0W", "n_weeks": n}

    # "8 weeks" / "8 semanas"
    m = re.search(r"(\d+)\s*(?:weeks?|semanas?)", raw_lower)
    if m:
        n = int(m.group(1))
        n = min(n, 8)
        start_label = f"L{n}W"
        return {"type": "range", "start": start_label, "end": "L0W", "n_weeks": n}

    # "this week" / "current" / "esta semana"
    if any(k in raw_lower for k in ["esta semana", "this week", "current", "actual", "ahora"]):
        return {"type": "single", "week": "L0W"}

    # "last week"
    if any(k in raw_lower for k in ["last week", "semana pasada"]):
        return {"type": "single", "week": "L1W"}

    # Default to L0W
    return {"type": "single", "week": "L0W"}


# ──────────────────────────────────────────────
# Business concept detection
# ──────────────────────────────────────────────
def detect_business_concept(text: str) -> str | None:
    """
    Detects high-level business concepts from free text.
    Returns a concept key or None.
    """
    text_lower = text.lower()
    if any(k in text_lower for k in ["problemáticas", "problematicas", "problem", "deterioradas", "malas"]):
        return "zonas_problematicas"
    if any(k in text_lower for k in ["alto lead", "high lead", "buen lead"]) and \
       any(k in text_lower for k in ["bajo perfect", "low perfect", "mal perfect"]):
        return "alto_lead_bajo_perfect"
    if any(k in text_lower for k in ["crecen", "crecimiento", "growing", "fastest", "más crecen"]):
        return "zonas_en_crecimiento"
    return None


# ──────────────────────────────────────────────
# Expose higher_is_better for a metric
# ──────────────────────────────────────────────
def is_higher_better(metric: str) -> bool:
    d = _get_dict()
    info = d["metrics"].get(metric, {})
    return info.get("higher_is_better", True)


def get_all_canonical_metrics() -> list:
    d = _get_dict()
    return list(d["metrics"].keys())
