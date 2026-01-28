"""Scraper for FundsForWriters Grants."""

import requests
from bs4 import BeautifulSoup
from typing import List
from datetime import datetime

SOURCE_URL = "https://fundsforwriters.com/grants/"
SOURCE_NAME = "FundsForWriters"


def scrape() -> List[dict]:
    """Scrape FundsForWriters grants page."""
    opportunities = []

    try:
        response = requests.get(SOURCE_URL, timeout=30)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        # FundsForWriters typically uses article/post format
        articles = soup.select("article, .post, .grant-listing, .entry")

        for article in articles:
            title_elem = article.select_one("h2, h3, .entry-title, a")
            link_elem = article.select_one("a[href]")
            desc_elem = article.select_one("p, .entry-content, .excerpt")

            if not title_elem:
                continue

            title = title_elem.get_text(strip=True)
            url = link_elem.get("href", "") if link_elem else ""
            description = desc_elem.get_text(strip=True) if desc_elem else ""

            if not title:
                continue

            opportunities.append({
                "title": title,
                "url": url,
                "description": description,
                "source": SOURCE_NAME,
                "source_url": SOURCE_URL,
                "type": "grant",
                "scraped_at": datetime.utcnow().isoformat(),
                "deadline": None,
            })

    except requests.RequestException as e:
        print(f"Error scraping {SOURCE_NAME}: {e}")

    return opportunities
