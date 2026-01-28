"""Filtering utilities for relevance checking."""

from typing import Optional
import re

# Keywords indicating relevant opportunities
RELEVANT_KEYWORDS = [
    "journalism", "journalist", "investigative", "reporting", "reporter",
    "nonfiction", "non-fiction", "essay", "essayist", "narrative",
    "literary", "longform", "long-form", "feature writing",
    "magazine writing", "news", "media", "documentary",
    "public interest", "accountability", "watchdog"
]

# Keywords indicating irrelevant opportunities
EXCLUDE_KEYWORDS = [
    "poetry", "poet", "fiction writing", "short story", "novel",
    "screenwriting", "screenplay", "playwriting", "playwright",
    "mfa program", "mfa degree", "creative writing mfa",
    "children's book", "young adult fiction", "romance writing"
]

# Types we want to track
VALID_TYPES = ["fellowship", "grant", "award", "prize", "fund", "scholarship"]


def is_relevant(opportunity: dict) -> bool:
    """Check if an opportunity is relevant for narrative journalism/nonfiction."""
    title = opportunity.get("title", "").lower()
    description = opportunity.get("description", "").lower()
    opp_type = opportunity.get("type", "").lower()
    text = f"{title} {description} {opp_type}"

    # Check for exclusion keywords first
    for keyword in EXCLUDE_KEYWORDS:
        if keyword in text:
            # Allow if it also has strong journalism keywords
            has_journalism = any(k in text for k in ["journalism", "journalist", "investigative", "reporting"])
            if not has_journalism:
                return False

    # Check for relevant keywords
    has_relevant = any(keyword in text for keyword in RELEVANT_KEYWORDS)

    # Check for valid type
    has_valid_type = any(t in text for t in VALID_TYPES)

    return has_relevant or has_valid_type


def filter_relevant(opportunities: list[dict]) -> list[dict]:
    """Filter list to only relevant opportunities."""
    return [opp for opp in opportunities if is_relevant(opp)]


def extract_deadline(text: str) -> Optional[str]:
    """Try to extract a deadline date from text."""
    # Common date patterns
    patterns = [
        r"deadline[:\s]+(\w+\s+\d{1,2},?\s+\d{4})",
        r"due[:\s]+(\w+\s+\d{1,2},?\s+\d{4})",
        r"closes?[:\s]+(\w+\s+\d{1,2},?\s+\d{4})",
        r"(\w+\s+\d{1,2},?\s+\d{4})\s+deadline",
        r"by\s+(\w+\s+\d{1,2},?\s+\d{4})",
    ]

    text_lower = text.lower()
    for pattern in patterns:
        match = re.search(pattern, text_lower, re.IGNORECASE)
        if match:
            return match.group(1).strip()

    return None
