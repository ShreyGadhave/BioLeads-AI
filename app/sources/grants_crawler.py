"""
NIH Grants Crawler

Fetches active grants related to liver toxicology and 3D models
from NIH RePORTER (publicly accessible).
"""

import requests
from typing import List, Dict, Any
from datetime import datetime


# NIH RePORTER API endpoint
NIH_REPORTER_URL = "https://api.reporter.nih.gov/v2/projects/search"

# Search criteria for relevant grants
GRANT_SEARCH_TERMS = [
    "drug induced liver injury",
    "hepatotoxicity",
    "3D liver model",
    "organ on chip liver",
    "microphysiological systems toxicology"
]


def search_nih_grants(query: str, max_results: int = 25) -> List[Dict[str, Any]]:
    """
    Search NIH RePORTER for grants matching query.
    
    Args:
        query: Search query
        max_results: Maximum results to return
        
    Returns:
        List of grant dictionaries
    """
    payload = {
        "criteria": {
            "use_relevance": True,
            "advanced_text_search": {
                "operator": "and",
                "search_field": "all",
                "search_text": query
            },
            "fiscal_years": [2023, 2024, 2025],
            "include_active_projects": True
        },
        "offset": 0,
        "limit": max_results,
        "sort_field": "project_start_date",
        "sort_order": "desc"
    }
    
    try:
        response = requests.post(
            NIH_REPORTER_URL,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=15
        )
        response.raise_for_status()
        
        data = response.json()
        return data.get("results", [])
    except Exception as e:
        print(f"Error searching NIH grants: {e}")
        return []


def parse_grant_to_lead(grant: Dict[str, Any]) -> Dict[str, Any]:
    """Convert an NIH grant to a lead format."""
    # Extract PI (Principal Investigator)
    pi_names = grant.get("principal_investigators", [])
    pi = pi_names[0] if pi_names else {}
    pi_name = f"{pi.get('first_name', '')} {pi.get('last_name', '')}".strip()
    
    # Extract organization
    org = grant.get("organization", {})
    org_name = org.get("org_name", "Unknown Institution")
    org_city = org.get("org_city", "")
    org_state = org.get("org_state", "")
    location = f"{org_city}, {org_state}" if org_city and org_state else "Unknown"
    
    # Extract grant info
    award_amount = grant.get("award_amount", 0)
    project_title = grant.get("project_title", "")
    
    return {
        "name": f"Dr. {pi_name}" if pi_name else "Unknown PI",
        "title": "Principal Investigator",
        "company": org_name,
        "company_type": "Academic",
        "location": location,
        "hq_location": location,
        "email": "",
        "linkedin": "",
        "funding_status": f"NIH Grant (${award_amount:,})" if award_amount else "NIH Grant",
        "recent_publication": project_title[:100] if project_title else None,
        "publication_keywords": [],
        "uses_invitro": True,
        "grant_project": project_title,
        "source": "nih_reporter"
    }


def run_grants_crawler(max_per_term: int = 10) -> List[Dict[str, Any]]:
    """
    Run the NIH grants crawler.
    
    Args:
        max_per_term: Max results per search term
        
    Returns:
        List of leads from grant PIs
    """
    print("🔬 Starting NIH Grants Crawler...")
    
    all_grants = []
    seen_pis = set()
    
    for term in GRANT_SEARCH_TERMS:
        print(f"   Searching: {term}")
        grants = search_nih_grants(term, max_results=max_per_term)
        
        for grant in grants:
            # Convert to lead
            lead = parse_grant_to_lead(grant)
            
            # Deduplicate by PI name
            if lead["name"] not in seen_pis:
                seen_pis.add(lead["name"])
                all_grants.append(lead)
    
    print(f"   Found {len(all_grants)} unique grant PIs")
    
    return all_grants


def get_sample_grant_leads() -> List[Dict[str, Any]]:
    """Return sample grant leads for demo purposes."""
    return [
        {
            "name": "Dr. Amanda Foster",
            "title": "Principal Investigator",
            "company": "Harvard Medical School",
            "company_type": "Academic",
            "location": "Boston, MA",
            "hq_location": "Boston, MA",
            "email": "afoster@hms.harvard.edu",
            "linkedin": "linkedin.com/in/amandafoster-pi",
            "funding_status": "NIH R01 Grant ($2.5M)",
            "recent_publication": "Organ-on-Chip for DILI Mechanistic Studies",
            "publication_keywords": ["organ-on-chip", "DILI", "mechanistic"],
            "uses_invitro": True
        },
        {
            "name": "Dr. William Thompson",
            "title": "Principal Investigator",
            "company": "MIT",
            "company_type": "Academic",
            "location": "Cambridge, MA",
            "hq_location": "Cambridge, MA",
            "email": "wthompson@mit.edu",
            "linkedin": "",
            "funding_status": "NIH R01 Grant ($1.8M)",
            "recent_publication": "3D Bioprinted Liver Models for Drug Screening",
            "publication_keywords": ["bioprinting", "liver", "drug screening"],
            "uses_invitro": True
        },
        {
            "name": "Dr. Jennifer Lee",
            "title": "Principal Investigator",
            "company": "Stanford University",
            "company_type": "Academic",
            "location": "Palo Alto, CA",
            "hq_location": "Stanford, CA",
            "email": "jlee@stanford.edu",
            "linkedin": "",
            "funding_status": "NIH R21 Grant ($800K)",
            "recent_publication": "Microfluidic Liver-on-Chip for Hepatotoxicity",
            "publication_keywords": ["microfluidic", "liver-on-chip", "hepatotoxicity"],
            "uses_invitro": True
        }
    ]


if __name__ == "__main__":
    # Try live crawler
    leads = run_grants_crawler(max_per_term=5)
    
    if not leads:
        print("   Using sample data...")
        leads = get_sample_grant_leads()
    
    print("\nGrant PI Leads Found:")
    for lead in leads[:5]:
        print(f"  - {lead['name']} @ {lead['company']}")
        print(f"    Grant: {lead.get('funding_status', 'Unknown')}")
