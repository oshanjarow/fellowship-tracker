"""Direct page scrapers for specific organizations."""

import re
import requests
from bs4 import BeautifulSoup
from typing import List, Optional
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


def extract_funding_amount(text: str) -> Optional[str]:
    """Extract funding/award amount from text."""
    if not text:
        return None

    patterns = [
        r'(?:receives?|award(?:ed)?|stipend|grant|fellowship)[^\$€£]*?([\$€£][\d,]+(?:\s*[-–]\s*[\$€£]?[\d,]+)?)',
        r'([\$€£][\d,]+(?:\s*[-–]\s*[\$€£]?[\d,]+)?)\s*(?:fellowship|award|grant|stipend|prize)',
        r'(up to\s*[\$€£][\d,]+)',
        r'((?:USD|EUR|GBP)\s*[\d,]+(?:\s*[-–]\s*[\d,]+)?)',
        r'(?:amount|funding|support|receive)[^\$€£]{0,30}([\$€£][\d,]+(?:\s*[-–]\s*[\$€£]?[\d,]+)?)',
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            amount = match.group(1).strip()
            amount = re.sub(r'\s+', ' ', amount)
            return amount

    # Fallback: find significant dollar amounts
    amounts = re.findall(r'[\$€£]([\d,]+)', text)
    for amt in amounts:
        try:
            value = int(amt.replace(',', ''))
            if 1000 <= value <= 500000:
                return f"${amt}"
        except ValueError:
            continue

    return None


def scrape() -> List[dict]:
    """Scrape direct organization pages."""
    opportunities = []

    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    for source in DIRECT_SOURCES:
        try:
            response = requests.get(source["url"], timeout=30, headers=headers)
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

            # Get full page text for extraction
            page_text = soup.get_text(separator=' ', strip=True)

            # Get main content for description
            content = soup.select_one("main, .content, article, #content")
            description = ""
            if content:
                paragraphs = content.select("p")
                if paragraphs:
                    description = " ".join(p.get_text(strip=True) for p in paragraphs[:2])
                    if len(description) > 500:
                        description = description[:497] + "..."

            # Extract funding amount
            funding_size = extract_funding_amount(page_text)

            # Try to find deadline patterns
            deadline = None
            deadline_patterns = [
                r"deadline[:\s]+(\w+\s+\d{1,2},?\s+\d{4})",
                r"applications?\s+due[:\s]+(\w+\s+\d{1,2},?\s+\d{4})",
                r"closes?[:\s]+(\w+\s+\d{1,2},?\s+\d{4})",
            ]
            for pattern in deadline_patterns:
                match = re.search(pattern, page_text.lower())
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
                "funding_size": funding_size,
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
                "funding_size": None,
                "scrape_error": str(e),
            })

    return opportunities
