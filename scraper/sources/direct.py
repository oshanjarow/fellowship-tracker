"""Direct page scrapers for specific organizations."""

import requests
from bs4 import BeautifulSoup
from typing import List
from datetime import datetime

DIRECT_SOURCES = [
    {
        "name": "NEA Creative Writing Fellowships",
        "url": "https://www.arts.gov/grants/creative-writing-fellowships",
        "type": "fellowship"
    },
    {
        "name": "Whiting Foundation",
        "url": "https://www.whiting.org/writers/creative-nonfiction-grant",
        "type": "grant"
    },
    {
        "name": "Fund for Investigative Journalism",
        "url": "https://fij.org/grants/",
        "type": "grant"
    },
    {
        "name": "PEN America Literary Awards",
        "url": "https://pen.org/literary-awards/",
        "type": "award"
    },
]


def scrape() -> List[dict]:
    """Scrape direct organization pages."""
    opportunities = []

    for source in DIRECT_SOURCES:
        try:
            response = requests.get(source["url"], timeout=30)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")

            # Get page title
            title = soup.select_one("h1, .page-title, title")
            title_text = title.get_text(strip=True) if title else source["name"]

            # Clean up title from <title> tag
            if " | " in title_text:
                title_text = title_text.split(" | ")[0]
            if " - " in title_text:
                title_text = title_text.split(" - ")[0]

            # Get main content for description
            content = soup.select_one("main, .content, article, #content")
            description = ""
            if content:
                paragraphs = content.select("p")
                if paragraphs:
                    description = " ".join(p.get_text(strip=True) for p in paragraphs[:2])
                    if len(description) > 500:
                        description = description[:497] + "..."

            # Look for deadline information in page
            page_text = soup.get_text().lower()
            deadline = None

            # Try to find deadline patterns
            import re
            deadline_patterns = [
                r"deadline[:\s]+(\w+\s+\d{1,2},?\s+\d{4})",
                r"applications?\s+due[:\s]+(\w+\s+\d{1,2},?\s+\d{4})",
                r"closes?[:\s]+(\w+\s+\d{1,2},?\s+\d{4})",
            ]
            for pattern in deadline_patterns:
                match = re.search(pattern, page_text)
                if match:
                    deadline = match.group(1).strip()
                    break

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
