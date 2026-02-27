#!/usr/bin/env python3
"""
Update Trivy Rules Database

This script updates the vulnerability database from Trivy's official GitHub repository.
The database contains security rules used by the Red Team to inject vulnerabilities.

Usage:
    python scripts/update_trivy_rules.py
    
Note: This is optional - the included database (142 rules) is sufficient for benchmarking.
Only run this if you need the latest Trivy rules.
"""

import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

# Paths
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
DATA_DIR = PROJECT_ROOT / "src" / "data"
OUTPUT_FILE = DATA_DIR / "trivy_rules_db.json"

# Trivy checks repository
TRIVY_REPO = "aquasecurity/trivy-checks"
TRIVY_RAW_BASE = f"https://raw.githubusercontent.com/{TRIVY_REPO}/main"

# Rule categories to fetch
CLOUD_PROVIDERS = ["aws", "azure", "google"]
RULE_PATHS = {
    "aws": "checks/cloud/aws",
    "azure": "checks/cloud/azure", 
    "google": "checks/cloud/google",
}


def fetch_rules_from_github() -> Dict[str, Any]:
    """
    Fetch rules from Trivy GitHub repository.
    
    Note: This requires network access and the 'requests' package.
    """
    try:
        import requests
    except ImportError:
        logger.error("requests package required. Install with: pip install requests")
        sys.exit(1)
    
    logger.info(f"Fetching rules from {TRIVY_REPO}...")
    
    rules_db = {
        "metadata": {
            "source": "trivy-checks",
            "repository": f"https://github.com/{TRIVY_REPO}",
            "updated": datetime.utcnow().isoformat(),
            "version": "auto-updated",
        },
        "rules": {}
    }
    
    # This is a simplified version - a full scraper would need to:
    # 1. Use GitHub API to list all YAML files in each provider directory
    # 2. Parse each YAML file for rule metadata
    # 3. Handle rate limiting and pagination
    
    # For now, we'll just validate the existing database
    logger.warning("Full GitHub scraping requires GitHub API token for rate limits.")
    logger.warning("Using existing database. For full updates, see:")
    logger.warning("  https://github.com/SymbioticSec/vulnerable-iac-dataset-generator")
    
    return None


def validate_existing_database() -> bool:
    """Validate the existing database is present and valid."""
    if not OUTPUT_FILE.exists():
        logger.error(f"Database not found at: {OUTPUT_FILE}")
        return False
    
    try:
        with open(OUTPUT_FILE) as f:
            db = json.load(f)
        
        rules = db.get("rules", {})
        total_rules = sum(len(rule_list) for rule_list in rules.values())
        
        logger.info(f"✓ Database validated: {OUTPUT_FILE}")
        logger.info(f"  Rule sets: {list(rules.keys())}")
        logger.info(f"  Total rules: {total_rules}")
        
        # Show breakdown
        for key, rule_list in rules.items():
            logger.info(f"    {key}: {len(rule_list)} rules")
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to validate database: {e}")
        return False


def main():
    """Main entry point."""
    logger.info("=" * 60)
    logger.info("Trivy Rules Database Manager")
    logger.info("=" * 60)
    
    # Ensure data directory exists
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    # Check for update flag
    if "--fetch" in sys.argv:
        result = fetch_rules_from_github()
        if result:
            with open(OUTPUT_FILE, "w") as f:
                json.dump(result, f, indent=2)
            logger.info(f"Database updated: {OUTPUT_FILE}")
    else:
        # Just validate existing database
        if validate_existing_database():
            logger.info("\nDatabase is ready for use.")
            logger.info("To fetch latest rules (requires GitHub API): python scripts/update_trivy_rules.py --fetch")
        else:
            logger.error("\nDatabase validation failed!")
            sys.exit(1)


if __name__ == "__main__":
    main()
