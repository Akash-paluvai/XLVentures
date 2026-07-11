import os
import json
import logging
from pathlib import Path
import sys

# Ensure project root is importable
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.core.settings import settings
from backend.core.logger import setup_logging
from backend.core.config_loader import load_domain_pack, load_accounts

# Initialize logging early
setup_logging()
logger = logging.getLogger("seed_data")


def seed_all_data():
    """
    Checks, creates, and validates all domain packs and synthetic datasets.
    """
    logger.info("--- Starting Seeding and Validation Script ---")
    
    # 1. Ensure folders exist using settings.BASE_DIR
    folders = [
        settings.BASE_DIR / "backend" / "config" / "domain_packs",
        settings.BASE_DIR / "backend" / "data" / "customer_success",
        settings.BASE_DIR / "backend" / "data" / "recruitment",
        settings.BASE_DIR / "backend" / "docs" / "examples"
    ]
    
    for f in folders:
        f.mkdir(parents=True, exist_ok=True)
        logger.info(f"Verified directory: {f}")

    # 2. Check and Seed Customer Success domain pack
    cs_pack_path = settings.BASE_DIR / "backend" / "config" / "domain_packs" / "customer_success.json"
    if not cs_pack_path.exists():
        cs_pack = {
            "id": "customer_success",
            "name": "Customer Success",
            "description": "Customer Success domain pack for SaaS account management and renewal intelligence.",
            "entities": ["Customer", "Account", "Product"],
            "workflows": ["Renewal", "Upsell", "Escalation"],
            "decision_points": ["renewal_risk", "upsell_opportunity", "champion_change_risk", "escalation_risk"],
            "business_rules": [],
            "success_metrics": ["net_revenue_retention", "renewal_rate", "customer_health"],
            "tools": [],
            "prompt_overrides": {}
        }
        with open(cs_pack_path, "w") as f:
            json.dump(cs_pack, f, indent=2)
        logger.info("Seeded customer_success.json")

    # 3. Check and Seed Recruitment domain pack
    rec_pack_path = settings.BASE_DIR / "backend" / "config" / "domain_packs" / "recruitment.json"
    if not rec_pack_path.exists():
        rec_pack = {
            "id": "recruitment",
            "name": "Staffing and Recruitment",
            "description": "Staffing and Recruitment domain pack for screening and offer workflows in candidate hiring pipelines.",
            "entities": ["Candidate", "Job", "Interview"],
            "workflows": ["Screening", "Offer"],
            "decision_points": ["candidate_dropoff_risk", "fast_track_opportunity"],
            "business_rules": [],
            "success_metrics": ["time_to_hire"],
            "tools": [],
            "prompt_overrides": {}
        }
        with open(rec_pack_path, "w") as f:
            json.dump(rec_pack, f, indent=2)
        logger.info("Seeded recruitment.json")

    # 4. Check and Validate loading
    logger.info("Validating loaded configurations...")
    for domain in ["customer_success", "recruitment"]:
        try:
            pack_data = load_domain_pack(domain)
            accounts_data = load_accounts(domain)
            logger.info(f"✅ Domain pack '{domain}' validated successfully. Loaded {len(accounts_data)} records.")
        except Exception as e:
            logger.error(f"❌ Validation failed for '{domain}': {str(e)}")

    logger.info("--- Seeding and Validation Completed ---")


if __name__ == "__main__":
    seed_all_data()
