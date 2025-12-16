"""
Crunchbase Crawler

Fetches recent biotech/pharma funding news from public sources.
Since Crunchbase API requires paid access, we use alternative
public sources like FierceBiotech RSS feeds.
"""

import requests
from typing import List, Dict, Any
from datetime import datetime
import xml.etree.ElementTree as ET


# Public RSS feeds for biotech funding news
RSS_FEEDS = [
    {
        "name": "FierceBiotech",
        "url": "https://www.fiercebiotech.com/rss/xml",
        "type": "funding"
    },
    {
        "name": "BioPharma Dive",
        "url": "https://www.biopharmadive.com/feeds/news/",
        "type": "funding"
    }
]

# Keywords indicating funding news
FUNDING_KEYWORDS = [
    "series a", "series b", "series c", "series d",
    "raises", "funding", "investment", "ipo",
    "million", "billion", "investors"
]

# Keywords for toxicology/liver-related companies
TOX_KEYWORDS = [
    "toxicology", "liver", "hepatic", "safety",
    "preclinical", "drug development", "organoid"
]


def fetch_rss_feed(url: str) -> List[Dict[str, Any]]:
    """Fetch and parse an RSS feed."""
    try:
        response = requests.get(url, timeout=10, headers={
            "User-Agent": "Mozilla/5.0 (compatible; Lead-Agent/1.0)"
        })
        response.raise_for_status()
        
        root = ET.fromstring(response.text)
        items = []
        
        # Handle different RSS formats
        for item in root.findall(".//item"):
            title_elem = item.find("title")
            link_elem = item.find("link")
            desc_elem = item.find("description")
            date_elem = item.find("pubDate")
            
            items.append({
                "title": title_elem.text if title_elem is not None else "",
                "link": link_elem.text if link_elem is not None else "",
                "description": desc_elem.text if desc_elem is not None else "",
                "date": date_elem.text if date_elem is not None else ""
            })
        
        return items
    except Exception as e:
        print(f"Error fetching RSS feed {url}: {e}")
        return []


def is_relevant_funding_news(item: Dict[str, Any]) -> bool:
    """Check if an RSS item is relevant funding news."""
    text = (item.get("title", "") + " " + item.get("description", "")).lower()
    
    # Must have funding keywords
    has_funding = any(kw in text for kw in FUNDING_KEYWORDS)
    
    return has_funding


def parse_funding_amount(text: str) -> str:
    """Extract funding amount from text."""
    import re
    
    # Look for patterns like "$50 million" or "$50M"
    patterns = [
        r'\$(\d+(?:\.\d+)?)\s*(?:million|M)',
        r'\$(\d+(?:\.\d+)?)\s*(?:billion|B)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            amount = match.group(1)
            if "billion" in text.lower() or "B" in pattern:
                return f"${amount}B"
            return f"${amount}M"
    
    return "Unknown"


def extract_company_from_news(item: Dict[str, Any]) -> Dict[str, Any]:
    """Extract company information from a funding news item."""
    title = item.get("title", "")
    description = item.get("description", "")
    
    # Try to extract company name (usually first part of title)
    company_name = title.split(" raise")[0].split(" secure")[0].split(" close")[0].strip()
    if len(company_name) > 50:
        company_name = company_name[:50]
    
    # Extract funding round
    text = (title + " " + description).lower()
    funding_round = "Unknown"
    for round_type in ["series a", "series b", "series c", "series d", "seed"]:
        if round_type in text:
            funding_round = round_type.title()
            break
    
    # Extract amount
    funding_amount = parse_funding_amount(title + " " + description)
    
    return {
        "company": company_name,
        "funding_round": funding_round,
        "funding_amount": funding_amount,
        "news_title": title,
        "news_link": item.get("link", ""),
        "news_date": item.get("date", ""),
        "source": "funding_news"
    }


def run_crunchbase_crawler() -> List[Dict[str, Any]]:
    """
    Run the funding news crawler.
    
    Returns:
        List of companies with recent funding
    """
    print("💰 Starting Funding News Crawler...")
    
    all_companies = []
    
    for feed in RSS_FEEDS:
        print(f"   Fetching: {feed['name']}")
        items = fetch_rss_feed(feed["url"])
        
        for item in items:
            if is_relevant_funding_news(item):
                company = extract_company_from_news(item)
                all_companies.append(company)
    
    print(f"   Found {len(all_companies)} funding events")
    
    return all_companies


# Sample data for when RSS feeds are unavailable
def get_sample_funding_data() -> List[Dict[str, Any]]:
    """Return sample funding data for demo purposes."""
    return [
        {
            "company": "Foghorn Therapeutics",
            "funding_round": "Series C",
            "funding_amount": "$200M",
            "company_type": "Series C Biotech",
            "hq_location": "Cambridge, MA",
            "uses_invitro": True
        },
        {
            "company": "Recursion Pharmaceuticals",
            "funding_round": "Series D",
            "funding_amount": "$450M",
            "company_type": "Series D Biotech",
            "hq_location": "Salt Lake City, UT",
            "uses_invitro": True
        },
        {
            "company": "Beam Therapeutics",
            "funding_round": "Series B",
            "funding_amount": "$180M",
            "company_type": "Series B Biotech",
            "hq_location": "Cambridge, MA",
            "uses_invitro": True
        },
        {
            "company": "Aligos Therapeutics",
            "funding_round": "Series B",
            "funding_amount": "$225M",
            "company_type": "Series B Biotech",
            "hq_location": "South San Francisco, CA",
            "uses_invitro": True
        },
        {
            "company": "Arcus Biosciences",
            "funding_round": "Series B",
            "funding_amount": "$150M",
            "company_type": "Series B Biotech",
            "hq_location": "Hayward, CA",
            "uses_invitro": True
        }
    ]


if __name__ == "__main__":
    # Try live crawler first
    companies = run_crunchbase_crawler()
    
    if not companies:
        print("   Using sample data...")
        companies = get_sample_funding_data()
    
    print("\nFunded Companies Found:")
    for company in companies[:5]:
        print(f"  - {company['company']}: {company.get('funding_round', 'Unknown')} ({company.get('funding_amount', 'Unknown')})")
