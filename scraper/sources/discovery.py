"""
Source Discovery Module

Automatically discovers new sources of journalism fellowships/grants by:
1. Web searching for relevant queries
2. Crawling links from known sources
3. Analyzing pages to find aggregators and opportunities
"""

import json
import re
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Set
from urllib.parse import urljoin, urlparse

# Paths
SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR.parent.parent / "data"
DISCOVERED_SOURCES_FILE = DATA_DIR / "discovered_sources.json"
KNOWN_SOURCES_FILE = DATA_DIR / "known_sources.json"

# Search queries to find new sources
DISCOVERY_QUERIES = [
    "journalism fellowship 2026",
    "journalism grant application",
    "investigative journalism fellowship",
    "reporting grant for journalists",
    "narrative journalism fellowship",
    "media fellowship program",
    "journalist grants and funding",
    "writing fellowship nonfiction",
    "long-form journalism grant",
    "journalism funding opportunities",
]

# Keywords indicating a page is an aggregator (lists multiple opportunities)
AGGREGATOR_INDICATORS = [
    "list of", "directory", "database", "opportunities", "grants available",
    "fellowships for", "funding opportunities", "resources for journalists",
    "grants for journalists", "journalism fellowships", "apply now",
    "upcoming deadlines", "open calls"
]

# Keywords indicating a page is a single opportunity
OPPORTUNITY_INDICATORS = [
    "apply", "application", "deadline", "eligibility", "how to apply",
    "submit", "fellowship program", "grant program", "award program",
    "stipend", "funding amount"
]

# Domains to skip (social media, generic sites, etc.)
SKIP_DOMAINS = {
    "facebook.com", "twitter.com", "x.com", "linkedin.com", "instagram.com",
    "youtube.com", "tiktok.com", "reddit.com", "pinterest.com",
    "amazon.com", "ebay.com", "wikipedia.org", "wikimedia.org",
    "google.com", "bing.com", "yahoo.com",
    "medium.com",  # Too noisy
}

# Known good domains (journalism/media focused)
TRUSTED_DOMAINS = {
    "journalism.org", "nieman.harvard.edu", "pulitzercenter.org",
    "ijnet.org", "gijn.org", "spj.org", "asne.org", "ona.org",
    "poynter.org", "cjr.org", "niemanlab.org", "journalismfund.eu",
    "journalism.co.uk", "fundforjournalism.org", "fij.org"
}

# Headers for requests
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
}


def load_known_sources() -> Set[str]:
    """Load URLs of already known sources."""
    known = set()

    # Load from known_sources.json if it exists
    if KNOWN_SOURCES_FILE.exists():
        with open(KNOWN_SOURCES_FILE) as f:
            data = json.load(f)
            known.update(data.get("urls", []))

    # Also check existing scraper source files for URLs
    sources_dir = SCRIPT_DIR
    for py_file in sources_dir.glob("*.py"):
        if py_file.name in ["__init__.py", "discovery.py"]:
            continue
        try:
            content = py_file.read_text()
            # Extract URLs from the source files
            urls = re.findall(r'https?://[^\s"\',\)]+', content)
            known.update(urls)
        except Exception:
            pass

    return known


def load_discovered_sources() -> List[Dict]:
    """Load previously discovered sources."""
    if DISCOVERED_SOURCES_FILE.exists():
        with open(DISCOVERED_SOURCES_FILE) as f:
            return json.load(f)
    return []


def save_discovered_sources(sources: List[Dict]) -> None:
    """Save discovered sources to file."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(DISCOVERED_SOURCES_FILE, "w") as f:
        json.dump(sources, f, indent=2, default=str)


def get_domain(url: str) -> str:
    """Extract domain from URL."""
    parsed = urlparse(url)
    domain = parsed.netloc.lower()
    # Remove www. prefix
    if domain.startswith("www."):
        domain = domain[4:]
    return domain


def should_skip_url(url: str, known_sources: Set[str]) -> bool:
    """Check if URL should be skipped."""
    domain = get_domain(url)

    # Skip known bad domains
    if domain in SKIP_DOMAINS:
        return True

    # Skip if already known
    if url in known_sources:
        return True

    # Skip non-http URLs
    if not url.startswith(("http://", "https://")):
        return True

    return False


def analyze_page(url: str) -> Optional[Dict]:
    """Analyze a page to determine if it's relevant and what type it is."""
    try:
        response = requests.get(url, timeout=15, headers=HEADERS)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        # Get page text
        title = soup.title.get_text(strip=True) if soup.title else ""

        # Get meta description
        meta_desc = ""
        meta_tag = soup.find("meta", attrs={"name": "description"})
        if meta_tag:
            meta_desc = meta_tag.get("content", "")

        # Get main content text
        main_content = soup.find("main") or soup.find("article") or soup.find("body")
        page_text = main_content.get_text(separator=" ", strip=True)[:5000] if main_content else ""

        combined_text = f"{title} {meta_desc} {page_text}".lower()

        # Check relevance - must mention journalism/grants/fellowships
        relevance_keywords = ["journalism", "journalist", "fellowship", "grant", "reporting", "investigative"]
        if not any(kw in combined_text for kw in relevance_keywords):
            return None

        # Determine page type
        aggregator_score = sum(1 for ind in AGGREGATOR_INDICATORS if ind in combined_text)
        opportunity_score = sum(1 for ind in OPPORTUNITY_INDICATORS if ind in combined_text)

        # Count number of external links (aggregators have more)
        links = soup.find_all("a", href=True)
        external_links = [l for l in links if l["href"].startswith("http") and get_domain(l["href"]) != get_domain(url)]

        if aggregator_score > opportunity_score and len(external_links) > 5:
            page_type = "aggregator"
        elif opportunity_score > 0:
            page_type = "opportunity"
        else:
            page_type = "unknown"

        # Extract potential opportunity links from aggregator pages
        opportunity_links = []
        if page_type == "aggregator":
            for link in links:
                href = link.get("href", "")
                link_text = link.get_text(strip=True).lower()
                # Look for links that seem to be opportunities
                if any(kw in link_text for kw in ["fellowship", "grant", "apply", "program", "award"]):
                    full_url = urljoin(url, href)
                    if not should_skip_url(full_url, set()):
                        opportunity_links.append(full_url)

        domain = get_domain(url)
        trust_score = 10 if domain in TRUSTED_DOMAINS else 5

        return {
            "url": url,
            "title": title[:200],
            "description": meta_desc[:500],
            "page_type": page_type,
            "trust_score": trust_score,
            "aggregator_score": aggregator_score,
            "opportunity_score": opportunity_score,
            "external_link_count": len(external_links),
            "opportunity_links": opportunity_links[:20],  # Limit to 20
            "discovered_at": datetime.utcnow().isoformat(),
            "domain": domain,
        }

    except Exception as e:
        return None


def search_web_for_sources(query: str, num_results: int = 10) -> List[str]:
    """
    Search the web for potential sources.
    Uses DuckDuckGo HTML search (no API key needed).
    """
    urls = []
    try:
        search_url = f"https://html.duckduckgo.com/html/?q={query.replace(' ', '+')}"
        response = requests.get(search_url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(response.text, "html.parser")

        # Find result links
        for result in soup.find_all("a", class_="result__a"):
            href = result.get("href", "")
            # DuckDuckGo wraps URLs, extract the actual URL
            if "uddg=" in href:
                import urllib.parse
                parsed = urllib.parse.parse_qs(urllib.parse.urlparse(href).query)
                if "uddg" in parsed:
                    actual_url = parsed["uddg"][0]
                    urls.append(actual_url)
            elif href.startswith("http"):
                urls.append(href)

            if len(urls) >= num_results:
                break

    except Exception as e:
        print(f"Search error for '{query}': {e}")

    return urls


def crawl_known_source_for_links(url: str) -> List[str]:
    """Crawl a known source to find links to other opportunities/sources."""
    links = []
    try:
        response = requests.get(url, timeout=15, headers=HEADERS)
        soup = BeautifulSoup(response.text, "html.parser")

        for a_tag in soup.find_all("a", href=True):
            href = a_tag.get("href", "")
            link_text = a_tag.get_text(strip=True).lower()

            # Look for relevant-sounding links
            relevant_terms = ["fellowship", "grant", "funding", "opportunity", "apply", "program"]
            if any(term in link_text for term in relevant_terms):
                full_url = urljoin(url, href)
                if full_url.startswith("http"):
                    links.append(full_url)

    except Exception as e:
        print(f"Crawl error for {url}: {e}")

    return links


def discover_sources(max_new: int = 20) -> List[Dict]:
    """
    Main discovery function. Searches for and analyzes potential new sources.
    Returns list of newly discovered sources.
    """
    print("\n" + "=" * 60)
    print("SOURCE DISCOVERY")
    print("=" * 60)

    known_sources = load_known_sources()
    existing_discovered = load_discovered_sources()
    existing_urls = {s["url"] for s in existing_discovered}

    print(f"Known sources: {len(known_sources)}")
    print(f"Previously discovered: {len(existing_discovered)}")

    # Collect candidate URLs
    candidates = set()

    # 1. Web search for each query
    print("\n[1/3] Searching web for new sources...")
    for query in DISCOVERY_QUERIES[:5]:  # Limit queries per run
        print(f"  Searching: {query}")
        results = search_web_for_sources(query, num_results=5)
        for url in results:
            if not should_skip_url(url, known_sources) and url not in existing_urls:
                candidates.add(url)

    print(f"  Found {len(candidates)} candidates from search")

    # 2. Crawl existing discovered aggregators for more links
    print("\n[2/3] Crawling known aggregators for links...")
    aggregators = [s for s in existing_discovered if s.get("page_type") == "aggregator"]
    for agg in aggregators[:3]:  # Limit per run
        print(f"  Crawling: {agg['url'][:60]}...")
        links = crawl_known_source_for_links(agg["url"])
        for url in links:
            if not should_skip_url(url, known_sources) and url not in existing_urls:
                candidates.add(url)

    print(f"  Total candidates: {len(candidates)}")

    # 3. Analyze candidates
    print("\n[3/3] Analyzing candidates...")
    new_discoveries = []

    for url in list(candidates)[:max_new]:
        print(f"  Analyzing: {url[:60]}...")
        result = analyze_page(url)
        if result:
            print(f"    -> {result['page_type']} (trust: {result['trust_score']})")
            new_discoveries.append(result)

            # If it's an aggregator, also check its opportunity links
            if result["page_type"] == "aggregator":
                for opp_url in result.get("opportunity_links", [])[:5]:
                    if opp_url not in existing_urls and opp_url not in candidates:
                        opp_result = analyze_page(opp_url)
                        if opp_result:
                            new_discoveries.append(opp_result)

    # Merge with existing and save
    all_discovered = existing_discovered + new_discoveries

    # Deduplicate by URL
    seen_urls = set()
    unique_discovered = []
    for source in all_discovered:
        if source["url"] not in seen_urls:
            seen_urls.add(source["url"])
            unique_discovered.append(source)

    # Sort by trust score
    unique_discovered.sort(key=lambda x: -x.get("trust_score", 0))

    save_discovered_sources(unique_discovered)

    print(f"\n{'=' * 60}")
    print(f"Discovery complete!")
    print(f"New sources found: {len(new_discoveries)}")
    print(f"Total discovered sources: {len(unique_discovered)}")
    print("=" * 60)

    return new_discoveries


def get_sources_to_scrape() -> List[Dict]:
    """
    Get discovered sources that should be added to scraping.
    Returns high-trust sources that appear to be opportunities or aggregators.
    """
    discovered = load_discovered_sources()

    # Filter for high-quality sources
    good_sources = [
        s for s in discovered
        if s.get("trust_score", 0) >= 5
        and s.get("page_type") in ["opportunity", "aggregator"]
    ]

    return good_sources


def scrape() -> List[Dict]:
    """
    Scrape opportunities from discovered sources.
    This integrates with the main scraper.
    """
    opportunities = []
    discovered = get_sources_to_scrape()

    print(f"Scraping {len(discovered)} discovered sources...")

    for source in discovered[:10]:  # Limit per run
        if source.get("page_type") == "opportunity":
            # It's a direct opportunity page
            opp = {
                "title": source.get("title", "Unknown"),
                "url": source["url"],
                "description": source.get("description", ""),
                "source": f"Discovered: {source.get('domain', 'unknown')}",
                "source_url": source["url"],
                "type": "opportunity",
                "scraped_at": datetime.utcnow().isoformat(),
            }
            opportunities.append(opp)

    return opportunities


if __name__ == "__main__":
    # Run discovery when called directly
    discover_sources()
