"""Filtering utilities for relevance checking."""

from typing import Optional
import re

# Keywords indicating relevant opportunities for INDIVIDUAL journalists
RELEVANT_KEYWORDS = [
    "journalism", "journalist", "investigative", "reporting", "reporter",
    "nonfiction", "non-fiction", "essay", "essayist", "narrative",
    "literary", "longform", "long-form", "feature writing",
    "magazine writing", "documentary", "writer", "fellow",
    "public interest", "accountability", "watchdog"
]

# Keywords indicating irrelevant opportunities (fiction, etc.)
EXCLUDE_KEYWORDS = [
    "poetry", "poet", "fiction writing", "short story", "novel",
    "screenwriting", "screenplay", "playwriting", "playwright",
    "mfa program", "mfa degree", "creative writing mfa",
    "children's book", "young adult fiction", "romance writing"
]

# Keywords indicating grants for ORGANIZATIONS, not individuals
ORGANIZATION_KEYWORDS = [
    "media organization", "media organisations", "news organization",
    "news organisations", "newsroom", "news outlet", "media outlet",
    "consortium", "collaborative", "partnership", "media partners",
    "news partners", "cross-border collaboration", "media company",
    "media companies", "institutional", "organisational support",
    "organizational support", "media development", "outlet",
    "collaborations between", "news entities", "media entities",
    "independent media", "accelerator for media", "for media",
    "media sector", "media support", "civil society"
]

# Exact titles that are too generic (must match exactly after cleaning)
GENERIC_TITLES = [
    "tipsheet", "grantees", "fellowships", "grants", "awards",
    "opportunities", "resources", "about", "home", "contact"
]

# Patterns that indicate non-opportunity content
BAD_TITLE_PATTERNS = [
    "uphold democracy",  # Knight-Wallace tagline, not a title
]

# Types we want to track (for individuals)
VALID_TYPES = ["fellowship", "grant", "award", "prize", "fund", "scholarship", "funding"]

# Types to exclude
EXCLUDE_TYPES = ["newsletter", "article", "blog", "post"]


def is_for_organization(opportunity: dict) -> bool:
    """Check if an opportunity is meant for organizations, not individuals."""
    title = opportunity.get("title", "").lower()
    description = opportunity.get("description", "").lower()
    text = f"{title} {description}"

    # Check for organization-focused keywords
    for keyword in ORGANIZATION_KEYWORDS:
        if keyword in text:
            return True

    # Check funding size - very large amounts are usually for orgs
    funding_size = opportunity.get("funding_size", "")
    if funding_size:
        # Extract numeric value
        import re
        amounts = re.findall(r'[\d,]+(?:\.\d+)?', funding_size.replace(',', ''))
        for amount in amounts:
            try:
                value = float(amount.replace(',', ''))
                # Grants over 500k are almost always for organizations
                if value >= 500000:
                    return True
            except ValueError:
                pass

    return False


def is_relevant(opportunity: dict) -> bool:
    """Check if an opportunity is relevant for individual narrative journalists."""
    title = opportunity.get("title", "").lower()
    description = opportunity.get("description", "").lower()
    opp_type = opportunity.get("type", "").lower()
    text = f"{title} {description} {opp_type}"

    # Exclude newsletter/blog content types
    if opp_type in EXCLUDE_TYPES:
        return False

    # Exclude generic/bad titles
    title_clean = title.strip().lower().replace("»", "").strip()
    if len(title_clean) < 5:
        return False

    # Exact match for generic single-word titles
    if title_clean in GENERIC_TITLES:
        return False

    # Check for bad patterns (substrings)
    for pattern in BAD_TITLE_PATTERNS:
        if pattern in title_clean:
            return False

    # Exclude organization-focused opportunities
    if is_for_organization(opportunity):
        return False

    # Check for exclusion keywords (fiction, poetry, etc.)
    for keyword in EXCLUDE_KEYWORDS:
        if keyword in text:
            # Allow if it also has strong journalism keywords
            has_journalism = any(k in text for k in ["journalism", "journalist", "investigative", "reporting"])
            if not has_journalism:
                return False

    # Check for relevant keywords
    has_relevant = any(keyword in text for keyword in RELEVANT_KEYWORDS)

    # Check for valid type
    has_valid_type = any(t in opp_type for t in VALID_TYPES)

    return has_relevant or has_valid_type


def filter_relevant(opportunities: list[dict]) -> list[dict]:
    """Filter list to only relevant opportunities for individual journalists."""
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
