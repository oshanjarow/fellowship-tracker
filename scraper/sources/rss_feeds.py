"""Scraper for RSS feeds including Wild Writing Substack."""

from typing import List
import feedparser
from datetime import datetime

RSS_FEEDS = [
    {
        "name": "Wild Writing",
        "url": "https://wildwriting.substack.com/feed",
        "type": "newsletter"
    },
]


def scrape() -> List[dict]:
    """Scrape RSS feeds for opportunities."""
    opportunities = []

    for feed_info in RSS_FEEDS:
        try:
            feed = feedparser.parse(feed_info["url"])

            for entry in feed.entries:
                title = entry.get("title", "")
                url = entry.get("link", "")
                description = entry.get("summary", entry.get("description", ""))

                # Clean HTML from description
                if description:
                    from bs4 import BeautifulSoup
                    description = BeautifulSoup(description, "html.parser").get_text(strip=True)
                    # Truncate long descriptions
                    if len(description) > 500:
                        description = description[:497] + "..."

                # Get published date
                published = None
                if hasattr(entry, "published_parsed") and entry.published_parsed:
                    published = datetime(*entry.published_parsed[:6]).isoformat()

                if not title:
                    continue

                opportunities.append({
                    "title": title,
                    "url": url,
                    "description": description,
                    "source": feed_info["name"],
                    "source_url": feed_info["url"],
                    "type": feed_info["type"],
                    "scraped_at": datetime.utcnow().isoformat(),
                    "published_at": published,
                    "deadline": None,
                })

        except Exception as e:
            print(f"Error scraping RSS feed {feed_info['name']}: {e}")

    return opportunities
