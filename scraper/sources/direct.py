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
    # General-purpose grants that can fund journalism/nonfiction projects
    {
        "name": "Emergent Ventures",
        "url": "https://www.mercatus.org/emergent-ventures",
        "type": "grant",
        "known_amount": "$1,000 - $50,000",
        "known_description": "Fast grants for ideas that improve society. Funds ambitious projects including journalism, media, research, and writing. Rolling applications, no restrictions on profit-making.",
        "known_eligibility": "Open globally to anyone 13+. No citizenship or residency requirements.",
        "bypass_filter": True,
    },
    {
        "name": "ACX Grants",
        "url": "https://www.astralcodexten.com/p/apply-for-an-acx-grant-2025",
        "type": "grant",
        "known_amount": "$5,000 - $100,000",
        "known_description": "Annual grants from Scott Alexander's Astral Codex Ten for diverse projects including research, writing, and creative ventures. Funded 42 projects in 2025 round.",
        "known_eligibility": "Open to anyone with a compelling project idea.",
        "bypass_filter": True,
    },
    {
        "name": "1517 Fund Medici Grant",
        "url": "https://www.1517fund.com/",
        "type": "grant",
        "known_amount": "$1,000 - $100,000",
        "known_description": "Micro-grants and R&D funding for early-stage builders and researchers. Supports experimental projects, writing, and ideas outside traditional institutions.",
        "known_eligibility": "Open to young builders, researchers, and creators globally.",
        "bypass_filter": True,
    },
    {
        "name": "Awesome Foundation",
        "url": "https://www.awesomefoundation.org/en",
        "type": "grant",
        "known_amount": "$1,000",
        "known_description": "Monthly micro-grants for 'awesome' projects with no strings attached. 80+ local chapters worldwide funding arts, technology, community, and creative projects.",
        "known_eligibility": "Anyone can apply - individuals, groups, or organizations.",
        "bypass_filter": True,
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

            # Use known values if provided, otherwise use scraped values
            final_description = source.get("known_description") or description
            final_funding = source.get("known_amount") or funding_size
            final_eligibility = source.get("known_eligibility")

            opp = {
                "title": title_text,
                "url": source["url"],
                "description": final_description,
                "source": source["name"],
                "source_url": source["url"],
                "type": source["type"],
                "scraped_at": datetime.utcnow().isoformat(),
                "deadline": deadline,
                "funding_size": final_funding,
            }

            if final_eligibility:
                opp["eligibility"] = final_eligibility

            # Mark if this should bypass relevance filter
            if source.get("bypass_filter"):
                opp["bypass_filter"] = True

            opportunities.append(opp)

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
