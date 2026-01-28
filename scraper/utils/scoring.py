"""Relevance scoring for personalized opportunity ranking."""

import re
from typing import Optional

# Keywords related to user's interests (higher weight = more relevant)
INTEREST_KEYWORDS = {
    # Consciousness, meditation, psychedelics (high priority)
    "consciousness": 10,
    "psychedelic": 10,
    "psychedelics": 10,
    "meditation": 10,
    "contemplative": 8,
    "mind": 5,
    "neuroscience": 6,
    "brain": 5,
    "mental health": 6,
    "psychology": 4,
    "philosophy": 6,
    "phenomenology": 8,

    # Political economy, anti-poverty (high priority)
    "poverty": 10,
    "anti-poverty": 10,
    "economic justice": 10,
    "inequality": 8,
    "basic income": 10,
    "universal basic": 10,
    "ubi": 10,
    "welfare": 6,
    "social policy": 8,
    "policy": 4,
    "political economy": 10,
    "economics": 5,
    "labor": 5,
    "workers": 5,
    "progressive": 6,

    # Science writing
    "science": 5,
    "scientific": 4,
    "research": 3,

    # Narrative/longform (general relevance)
    "narrative": 4,
    "longform": 4,
    "long-form": 4,
    "literary": 4,
    "nonfiction": 3,
    "non-fiction": 3,
    "essay": 3,
    "feature": 2,
}

# US-based indicators (boost score)
US_INDICATORS = [
    "north america",
    "united states",
    "u.s.",
    "us-based",
    "american",
]

# Global/international indicators (slight penalty for non-US focus)
GLOBAL_INDICATORS = [
    "eastern europe",
    "africa",
    "asia",
    "latin america",
    "middle east",
    "european union",
    "eu countries",
    "ukraine",
    "global south",
]


def calculate_relevance_score(opportunity: dict) -> int:
    """Calculate a relevance score for an opportunity based on user interests.

    Higher score = more relevant to user's interests.
    """
    score = 0

    # Combine all text fields for keyword matching
    title = opportunity.get("title", "").lower()
    description = opportunity.get("description", "").lower()
    region = opportunity.get("region", "").lower() if opportunity.get("region") else ""
    org = opportunity.get("organisation", "").lower() if opportunity.get("organisation") else ""

    text = f"{title} {description} {org}"

    # Check for interest keywords
    for keyword, weight in INTEREST_KEYWORDS.items():
        if keyword in text:
            score += weight
            # Bonus if keyword is in title (more directly relevant)
            if keyword in title:
                score += weight // 2

    # US-based boost
    is_us_based = False
    for indicator in US_INDICATORS:
        if indicator in region or indicator in text:
            is_us_based = True
            score += 15
            break

    # No region often means US-based or open to US applicants
    if not region or region.strip() == "":
        score += 5

    # Slight penalty for explicitly non-US focused opportunities
    if not is_us_based:
        for indicator in GLOBAL_INDICATORS:
            if indicator in region:
                score -= 5
                break

    # Bonus for having a deadline (more actionable)
    if opportunity.get("deadline"):
        score += 3

    # Bonus for having funding amount listed
    if opportunity.get("funding_size"):
        score += 2

    return max(0, score)  # Don't go negative


def add_relevance_scores(opportunities: list[dict]) -> list[dict]:
    """Add relevance_score field to each opportunity."""
    for opp in opportunities:
        opp["relevance_score"] = calculate_relevance_score(opp)
    return opportunities
