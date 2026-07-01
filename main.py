"""
MAIN: Orchestrator - Pattern Pomodoro 25 phút / 15 phút nghỉ
Xoay vòng 35 từ khóa
"""
import os
import sys
import time
import logging
import uuid
from datetime import datetime, timezone

from config import settings

# Import pipeline stages
from t0_search import run_t0
from t1_classify import run_t1
from t2_scrape import run_t2
from t3_normalize import run_t3
from t4_deduplicate import run_t4
from t5_upload import run_t5

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(name)s] %(message)s',
    datefmt='%H:%M:%S',
    stream=sys.stderr
)
logger = logging.getLogger("MAIN")


def run_pipeline_session() -> dict:
    """
    Chạy 1 phiên pipeline hoàn chỉnh (trong 25 phút)
    """
    run_id = f"run_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
    
    logger.info("=" * 80)
    logger.info(f"🚀 PIPELINE SESSION STARTED")
    logger.info(f"   Run ID: {run_id}")
    logger.info(f"   Start:  {datetime.now().strftime('%H:%M:%S')}")
    logger.info("=" * 80)
    
    stats = {
        "started_at": datetime.now(timezone.utc).isoformat(),
        "keywords_used": [],
        "links_found": 0,
        "links_scraped": 0,
        "contents_validated": 0,
        "duplicates_removed": 0,
        "rules_uploaded": 0
    }
    
    session_start = time.time()
    
    try:
        # === T0: SEARCH ===
        logger.info("\n" + "=" * 80)
        logger.info("🔍 STAGE T0: SEARCH")
        logger.info("=" * 80)
        
        links = run_t0()
        stats["links_found"] = len(links)
        
        if not links:
            logger.warning("⚠️  Không tìm được link nào, kết thúc session")
            return stats
        
        # === T1: CLASSIFY ===
        logger.info("\n" + "=" * 80)
        logger.info("🏷️  STAGE T1: CLASSIFY")
        logger.info("=" * 80)
        
        classified_links = run_t1(links)
        
        # === T2: SCRAPE ===
        logger.info("\n" + "=" * 80)
        logger.info("📥 STAGE T2: SCRAPE")
        logger.info("=" * 80)
        
        scraped_contents = run_t2(classified_links)
        stats["links_scraped"] = len(scraped_contents)
        
        if not scraped_contents:
            logger.warning("⚠️  Không scrape được nội dung nào")
            return stats
        
        # === T3: NORMALIZE ===
        logger.info("\n" + "=" * 80)
        logger.info("🔧 STAGE T3: NORMALIZE")
        logger.info("=" * 80)
        
        normalized_contents = run_t3(scraped_contents)
        
        # === T4: DEDUPLICATE ===
        logger.info("\n" + "=" * 80)
        logger.info("🔍 STAGE T4: DEDUPLICATE")
        logger.info("=" * 80)
        
        unique_contents = run_t4(normalized_contents, run_id)
        stats["duplicates_removed"] = len(normalized_contents) - len(unique_contents)
        stats["contents_validated"] = len(unique_contents)
        
        # === T5: UPLOAD ===
        logger.info("\n" + "=" * 80)
        logger.info("📤 STAGE T5: UPLOAD")
        logger.info("=" * 80)
        
        run_t5(unique_contents, run_id, stats)
        stats["rules_uploaded"] = len(unique_contents)
        
    except Exception as e:
        logger.error(f"❌ Pipeline error: {e}", exc_info=True)
    
    # Calculate duration
    stats["duration_seconds"] = time.time() - session_start
    
    logger.info("\n" + "=" * 80)
    logger.info("📊 SESSION SUMMARY")
    logger.info("=" * 80)
    logger.info(f"   Duration:        {stats['duration_seconds']/60:.1f} phút")
    logger.info(f"   Links found:     {stats['links_found']}")
    logger.info(f"   Links scraped:   {stats['links_scraped']}")
    logger.info(f"   Contents valid:  {stats['contents_validated']}")
    logger.info(f"   Duplicates:      {stats['duplicates_removed']}")
    logger.info(f"   Rules uploaded:  {stats['rules_uploaded']}")
    logger.info("=" * 80)
    
    return stats


def run_pomodoro_loop():
    """
    Loop Pomodoro: 25 phút làm việc, 15 phút nghỉ
    """
    logger.info("🎯 RULESWORLD SCRAPER - POMODORO MODE")
    logger.info(f"   Work:  {settings.WORK_MINUTES} phút")
    logger.info(f"   Break: {settings.BREAK_MINUTES} phút")
    logger.info(f"   Keywords: {len(settings.KEYWORDS_FILE)} từ khóa")
    logger.info("")
    
    session_count = 0
    
    while True:
        session_count += 1
        
        logger.info("\n" + "🟢" * 40)
        logger.info(f"📝 SESSION #{session_count} - BẮT ĐẦU LÀM VIỆC")
        logger.info("🟢" * 40 + "\n")
        
        # Run pipeline
        stats = run_pipeline_session()
        
        # Break time
        logger.info("\n" + "🔴" * 40)
        logger.info(f"☕ BREAK TIME - NGHỈ {settings.BREAK_MINUTES} PHÚT")
        logger.info(f"   Session #{session_count} completed")
        logger.info(f"   Next session starts at: {datetime.fromtimestamp(time.time() + settings.BREAK_MINUTES * 60).strftime('%H:%M:%S')}")
        logger.info("🔴" * 40 + "\n")
        
        # Sleep for break duration
        time.sleep(settings.BREAK_MINUTES * 60)


def run_single_session():
    """Chạy 1 session duy nhất (cho testing)"""
    stats = run_pipeline_session()
    return stats


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Rulesworld Scraper")
    parser.add_argument("--loop", action="store_true", help="Chạy loop Pomodoro liên tục")
    parser.add_argument("--once", action="store_true", help="Chạy 1 session duy nhất")
    args = parser.parse_args()
    
    if args.loop:
        run_pomodoro_loop()
    else:
        # Default: chạy 1 session
        run_single_session()
