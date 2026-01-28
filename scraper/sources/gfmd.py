"""Scraper for GFMD Funding Database."""

import re
import requests
from bs4 import BeautifulSoup
from typing import List, Optional
from datetime import datetime

SOURCE_URL = "https://gfmd.info/fundings/"
SOURCE_NAME = "GFMD"


def parse_gfmd_text(raw_text: str) -> dict:
    """Parse GFMD listing text that contains concatenated metadata.

    Example input:
    "Media Forward Fund for independent media in DACH regionOrganisation:Media Forward FundRegion:Europe...Status:OpenDeadline:20/02/2026Type:GrantFunding Size:€200,000"

    Returns dict with parsed fields.
    """
    result = {
        "title": raw_text,
        "organisation": None,
        "region": None,
        "deadline": None,
        "funding_type": None,
        "funding_size": None,
    }

    # Check if this text contains the metadata pattern
    if "Organisation:" not in raw_text:
        return result

    # Extract title (everything before "Organisation:")
    title_match = re.match(r'^(.+?)Organisation:', raw_text)
    if title_match:
        result["title"] = title_match.group(1).strip()

    # Extract Organisation
    org_match = re.search(r'Organisation:([^R]+?)(?:Region:|$)', raw_text)
    if org_match:
        result["organisation"] = org_match.group(1).strip()

    # Extract Region
    region_match = re.search(r'Region:([^S]+?)(?:Status:|$)', raw_text)
    if region_match:
        result["region"] = region_match.group(1).strip()

    # Extract Deadline
    deadline_match = re.search(r'Deadline:([^T]+?)(?:Type:|$)', raw_text)
    if deadline_match:
        deadline_str = deadline_match.group(1).strip()
        if deadline_str.lower() != "ongoing":
            result["deadline"] = deadline_str

    # Extract Type
    type_match = re.search(r'Type:([^F]+?)(?:Funding Size:|$)', raw_text)
    if type_match:
        result["funding_type"] = type_match.group(1).strip()

    # Extract Funding Size
    size_match = re.search(r'Funding Size:(.+)$', raw_text)
    if size_match:
        result["funding_size"] = size_match.group(1).strip()

    return result


def scrape() -> List[dict]:
    """Scrape GFMD funding database."""
    opportunities = []

    try:
        response = requests.get(SOURCE_URL, timeout=30)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        # GFMD uses a funding listing structure
        listings = soup.select(".funding-item, .post, article, .listing")

        for listing in listings:
            title_elem = listing.select_one("h2, h3, .funding-title, a")
            link_elem = listing.select_one("a[href]")

            if not title_elem:
                continue

            raw_text = title_elem.get_text(strip=True)
            url = link_elem.get("href", "") if link_elem else ""

            if not raw_text:
                continue

            # Parse the concatenated text into separate fields
            parsed = parse_gfmd_text(raw_text)

            if not parsed["title"]:
                continue

            opportunities.append({
                "title": parsed["title"],
                "url": url,
                "description": "",  # Will be filled from individual pages if needed
                "source": SOURCE_NAME,
                "source_url": SOURCE_URL,
                "type": parsed["funding_type"] or "funding",
                "scraped_at": datetime.utcnow().isoformat(),
                "deadline": parsed["deadline"],
                "organisation": parsed["organisation"],
                "region": parsed["region"],
                "funding_size": parsed["funding_size"],
            })

    except requests.RequestException as e:
        print(f"Error scraping {SOURCE_NAME}: {e}")

    return opportunities
