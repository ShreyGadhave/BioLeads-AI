"""
PubMed Crawler

Fetches recent publications related to DILI, hepatotoxicity, and 3D models.
Uses the NCBI E-utilities API (free, no API key required for small queries).
"""

import requests
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import time
import xml.etree.ElementTree as ET


# PubMed API base URLs
ESEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
EFETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"

# Search terms for 3D in-vitro toxicology
SEARCH_TERMS = [
    '"drug-induced liver injury"',
    '"DILI"',
    '"hepatotoxicity" AND "3D"',
    '"liver organoid"',
    '"hepatic spheroid"',
    '"organ-on-chip" AND "liver"',
    '"microphysiological systems" AND "toxicology"',
    '"NAMs" AND "toxicology"'
]


def search_pubmed(query: str, max_results: int = 100, days_back: int = 730) -> List[str]:
    """
    Search PubMed for articles matching query.
    
    Args:
        query: Search query string
        max_results: Maximum number of results to return
        days_back: Only include papers from last N days (default: 2 years)
        
    Returns:
        List of PubMed IDs (PMIDs)
    """
    # Calculate date range
    end_date = datetime.now().strftime("%Y/%m/%d")
    start_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y/%m/%d")
    
    params = {
        "db": "pubmed",
        "term": query,
        "retmax": max_results,
        "retmode": "json",
        "datetype": "pdat",
        "mindate": start_date,
        "maxdate": end_date,
        "sort": "relevance"
    }
    
    try:
        response = requests.get(ESEARCH_URL, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        return data.get("esearchresult", {}).get("idlist", [])
    except Exception as e:
        print(f"Error searching PubMed: {e}")
        return []


def fetch_article_details(pmids: List[str]) -> List[Dict[str, Any]]:
    """
    Fetch detailed information for a list of PubMed IDs.
    
    Args:
        pmids: List of PubMed IDs
        
    Returns:
        List of article dictionaries
    """
    if not pmids:
        return []
    
    params = {
        "db": "pubmed",
        "id": ",".join(pmids),
        "retmode": "xml"
    }
    
    try:
        response = requests.get(EFETCH_URL, params=params, timeout=30)
        response.raise_for_status()
        
        # Parse XML response
        root = ET.fromstring(response.text)
        articles = []
        
        for article_elem in root.findall(".//PubmedArticle"):
            article = parse_article_xml(article_elem)
            if article:
                articles.append(article)
        
        return articles
    except Exception as e:
        print(f"Error fetching article details: {e}")
        return []


def parse_article_xml(article_elem: ET.Element) -> Optional[Dict[str, Any]]:
    """Parse a single article from PubMed XML."""
    try:
        medline = article_elem.find(".//MedlineCitation")
        if medline is None:
            return None
        
        # Extract PMID
        pmid_elem = medline.find(".//PMID")
        pmid = pmid_elem.text if pmid_elem is not None else None
        
        # Extract title
        title_elem = medline.find(".//ArticleTitle")
        title = title_elem.text if title_elem is not None else ""
        
        # Extract abstract
        abstract_elem = medline.find(".//Abstract/AbstractText")
        abstract = abstract_elem.text if abstract_elem is not None else ""
        
        # Extract authors
        authors = []
        for author_elem in medline.findall(".//Author"):
            last_name = author_elem.find("LastName")
            first_name = author_elem.find("ForeName")
            affiliation = author_elem.find(".//Affiliation")
            
            if last_name is not None:
                author = {
                    "name": f"{first_name.text if first_name is not None else ''} {last_name.text}".strip(),
                    "affiliation": affiliation.text if affiliation is not None else ""
                }
                authors.append(author)
        
        # Extract publication date
        pub_date = medline.find(".//PubDate")
        year = pub_date.find("Year").text if pub_date is not None and pub_date.find("Year") is not None else ""
        
        # Extract journal
        journal_elem = medline.find(".//Journal/Title")
        journal = journal_elem.text if journal_elem is not None else ""
        
        # Extract keywords
        keywords = []
        for keyword_elem in medline.findall(".//Keyword"):
            if keyword_elem.text:
                keywords.append(keyword_elem.text)
        
        return {
            "pmid": pmid,
            "title": title,
            "abstract": abstract[:500] if abstract else "",  # Truncate long abstracts
            "authors": authors,
            "year": year,
            "journal": journal,
            "keywords": keywords,
            "source": "pubmed"
        }
    except Exception as e:
        print(f"Error parsing article: {e}")
        return None


def extract_leads_from_publications(articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Convert publications into lead format.
    Focus on corresponding authors (usually budget holders).
    """
    leads = []
    seen_names = set()
    
    for article in articles:
        # Get corresponding author (last author) or first author
        authors = article.get("authors", [])
        if not authors:
            continue
        
        # Try corresponding author (usually last in list)
        author = authors[-1] if len(authors) > 1 else authors[0]
        
        # Skip if we've seen this person
        name = author.get("name", "")
        if not name or name in seen_names:
            continue
        seen_names.add(name)
        
        # Parse affiliation for company/institution
        affiliation = author.get("affiliation", "")
        company, location = parse_affiliation(affiliation)
        
        lead = {
            "name": f"Dr. {name}",
            "title": "Research Author",
            "company": company,
            "company_type": classify_company_type(company, affiliation),
            "location": location,
            "hq_location": location,
            "email": "",  # Would need enrichment
            "linkedin": "",
            "funding_status": "Unknown",
            "recent_publication": f"{article.get('title', '')} ({article.get('year', '')})",
            "publication_keywords": article.get("keywords", []),
            "uses_invitro": True,
            "source": "pubmed"
        }
        leads.append(lead)
    
    return leads


def parse_affiliation(affiliation: str) -> tuple:
    """Parse affiliation string to extract company and location."""
    if not affiliation:
        return "Unknown Institution", "Unknown"
    
    # Common patterns
    parts = affiliation.split(",")
    
    # First part is usually the institution
    company = parts[0].strip() if parts else "Unknown Institution"
    
    # Try to find location (usually last part or contains state/country)
    location = "Unknown"
    for part in reversed(parts):
        part = part.strip()
        # Check for common location patterns
        if any(loc in part.lower() for loc in ["usa", "uk", "germany", "switzerland", "ma", "ca", "ny"]):
            location = part
            break
    
    return company[:50], location[:30]  # Truncate for display


def classify_company_type(company: str, affiliation: str) -> str:
    """Classify the company/institution type."""
    text = (company + " " + affiliation).lower()
    
    if any(uni in text for uni in ["university", "college", "institute", "school"]):
        return "Academic"
    elif any(pharma in text for pharma in ["pfizer", "merck", "novartis", "roche", "gsk", "astrazeneca", "lilly", "abbvie"]):
        return "Large Pharma"
    elif any(bio in text for bio in ["biotech", "therapeutics", "biosciences", "pharmaceuticals"]):
        return "Biotech"
    elif any(gov in text for gov in ["nih", "fda", "epa", "cdc", "government"]):
        return "Government"
    else:
        return "Other"


def run_pubmed_crawler(max_per_term: int = 20) -> List[Dict[str, Any]]:
    """
    Run the full PubMed crawl.
    
    Args:
        max_per_term: Max results per search term
        
    Returns:
        List of leads extracted from publications
    """
    print("🔬 Starting PubMed Crawler...")
    
    all_pmids = set()
    
    for term in SEARCH_TERMS:
        print(f"   Searching: {term}")
        pmids = search_pubmed(term, max_results=max_per_term)
        all_pmids.update(pmids)
        time.sleep(0.5)  # Be nice to NCBI servers
    
    print(f"   Found {len(all_pmids)} unique articles")
    
    if not all_pmids:
        return []
    
    # Fetch details
    print("   Fetching article details...")
    articles = fetch_article_details(list(all_pmids))
    print(f"   Retrieved {len(articles)} articles")
    
    # Convert to leads
    leads = extract_leads_from_publications(articles)
    print(f"   Extracted {len(leads)} potential leads")
    
    return leads


if __name__ == "__main__":
    leads = run_pubmed_crawler(max_per_term=10)
    
    print("\nSample Leads Found:")
    for lead in leads[:5]:
        print(f"  - {lead['name']} @ {lead['company']}")
        print(f"    Publication: {lead['recent_publication'][:60]}...")
