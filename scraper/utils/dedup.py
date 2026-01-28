"""Deduplication utilities for opportunity matching."""

import re
from difflib import SequenceMatcher
from urllib.parse import urlparse, urlunparse


def normalize_url(url: str) -> str:
    """Normalize URL for comparison."""
    if not url:
        return ""
    parsed = urlparse(url.lower().strip())
    # Remove www prefix, trailing slashes, query params for matching
    netloc = parsed.netloc.replace("www.", "")
    path = parsed.path.rstrip("/")
    return urlunparse(("", netloc, path, "", "", ""))


def title_similarity(title1: str, title2: str) -> float:
    """Calculate similarity ratio between two titles."""
    if not title1 or not title2:
        return 0.0
    # Normalize titles for comparison
    t1 = re.sub(r"[^\w\s]", "", title1.lower())
    t2 = re.sub(r"[^\w\s]", "", title2.lower())
    return SequenceMatcher(None, t1, t2).ratio()


def is_duplicate(opp1: dict, opp2: dict, url_match: bool = True, title_threshold: float = 0.9) -> bool:
    """Check if two opportunities are duplicates."""
    # URL match
    if url_match and opp1.get("url") and opp2.get("url"):
        if normalize_url(opp1["url"]) == normalize_url(opp2["url"]):
            return True

    # Title similarity match
    if title_similarity(opp1.get("title", ""), opp2.get("title", "")) >= title_threshold:
        return True

    return False


def deduplicate(opportunities: list[dict], existing: list[dict] = None) -> list[dict]:
    """Remove duplicates from opportunities list, optionally checking against existing."""
    if existing is None:
        existing = []

    unique = []
    all_opps = existing + unique

    for opp in opportunities:
        is_dup = False
        for existing_opp in all_opps:
            if is_duplicate(opp, existing_opp):
                is_dup = True
                break
        if not is_dup:
            unique.append(opp)
            all_opps.append(opp)

    return unique
