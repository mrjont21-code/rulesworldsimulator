"""
T5: UPLOAD MONGODB - Upload rules vào MongoDB
"""
import logging
from datetime import datetime, timezone
from pymongo import MongoClient
from config import settings

logger = logging.getLogger(__name__)


class T5Upload:
    def __init__(self):
        if settings.MONGODB_URI:
            self.mongo = MongoClient(settings.MONGODB_URI)
            self.db = self.mongo[settings.MONGODB_DB_NAME]
        else:
            self.mongo = None
            self.db = None

    def upload_rules(self, contents: list[dict], run_id: str):
        """Upload rules vào MongoDB"""
        logger.info("=" * 80)
        logger.info("📤 T5: UPLOAD MONGODB")
        logger.info("=" * 80)
        
        if not self.db:
            logger.warning("Không có MongoDB, bỏ qua upload")
            return
        
        # Upload vào collection biology_rules
        for content in contents:
            self.db[settings.MONGODB_COLLECTION_RULES].insert_one({
                **content,
                "status": "raw",  # Chưa qua LLM extract
                "run_id": run_id,
                "uploaded_at": datetime.now(timezone.utc).isoformat()
            })
        
        logger.info(f"✅ Đã upload {len(contents)} rules")

    def save_run_log(self, run_id: str, stats: dict):
        """Lưu log của run"""
        if not self.db:
            return
        
        self.db[settings.MONGODB_COLLECTION_RUNS].insert_one({
            "run_id": run_id,
            "started_at": stats.get("started_at"),
            "ended_at": datetime.now(timezone.utc).isoformat(),
            "keywords_generated": stats.get("keywords_generated", 0),
            "links_found": stats.get("links_found", 0),
            "links_scraped": stats.get("links_scraped", 0),
            "contents_validated": stats.get("contents_validated", 0),
            "rules_uploaded": stats.get("rules_uploaded", 0),
            "duplicates_removed": stats.get("duplicates_removed", 0),
            "status": "success"
        })
        
        logger.info(f"✅ Đã lưu run log: {run_id}")
