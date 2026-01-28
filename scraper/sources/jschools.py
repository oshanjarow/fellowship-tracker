"""Scraper for J-school fellowships."""

import re
import requests
from bs4 import BeautifulSoup
from typing import List, Optional
from datetime import datetime

JSCHOOL_SOURCES = [
    {
        "name": "Berkeley BCSP Ferriss Fellowship",
        "url": "https://fellowships.journalism.berkeley.edu/bcsp/",
        "type": "fellowship",
        "known_amount": "$10,000",  # Per recipient
        "known_description": "The Ferriss Fellowship supports journalists pursuing long-form narrative projects. Fellows receive funding and mentorship at UC Berkeley's Graduate School of Journalism."
    },
    {
        "name": "NYU Matthew Power Award",
        "url": "https://journalism.nyu.edu/about-us/awards-and-fellowships/matthew-power-literary-reporting-award/",
        "type": "award",
        "known_amount": "$15,000",
    },
    {
        "name": "Columbia Journalism Fellowships",
        "url": "https://journalism.columbia.edu/fellowships",
        "type": "fellowship",
        "known_description": "Columbia offers various fellowships including the Knight-Bagehot Fellowship in Economics and Business Journalism, and the Maria Moors Cabot Prizes."
    },
    {
        "name": "Knight-Wallace Fellowships",
        "url": "https://wallacehouse.umich.edu/knight-wallace/",
        "type": "fellowship",
        "known_amount": "$75,000 stipend",
        "known_description": "A transformative eight-month fellowship at the University of Michigan for mid-career journalists. Fellows receive stipend, tuition, health insurance, and housing assistance."
    },
    {
        "name": "Nieman Fellowships",
        "url": "https://nieman.harvard.edu/fellowships/",
        "type": "fellowship",
        "known_amount": "$75,000 stipend",
        "known_description": "A year at Harvard University for journalists to pursue academic study and professional development. Fellows receive stipend, housing, and health benefits."
    },
    {
        "name": "USC Annenberg Fellowships",
        "url": "https://annenberg.usc.edu/journalism/fellowships",
        "type": "fellowship",
        "known_description": "USC Annenberg offers several fellowship programs for journalists at various career stages."
    },
    {
        "name": "Northwestern Medill Fellowships",
        "url": "https://www.medill.northwestern.edu/professional-education/",
        "type": "fellowship",
        "known_description": "Medill offers several fellowship programs including the O'Brien Fellowship in Public Service Journalism."
    },
]


def extract_funding_amount(text: str) -> Optional[str]:
    """Extract funding/award amount from text.

    Looks for patterns like:
    - $10,000
    - $10,000 - $20,000
    - €5,000
    - up to $50,000
    - USD 10,000
    """
    if not text:
        return None

    # Patterns to find monetary amounts with context
    patterns = [
        # "receives $X" or "award of $X" or "stipend of $X"
        r'(?:receives?|award(?:ed)?|stipend|grant|fellowship)[^\$€£]*?([\$€£][\d,]+(?:\s*[-–]\s*[\$€£]?[\d,]+)?)',
        # "$X fellowship/award/grant/stipend"
        r'([\$€£][\d,]+(?:\s*[-–]\s*[\$€£]?[\d,]+)?)\s*(?:fellowship|award|grant|stipend|prize)',
        # "up to $X"
        r'(up to\s*[\$€£][\d,]+)',
        # "USD/EUR X,XXX"
        r'((?:USD|EUR|GBP)\s*[\d,]+(?:\s*[-–]\s*[\d,]+)?)',
        # Standalone amounts near keywords
        r'(?:amount|funding|support|receive)[^\$€£]{0,30}([\$€£][\d,]+(?:\s*[-–]\s*[\$€£]?[\d,]+)?)',
    ]

    text_lower = text.lower()

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            amount = match.group(1).strip()
            # Clean up the amount
            amount = re.sub(r'\s+', ' ', amount)
            return amount

    # Fallback: find any dollar amount that looks significant (over $1000)
    amounts = re.findall(r'[\$€£]([\d,]+)', text)
    for amt in amounts:
        try:
            value = int(amt.replace(',', ''))
            if 1000 <= value <= 500000:  # Reasonable fellowship range
                return f"${amt}"
        except ValueError:
            continue

    return None


def extract_deadline(text: str) -> Optional[str]:
    """Extract deadline date from text."""
    if not text:
        return None

    # Common deadline patterns
    patterns = [
        r'deadline[:\s]+([A-Z][a-z]+\s+\d{1,2},?\s+\d{4})',
        r'due[:\s]+([A-Z][a-z]+\s+\d{1,2},?\s+\d{4})',
        r'applications?\s+(?:are\s+)?due[:\s]+([A-Z][a-z]+\s+\d{1,2},?\s+\d{4})',
        r'submit\s+by[:\s]+([A-Z][a-z]+\s+\d{1,2},?\s+\d{4})',
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip()

    return None


def scrape() -> List[dict]:
    """Scrape J-school fellowship pages."""
    opportunities = []

    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    for source in JSCHOOL_SOURCES:
        try:
            response = requests.get(source["url"], timeout=30, headers=headers)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")

            # Get page title
            title = soup.select_one("h1, .page-title, .entry-title")
            title_text = title.get_text(strip=True) if title else source["name"]

            # Use source name if page title is generic
            if title_text.lower() in ['home', 'fellowships', 'about', '']:
                title_text = source["name"]

            # Get full page text for extraction
            page_text = soup.get_text(separator=' ', strip=True)

            # Get main content for description
            content = soup.select_one("main, .content, article, .entry-content, #content")
            description = ""
            if content:
                paragraphs = content.select("p")
                if paragraphs:
                    description = " ".join(p.get_text(strip=True) for p in paragraphs[:3])
                    if len(description) > 500:
                        description = description[:497] + "..."

            # Extract funding amount from page, fallback to known amount
            funding_size = extract_funding_amount(page_text) or source.get("known_amount")

            # Look for deadline information
            deadline = extract_deadline(page_text)

            # Use known description if scraped one is empty
            if not description and source.get("known_description"):
                description = source["known_description"]

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
            # Still add the source with known/fallback info
            opportunities.append({
                "title": source["name"],
                "url": source["url"],
                "description": source.get("known_description", f"Visit {source['url']} for more information."),
                "source": source["name"],
                "source_url": source["url"],
                "type": source["type"],
                "scraped_at": datetime.utcnow().isoformat(),
                "deadline": None,
                "funding_size": source.get("known_amount"),
                "scrape_error": str(e),
            })

    return opportunities
