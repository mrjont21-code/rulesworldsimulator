"""
World Lore Harvester - Pipeline T0-T5
Chạy tay (giai đoạn 1) hoặc tự động 2 lần/ngày (giai đoạn 2)
"""
import os
import sys
import logging
import time
from datetime import datetime, timezone

from config import settings
from pipeline.t0_search import T0Search
from pipeline.t1_classify import T1Classify
from pipeline.t2_scrape import T2Scrape
from pipeline.t3_normalize import T3Normalize
from pipeline.t4_deduplicate import T4Deduplicate
from pipeline.t5_upload import T5Upload

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("main")


def run_pipeline():
    """Chạy pipeline T0-T5"""
    
    # Generate run_id
    run_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    started_at = datetime.now(timezone.utc).isoformat()
    
    logger.info("=" * 80)
    logger.info(f"🚀 BẮT ĐẦU PIPELINE - Run ID: {run_id}")
    logger.info("=" * 80)
    
    stats = {
        "run_id": run_id,
        "started_at": started_at,
        "keywords_generated": 0,
        "links_found": 0,
        "links_scraped": 0,
        "contents_validated": 0,
        "rules_uploaded": 0,
        "duplicates_removed": 0
    }
    
    start_time = time.time()
    
    try:
        # T0: Search
        t0 = T0Search()
        links = t0.run(run_id)
        stats["links_found"] = len(links)
        stats["keywords_generated"] = 5  # Giả sử sinh 5 từ khóa
        
        if not links:
            logger.error("❌ T0 không tìm được link nào")
            return
        
        # Check thời gian
        elapsed = time.time() - start_time
        if elapsed > 20 * 60:  # 20 phút
            logger.warning("⚠️  Gần hết thời gian, dừng pipeline")
            return
        
        # T1: Classify
        t1 = T1Classify()
        classified_links = t1.classify_links(links)
        
        # T2: Scrape
        t2 = T2Scrape()
        scraped_contents = t2.scrape_links(classified_links)
        stats["links_scraped"] = len(scraped_contents)
        
        # Check thời gian
        elapsed = time.time() - start_time
        if elapsed > 22 * 60:  # 22 phút
            logger.warning("⚠️  Gần hết thời gian, dừng pipeline")
            return
        
        # T3: Normalize
        t3 = T3Normalize()
        normalized_contents = t3.normalize_all(scraped_contents)
        stats["contents_validated"] = len(normalized_contents)
        
        # T4: Deduplicate
        t4 = T4Deduplicate()
        new_contents = t4.check_duplicates(normalized_contents)
        stats["duplicates_removed"] = len(normalized_contents) - len(new_contents)
        
        # Lưu links và content vào MongoDB
        t4.save_links(classified_links, run_id)
        t4.save_content(new_contents, run_id)
        
        # T5: Upload
        t5 = T5Upload()
        t5.upload_rules(new_contents, run_id)
        stats["rules_uploaded"] = len(new_contents)
        
        # Lưu run log
        t5.save_run_log(run_id, stats)
        
        # Tổng kết
        elapsed = time.time() - start_time
        logger.info("=" * 80)
        logger.info("✅ PIPELINE HOÀN TẤT")
        logger.info("=" * 80)
        logger.info(f"   Thời gian: {elapsed:.1f}s ({elapsed/60:.1f} phút)")
        logger.info(f"   Keywords: {stats['keywords_generated']}")
        logger.info(f"   Links: {stats['links_found']}")
        logger.info(f"   Scraped: {stats['links_scraped']}")
        logger.info(f"   Validated: {stats['contents_validated']}")
        logger.info(f"   Duplicates: {stats['duplicates_removed']}")
        logger.info(f"   Uploaded: {stats['rules_uploaded']}")
        
    except Exception as e:
        logger.error(f"❌ Pipeline lỗi: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    run_pipeline()
