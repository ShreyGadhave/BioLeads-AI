"""
Main Pipeline Orchestrator

Coordinates the lead generation pipeline:
1. Data ingestion from multiple sources
2. Lead enrichment and deduplication
3. Probability scoring
4. Output to dashboard/exports
"""

import json
import os
from pathlib import Path
from datetime import datetime

# Add app to path
import sys
sys.path.insert(0, str(Path(__file__).parent))

from app.scoring.probability_engine import rank_leads, calculate_lead_score, get_score_tier


def load_sample_data():
    """Load sample leads from JSON file."""
    data_path = Path(__file__).parent / "data" / "sample_leads.json"
    
    with open(data_path, "r") as f:
        return json.load(f)


def run_pipeline(test_mode=False):
    """
    Main pipeline execution.
    
    Args:
        test_mode: If True, runs with sample data only
    """
    print("\n" + "="*60)
    print("🧬 BIOLEADS AI - LEAD SCORING PIPELINE")
    print("="*60)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # Step 1: Load/Fetch Data
    print("📥 STEP 1: Loading Data")
    print("-" * 40)
    
    leads = load_sample_data()
    print(f"   Loaded {len(leads)} leads from sample data")
    
    # Step 2: Score and Rank Leads
    print("\n📊 STEP 2: Scoring Leads")
    print("-" * 40)
    
    scored_leads = rank_leads(leads)
    
    # Show top 5
    print("\n   Top 5 Leads:")
    for lead in scored_leads[:5]:
        score = lead["probability_score"]
        tier = get_score_tier(score)
        print(f"   {lead['rank']:2}. {lead['name']:<25} | Score: {score:3} | {tier}")
    
    # Step 3: Statistics
    print("\n📈 STEP 3: Pipeline Statistics")
    print("-" * 40)
    
    scores = [l["probability_score"] for l in scored_leads]
    hot_leads = sum(1 for s in scores if s >= 80)
    high_priority = sum(1 for s in scores if 60 <= s < 80)
    medium = sum(1 for s in scores if 40 <= s < 60)
    low = sum(1 for s in scores if s < 40)
    
    print(f"   Total Leads:     {len(scored_leads)}")
    print(f"   Average Score:   {sum(scores)/len(scores):.1f}")
    print(f"   Hot Leads (80+): {hot_leads}")
    print(f"   High (60-79):    {high_priority}")
    print(f"   Medium (40-59):  {medium}")
    print(f"   Low (<40):       {low}")
    
    # Step 4: Save Results
    print("\n💾 STEP 4: Saving Results")
    print("-" * 40)
    
    output_path = Path(__file__).parent / "data" / "scored_leads.json"
    with open(output_path, "w") as f:
        json.dump(scored_leads, f, indent=2)
    print(f"   Saved to: {output_path}")
    
    print("\n" + "="*60)
    print("✅ PIPELINE COMPLETE")
    print("="*60)
    print(f"\nRun 'streamlit run streamlit_app.py' to view the dashboard")
    
    return scored_leads


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="BioLeads AI - Lead Scoring Pipeline")
    parser.add_argument("--test-run", action="store_true", help="Run in test mode with sample data")
    args = parser.parse_args()
    
    run_pipeline(test_mode=args.test_run)
