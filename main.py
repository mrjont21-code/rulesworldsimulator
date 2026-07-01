import json
import os
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


def run():
    start_time = time.time()
    logger.info("=" * 60)
    logger.info("WORLD LORE HARVESTER - Starting")
    logger.info("=" * 60)

    # ----------------------------------------
    # PHASE 1: SCRAPE
    # ----------------------------------------
    logger.info("[PHASE 1] Scraping sources...")

    all_articles = []

    logger.info("[1/3] Scraping Orion's Arm...")
    orions = OrionsArmScraper()
    orions_articles = orions.scrape_all()
    all_articles.extend(orions_articles)
    logger.info(f"  -> {len(orions_articles)} articles")

    logger.info("[2/3] Scraping Speculative Evolution...")
    spec_evo = SpeculativeEvoScraper()
    spec_articles = spec_evo.scrape_all()
    all_articles.extend(spec_articles)
    logger.info(f"  -> {len(spec_articles)} articles")

    logger.info("[3/3] Scraping Project Rho...")
    project_rho = ProjectRhoScraper()
    rho_articles = project_rho.scrape_all()
    all_articles.extend(rho_articles)
    logger.info(f"  -> {len(rho_articles)} items")

    logger.info(f"[PHASE 1] Total scraped: {len(all_articles)} articles")

    # Save raw
    os.makedirs("data", exist_ok=True)
    with open(settings.RAW_OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(all_articles, f, ensure_ascii=False, indent=2)
    logger.info(f"Raw articles saved to {settings.RAW_OUTPUT_PATH}")

    # ----------------------------------------
    # PHASE 2: LLM EXTRACTION
    # ----------------------------------------
    logger.info("[PHASE 2] Extracting rules with LLM...")

    extractor = LoreExtractor()
    extracted_rules = []

    for i, article in enumerate(all_articles):
        logger.info(
            f"  Processing {i + 1}/{len(all_articles)}: "
            f"{article.get('title', 'unknown')}"
        )

        rule = extractor.extract_from_article(article)
        if rule:
            extracted_rules.append(rule)

        if (i + 1) % 50 == 0:
            logger.info(
                f"  Progress: {i + 1}/{len(all_articles)} processed, "
                f"{len(extracted_rules)} rules extracted so far"
            )

    logger.info(
        f"[PHASE 2] Total extracted: {len(extracted_rules)} rules"
    )

    # ----------------------------------------
    # PHASE 3: NORMALIZE & BUILD JSON
    # ----------------------------------------
    logger.info("[PHASE 3] Normalizing and building final JSON...")

    builder = JsonBuilder()
    final_json = builder.build(extracted_rules)

    with open(settings.FINAL_OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(final_json, f, ensure_ascii=False, indent=2)
    logger.info(f"Final JSON saved to {settings.FINAL_OUTPUT_PATH}")

    # ----------------------------------------
    # PHASE 4: UPLOAD TO MONGODB
    # ----------------------------------------
    logger.info("[PHASE 4] Uploading to MongoDB Atlas...")

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

    # ----------------------------------------
    # SUMMARY
    # ----------------------------------------
    elapsed = time.time() - start_time
    logger.info("=" * 60)
    logger.info("WORLD LORE HARVESTER - Complete")
    logger.info(f"Time elapsed: {elapsed:.1f} seconds")
    logger.info(f"Articles scraped: {len(all_articles)}")
    logger.info(f"Rules extracted: {len(extracted_rules)}")
    logger.info(f"Final rules (after dedup): {final_json['metadata']['total_rules']}")
    logger.info("=" * 60)


if __name__ == "__main__":
    run()
