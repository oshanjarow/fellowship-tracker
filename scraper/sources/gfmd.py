"""Scraper for GFMD Funding Database."""

import requests
from bs4 import BeautifulSoup
from typing import List
from datetime import datetime

SOURCE_URL = "https://gfmd.info/fundings/"
SOURCE_NAME = "GFMD"


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
            desc_elem = listing.select_one("p, .excerpt, .funding-description")
            deadline_elem = listing.select_one(".deadline, .date, time")

            if not title_elem:
                continue

            title = title_elem.get_text(strip=True)
            url = link_elem.get("href", "") if link_elem else ""
            description = desc_elem.get_text(strip=True) if desc_elem else ""
            deadline = deadline_elem.get_text(strip=True) if deadline_elem else None

            if not title:
                continue

            opportunities.append({
                "title": title,
                "url": url,
                "description": description,
                "source": SOURCE_NAME,
                "source_url": SOURCE_URL,
                "type": "funding",
                "scraped_at": datetime.utcnow().isoformat(),
                "deadline": deadline,
            })

    except requests.RequestException as e:
        print(f"Error scraping {SOURCE_NAME}: {e}")

    return opportunities
