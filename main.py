import json
import os
import sys
import logging
import time
from datetime import datetime

from config import settings
from scrapers import OrionsArmScraper, SpeculativeEvoScraper, ProjectRhoScraper
from processors import LoreExtractor
from normalizer import JsonBuilder
from storage import MongoUploader

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("main")


def scrape_orions_arm():
    logger.info("Scraping Orion's Arm...")
    scraper = OrionsArmScraper()
    articles = scraper.scrape_all()
    
    os.makedirs("data", exist_ok=True)
    with open("data/raw_orions.json", "w", encoding="utf-8") as f:
        json.dump(articles, f, ensure_ascii=False, indent=2)
    
    logger.info(f"Saved {len(articles)} articles to data/raw_orions.json")


def scrape_spec_evo():
    logger.info("Scraping Speculative Evolution...")
    scraper = SpeculativeEvoScraper()
    articles = scraper.scrape_all()
    
    os.makedirs("data", exist_ok=True)
    with open("data/raw_spec_evo.json", "w", encoding="utf-8") as f:
        json.dump(articles, f, ensure_ascii=False, indent=2)
    
    logger.info(f"Saved {len(articles)} articles to data/raw_spec_evo.json")


def scrape_project_rho():
    logger.info("Scraping Project Rho...")
    scraper = ProjectRhoScraper()
    articles = scraper.scrape_all()
    
    os.makedirs("data", exist_ok=True)
    with open("data/raw_project_rho.json", "w", encoding="utf-8") as f:
        json.dump(articles, f, ensure_ascii=False, indent=2)
    
    logger.info(f"Saved {len(articles)} items to data/raw_project_rho.json")


def extract_batch(batch_id):
    logger.info(f"Extracting batch {batch_id}...")
    
    # Load all raw data
    all_articles = []
    
    for filename in ["raw_orions.json", "raw_spec_evo.json", "raw_project_rho.json"]:
        filepath = f"data/{filename}"
        if os.path.exists(filepath):
            with open(filepath, "r", encoding="utf-8") as f:
                articles = json.load(f)
                all_articles.extend(articles)
    
    logger.info(f"Total articles loaded: {len(all_articles)}")
    
    # Calculate batch range
    batch_size = 100
    start_idx = batch_id * batch_size
    end_idx = start_idx + batch_size
    
    batch_articles = all_articles[start_idx:end_idx]
    
    if not batch_articles:
        logger.info(f"Batch {batch_id} is empty, skipping")
        return
    
    logger.info(f"Processing articles {start_idx} to {end_idx}")
    
    # Extract rules
    extractor = LoreExtractor()
    extracted_rules = []
    
    for i, article in enumerate(batch_articles):
        logger.info(f"  [{i+1}/{len(batch_articles)}] {article.get('title', 'unknown')}")
        
        rule = extractor.extract_from_article(article)
        if rule:
            rule["batch_id"] = batch_id
            extracted_rules.append(rule)
    
    # Save batch result
    output_path = f"data/extracted_batch_{batch_id}.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(extracted_rules, f, ensure_ascii=False, indent=2)
    
    logger.info(f"Batch {batch_id} complete: {len(extracted_rules)} rules extracted")


def finalize():
    logger.info("Finalizing: normalizing and uploading...")
    
    # Load all extracted batches
    all_rules = []
    
    for filename in os.listdir("data"):
        if filename.startswith("extracted_batch_") and filename.endswith(".json"):
            filepath = f"data/{filename}"
            with open(filepath, "r", encoding="utf-8") as f:
                rules = json.load(f)
                all_rules.extend(rules)
    
    logger.info(f"Total rules loaded: {len(all_rules)}")
    
    # Normalize
    builder = JsonBuilder()
    final_json = builder.build(all_rules)
    
    # Save final JSON
    with open("data/biology_rules_final.json", "w", encoding="utf-8") as f:
        json.dump(final_json, f, ensure_ascii=False, indent=2)
    
    logger.info(f"Final JSON saved: {final_json['metadata']['total_rules']} rules")
    
    # Upload to MongoDB
    try:
        uploader = MongoUploader()
        count = uploader.upload_rules(final_json)
        logger.info(f"Uploaded {count} rules to MongoDB")
        
        total_in_db = uploader.get_rule_count()
        logger.info(f"Total rules in MongoDB: {total_in_db}")
        
        uploader.close()
    except Exception as e:
        logger.error(f"MongoDB upload failed: {e}")
        logger.info("Final JSON file is still available locally")


def main():
    if len(sys.argv) < 2:
        logger.error("Usage: python main.py [--scrape-only SOURCE | --extract-batch ID | --finalize]")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "--scrape-only":
        source = sys.argv[2]
        if source == "orions_arm":
            scrape_orions_arm()
        elif source == "spec_evo":
            scrape_spec_evo()
        elif source == "project_rho":
            scrape_project_rho()
        else:
            logger.error(f"Unknown source: {source}")
            sys.exit(1)
    
    elif command == "--extract-batch":
        batch_id = int(sys.argv[2])
        extract_batch(batch_id)
    
    elif command == "--finalize":
        finalize()
    
    else:
        logger.error(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
