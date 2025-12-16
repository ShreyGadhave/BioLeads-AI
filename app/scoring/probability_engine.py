"""
Probability Engine - Lead Scoring Algorithm

Implements the 5-signal scoring model for 3D in-vitro lead qualification.
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import re


# Keywords for each scoring category
ROLE_KEYWORDS = [
    "toxicology", "toxicologist", "safety", "preclinical", "hepatic", 
    "liver", "3d", "in vitro", "invitro", "in-vitro", "adme", "dmpk",
    "pharmacology", "assessment"
]

SCIENTIFIC_KEYWORDS = [
    "dili", "drug-induced liver injury", "hepatotoxicity", "hepatotox",
    "3d culture", "3d model", "organoid", "spheroid", "organ-on-chip",
    "microphysiological", "mps", "nams", "new approach methodologies"
]

HUB_LOCATIONS = [
    "boston", "cambridge", "san francisco", "south san francisco", "bay area",
    "palo alto", "menlo park", "basel", "switzerland", "london", "oxford",
    "cambridge uk", "stevenage", "uk", "new jersey", "san diego"
]

FUNDED_KEYWORDS = ["series a", "series b", "series c", "series d", "public", "ipo"]


@dataclass
class LeadScore:
    """Represents the multi-dimensional score for a lead."""
    scientific_intent: int = 0
    role_fit: int = 0
    company_intent: int = 0
    technographic: int = 0
    location: int = 0
    
    @property
    def total(self) -> int:
        """Calculate total probability score (0-100)."""
        return min(100, 
            self.scientific_intent + 
            self.role_fit + 
            self.company_intent + 
            self.technographic + 
            self.location
        )
    
    def to_dict(self) -> Dict[str, int]:
        return {
            "scientific_intent": self.scientific_intent,
            "role_fit": self.role_fit,
            "company_intent": self.company_intent,
            "technographic": self.technographic,
            "location": self.location,
            "total": self.total
        }


def _normalize_text(text: str) -> str:
    """Normalize text for matching."""
    if not text:
        return ""
    return text.lower().strip()


def _has_keywords(text: str, keywords: List[str]) -> bool:
    """Check if text contains any of the keywords."""
    text_lower = _normalize_text(text)
    return any(kw in text_lower for kw in keywords)


def score_scientific_intent(lead: Dict[str, Any]) -> int:
    """
    Score based on recent DILI/hepatic publications.
    Max score: 40 points
    """
    publication = lead.get("recent_publication", "")
    pub_keywords = lead.get("publication_keywords", [])
    
    if not publication and not pub_keywords:
        return 0
    
    # Check publication title
    if _has_keywords(publication, SCIENTIFIC_KEYWORDS):
        return 40
    
    # Check publication keywords
    pub_keywords_str = " ".join(pub_keywords).lower()
    if any(kw in pub_keywords_str for kw in SCIENTIFIC_KEYWORDS):
        return 40
    
    # Partial credit for any publication
    if publication:
        return 20
    
    return 0


def score_role_fit(lead: Dict[str, Any]) -> int:
    """
    Score based on job title relevance.
    Max score: 30 points
    """
    title = _normalize_text(lead.get("title", ""))
    
    if not title:
        return 0
    
    # High-value titles
    high_value = ["director", "vp", "vice president", "head of", "chief"]
    has_high_title = any(hv in title for hv in high_value)
    
    # Role keywords
    has_role_keyword = _has_keywords(title, ROLE_KEYWORDS)
    
    if has_high_title and has_role_keyword:
        return 30
    elif has_role_keyword:
        return 25
    elif has_high_title:
        return 20
    elif "scientist" in title or "research" in title:
        return 10
    
    return 0


def score_company_intent(lead: Dict[str, Any]) -> int:
    """
    Score based on company funding status.
    Max score: 20 points
    """
    funding = _normalize_text(lead.get("funding_status", ""))
    company_type = _normalize_text(lead.get("company_type", ""))
    
    # Series A/B = highest intent (recent funding, looking to grow)
    if "series a" in funding or "series b" in funding:
        return 20
    
    # Series C/D or Public = good budget
    if "series c" in funding or "series d" in funding:
        return 18
    
    if "public" in funding:
        return 15
    
    # Grant-funded academics
    if "nih" in funding or "grant" in funding:
        return 10
    
    # Seed stage = less budget
    if "seed" in funding:
        return 5
    
    return 0


def score_technographic(lead: Dict[str, Any]) -> int:
    """
    Score based on current use of in-vitro technology.
    Max score: 15 points
    """
    uses_invitro = lead.get("uses_invitro", False)
    pub_keywords = " ".join(lead.get("publication_keywords", [])).lower()
    
    if uses_invitro:
        # Already using similar tech = high fit
        base_score = 15
    else:
        base_score = 0
    
    # Bonus for NAMs keywords
    if "nams" in pub_keywords or "new approach" in pub_keywords:
        return min(15, base_score + 5)
    
    return base_score


def score_location(lead: Dict[str, Any]) -> int:
    """
    Score based on hub location.
    Max score: 10 points
    """
    location = _normalize_text(lead.get("location", ""))
    hq = _normalize_text(lead.get("hq_location", ""))
    
    # Check both person location and HQ
    for loc in [location, hq]:
        if any(hub in loc for hub in HUB_LOCATIONS):
            return 10
    
    return 0


def calculate_lead_score(lead: Dict[str, Any]) -> LeadScore:
    """
    Calculate the full probability score for a lead.
    
    Args:
        lead: Dictionary containing lead data
        
    Returns:
        LeadScore object with all dimensions
    """
    return LeadScore(
        scientific_intent=score_scientific_intent(lead),
        role_fit=score_role_fit(lead),
        company_intent=score_company_intent(lead),
        technographic=score_technographic(lead),
        location=score_location(lead)
    )


def rank_leads(leads: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Score and rank a list of leads by probability.
    
    Args:
        leads: List of lead dictionaries
        
    Returns:
        Sorted list with scores attached
    """
    scored_leads = []
    
    for lead in leads:
        score = calculate_lead_score(lead)
        lead_with_score = lead.copy()
        lead_with_score["probability_score"] = score.total
        lead_with_score["score_breakdown"] = score.to_dict()
        scored_leads.append(lead_with_score)
    
    # Sort by probability score (descending)
    scored_leads.sort(key=lambda x: x["probability_score"], reverse=True)
    
    # Add rank
    for i, lead in enumerate(scored_leads, 1):
        lead["rank"] = i
    
    return scored_leads


def get_score_tier(score: int) -> str:
    """Get tier label for a score."""
    if score >= 80:
        return "Hot Lead 🔥"
    elif score >= 60:
        return "High Priority"
    elif score >= 40:
        return "Medium Priority"
    elif score >= 20:
        return "Low Priority"
    else:
        return "Cold Lead"


if __name__ == "__main__":
    # Test with sample lead
    test_lead = {
        "name": "Dr. Sarah Chen",
        "title": "Director of Toxicology",
        "company": "Vertex Pharmaceuticals",
        "location": "Cambridge, MA",
        "hq_location": "Boston, MA",
        "funding_status": "Public",
        "recent_publication": "Drug-Induced Liver Injury: A 3D Hepatic Spheroid Approach (2024)",
        "publication_keywords": ["DILI", "hepatic spheroids", "3D culture"],
        "uses_invitro": True
    }
    
    score = calculate_lead_score(test_lead)
    print(f"Lead: {test_lead['name']}")
    print(f"Score Breakdown: {score.to_dict()}")
    print(f"Total: {score.total}/100")
    print(f"Tier: {get_score_tier(score.total)}")
