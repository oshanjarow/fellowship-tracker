#!/usr/bin/env python3
"""Main scraper orchestrator for fellowship/grant tracker."""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple, List

from sources import gijn, gfmd, fundsforwriters, rss_feeds, jschools, direct, discovery
from utils.dedup import deduplicate
from utils.filter import filter_relevant
from utils.scoring import add_relevance_scores

# Paths
SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR.parent / "data"
OPPORTUNITIES_FILE = DATA_DIR / "opportunities.json"
ARCHIVE_FILE = DATA_DIR / "archive.json"


def load_json(path: Path) -> list[dict]:
    """Load JSON file or return empty list."""
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return []


def save_json(path: Path, data: list) -> None:
    """Save data to JSON file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2, default=str)


def parse_deadline(deadline_str: Optional[str]) -> Optional[datetime]:
    """Try to parse a deadline string into a datetime."""
    if not deadline_str:
        return None

    from dateutil import parser
    try:
        return parser.parse(deadline_str, fuzzy=True)
    except (ValueError, TypeError):
        return None


def is_expired(opportunity: dict) -> bool:
    """Check if an opportunity has expired."""
    deadline = parse_deadline(opportunity.get("deadline"))
    if deadline:
        return deadline < datetime.now()
    return False


def archive_expired(opportunities: List[dict], archive: List[dict]) -> Tuple[List[dict], List[dict]]:
    """Move expired opportunities to archive."""
    active = []
    newly_archived = []

    for opp in opportunities:
        if is_expired(opp):
            opp["archived_at"] = datetime.utcnow().isoformat()
            newly_archived.append(opp)
        else:
            active.append(opp)

    return active, archive + newly_archived


def main():
    """Run all scrapers and update data files."""
    print("=" * 60)
    print(f"Fellowship & Grant Tracker - Scrape Run")
    print(f"Started: {datetime.utcnow().isoformat()}")
    print("=" * 60)

    # Load existing data
    existing = load_json(OPPORTUNITIES_FILE)
    archive = load_json(ARCHIVE_FILE)
    print(f"\nLoaded {len(existing)} existing opportunities, {len(archive)} archived")

    # Run all scrapers
    all_scraped = []

    scrapers = [
        ("GIJN", gijn.scrape),
        ("GFMD", gfmd.scrape),
        ("FundsForWriters", fundsforwriters.scrape),
        ("RSS Feeds", rss_feeds.scrape),
        ("J-Schools", jschools.scrape),
        ("Direct Sources", direct.scrape),
        ("Discovered Sources", discovery.scrape),
    ]

    # Run source discovery (finds new sources for future scrapes)
    print("\n[Discovery] Searching for new sources...")
    try:
        new_sources = discovery.discover_sources(max_new=10)
        print(f"[Discovery] Found {len(new_sources)} new potential sources")
    except Exception as e:
        print(f"[Discovery] ERROR: {e}")

    for name, scraper in scrapers:
        print(f"\n[{name}] Scraping...")
        try:
            results = scraper()
            print(f"[{name}] Found {len(results)} items")
            all_scraped.extend(results)
        except Exception as e:
            print(f"[{name}] ERROR: {e}")

    print(f"\n{'=' * 60}")
    print(f"Total scraped: {len(all_scraped)}")

    # Filter for relevance
    relevant = filter_relevant(all_scraped)
    print(f"After relevance filter: {len(relevant)}")

    # Deduplicate against existing
    new_opps = deduplicate(relevant, existing)
    print(f"New unique opportunities: {len(new_opps)}")

    # Merge with existing
    merged = existing + new_opps

    # Archive expired
    active, updated_archive = archive_expired(merged, archive)
    print(f"Active opportunities: {len(active)}")
    print(f"Total archived: {len(updated_archive)}")

    # Add relevance scores based on user interests
    active = add_relevance_scores(active)

    # Sort by relevance score (high first), then by deadline (soon first)
    def sort_key(opp):
        score = opp.get("relevance_score", 0)
        deadline = parse_deadline(opp.get("deadline"))
        # Primary: negative score (so higher scores come first)
        # Secondary: deadline (None deadlines at end)
        if deadline:
            return (-score, 0, deadline)
        return (-score, 1, datetime.max)

    active.sort(key=sort_key)

    # Save updated data
    save_json(OPPORTUNITIES_FILE, active)
    save_json(ARCHIVE_FILE, updated_archive)

    print(f"\n{'=' * 60}")
    print(f"Completed: {datetime.utcnow().isoformat()}")
    print(f"Data saved to {OPPORTUNITIES_FILE}")
    print("=" * 60)

    # Print summary of opportunities
    if active:
        print("\n--- Active Opportunities ---")
        for i, opp in enumerate(active[:10], 1):
            deadline = opp.get("deadline", "No deadline")
            print(f"{i}. {opp['title'][:50]}... [{opp['source']}] - {deadline}")
        if len(active) > 10:
            print(f"... and {len(active) - 10} more")


if __name__ == "__main__":
    main()
