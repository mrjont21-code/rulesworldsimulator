"""
T4: DEDUPLICATE - Check trùng lặp với MongoDB
"""
import logging
from pymongo import MongoClient
from config import settings

logger = logging.getLogger(__name__)


class T4Deduplicate:
    def __init__(self):
        if settings.MONGODB_URI:
            self.mongo = MongoClient(settings.MONGODB_URI)
            self.db = self.mongo[settings.MONGODB_DB_NAME]
        else:
            self.mongo = None
            self.db = None

    def check_duplicates(self, normalized_data: list[dict]) -> list[dict]:
        """Check trùng lặp với data đã có trong MongoDB"""
        logger.info("=" * 80)
        logger.info("🔍 T4: DEDUPLICATE")
        logger.info("=" * 80)
        
        if not self.db:
            logger.warning("Không có MongoDB, bỏ qua deduplication")
            return normalized_data
        
        # Lấy tất cả content_hash đã có
        existing_hashes = set()
        for doc in self.db[settings.MONGODB_COLLECTION_CONTENT].find({}, {"content_hash": 1}):
            existing_hashes.add(doc.get("content_hash"))
        
        logger.info(f"   Đã có {len(existing_hashes)} nội dung trong DB")
        
        # Lọc data mới
        new_data = []
        duplicate_count = 0
        
        for data in normalized_data:
            content_hash = data.get("content_hash")
            
            if content_hash in existing_hashes:
                logger.info(f"   ⚠️  Trùng: {data['rule_id']}")
                duplicate_count += 1
            else:
                new_data.append(data)
        
        logger.info(f"\n📊 {len(new_data)} mới, {duplicate_count} trùng")
        
        return new_data

    def save_links(self, links: list[dict], run_id: str):
        """Lưu links đã cào vào MongoDB"""
        if not self.db:
            return
        
        for link in links:
            self.db[settings.MONGODB_COLLECTION_LINKS].insert_one({
                "url": link.get("url"),
                "title": link.get("title"),
                "keyword": link.get("keyword"),
                "label": link.get("label"),
                "scraped_at": link.get("scraped_at"),
                "run_id": run_id
            })

    def save_content(self, contents: list[dict], run_id: str):
        """Lưu nội dung vào MongoDB"""
        if not self.db:
            return
        
        for content in contents:
            self.db[settings.MONGODB_COLLECTION_CONTENT].insert_one({
                **content,
                "run_id": run_id
            })
