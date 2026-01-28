"""Scraper for J-school fellowships."""

import requests
from bs4 import BeautifulSoup
from typing import List
from datetime import datetime

JSCHOOL_SOURCES = [
    {
        "name": "Berkeley BCSP Ferriss Fellowship",
        "url": "https://fellowships.journalism.berkeley.edu/bcsp/",
        "type": "fellowship"
    },
    {
        "name": "NYU Matthew Power Award",
        "url": "https://journalism.nyu.edu/about-us/awards-and-fellowships/matthew-power-literary-reporting-award/",
        "type": "award"
    },
    {
        "name": "Columbia Journalism Fellowships",
        "url": "https://journalism.columbia.edu/fellowships",
        "type": "fellowship"
    },
    {
        "name": "Knight-Wallace Fellowships",
        "url": "https://wallacehouse.umich.edu/knight-wallace/",
        "type": "fellowship"
    },
    {
        "name": "Nieman Fellowships",
        "url": "https://nieman.harvard.edu/fellowships/",
        "type": "fellowship"
    },
    {
        "name": "USC Annenberg Fellowships",
        "url": "https://annenberg.usc.edu/journalism/fellowships",
        "type": "fellowship"
    },
    {
        "name": "Northwestern Medill Fellowships",
        "url": "https://www.medill.northwestern.edu/professional-education/",
        "type": "fellowship"
    },
]


def scrape() -> List[dict]:
    """Scrape J-school fellowship pages."""
    opportunities = []

    for source in JSCHOOL_SOURCES:
        try:
            response = requests.get(source["url"], timeout=30)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")

            # Get page title and description
            title = soup.select_one("h1, .page-title, .entry-title")
            title_text = title.get_text(strip=True) if title else source["name"]

            # Get main content for description
            content = soup.select_one("main, .content, article, .entry-content")
            description = ""
            if content:
                paragraphs = content.select("p")
                if paragraphs:
                    description = " ".join(p.get_text(strip=True) for p in paragraphs[:2])
                    if len(description) > 500:
                        description = description[:497] + "..."

            # Look for deadline information
            deadline = None
            deadline_elem = soup.select_one(".deadline, .date, [class*='deadline']")
            if deadline_elem:
                deadline = deadline_elem.get_text(strip=True)

            opportunities.append({
                "title": title_text,
                "url": source["url"],
                "description": description,
                "source": source["name"],
                "source_url": source["url"],
                "type": source["type"],
                "scraped_at": datetime.utcnow().isoformat(),
                "deadline": deadline,
            })

        except requests.RequestException as e:
            print(f"Error scraping {source['name']}: {e}")
            # Still add the source with basic info
            opportunities.append({
                "title": source["name"],
                "url": source["url"],
                "description": f"Visit {source['url']} for more information.",
                "source": source["name"],
                "source_url": source["url"],
                "type": source["type"],
                "scraped_at": datetime.utcnow().isoformat(),
                "deadline": None,
                "scrape_error": str(e),
            })

    return opportunities
