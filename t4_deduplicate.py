"""
T4: DEDUPLICATE - Check trùng lặp
1. Check với JSON state của keyword (local)
2. Check với MongoDB (nếu có)
"""
import os
import json
import logging
from config import settings

logger = logging.getLogger(__name__)


class T4Deduplicate:
    def __init__(self):
        # MongoDB connection (optional)
        self.mongo = None
        self.db = None
        self.existing_hashes = set()
        
        if settings.MONGODB_URI:
            try:
                from pymongo import MongoClient
                self.mongo = MongoClient(settings.MONGODB_URI, serverSelectionTimeoutMS=5000)
                self.mongo.admin.command('ping')
                self.db = self.mongo[settings.MONGODB_DB_NAME]
                
                # Load existing hashes
                for doc in self.db[settings.MONGODB_COLLECTION_CONTENT].find({}, {"content_hash": 1}):
                    self.existing_hashes.add(doc.get("content_hash"))
                
                logger.info(f"✅ MongoDB connected, {len(self.existing_hashes)} existing hashes")
            except Exception as e:
                logger.warning(f"⚠️  MongoDB connection failed: {e}")
                self.mongo = None
                self.db = None

    def get_keyword_scraped_urls(self, keyword: str) -> set[str]:
        """Lấy danh sách URLs đã scrape từ keyword state JSON"""
        from t0_search import T0Search
        searcher = T0Search()
        state = searcher.get_keyword_state(keyword)
        return set(state.get("scraped_urls", []))

    def update_keyword_scraped_urls(self, keyword: str, urls: list[str]):
        """Cập nhật danh sách URLs đã scrape vào keyword state JSON"""
        from t0_search import T0Search
        searcher = T0Search()
        state = searcher.get_keyword_state(keyword)
        
        # Add new URLs
        existing = set(state.get("scraped_urls", []))
        for url in urls:
            if url not in existing:
                state.setdefault("scraped_urls", []).append(url)
        
        state["links_scraped"] = len(state.get("scraped_urls", []))
        searcher.save_keyword_state(state)

    def check_duplicates(self, normalized_data: list[dict]) -> list[dict]:
        """Check trùng lặp"""
        logger.info("=" * 80)
        logger.info("🔍 T4: DEDUPLICATE")
        logger.info("=" * 80)
        
        # Local dedup (trong batch hiện tại)
        seen_hashes = set()
        seen_urls = set()
        
        new_data = []
        duplicate_hash_count = 0
        duplicate_url_count = 0
        
        for data in normalized_data:
            content_hash = data.get("content_hash")
            url = data.get("url")
            
            # Check URL duplicate (same URL)
            if url in seen_urls:
                logger.debug(f"   ⚠️  URL trùng: {url[:50]}")
                duplicate_url_count += 1
                continue
            
            # Check content hash duplicate
            if content_hash in seen_hashes:
                logger.debug(f"   ⚠️  Content trùng: {data['rule_id']}")
                duplicate_hash_count += 1
                continue
            
            # Check with MongoDB
            if self.db and content_hash in self.existing_hashes:
                logger.debug(f"   ⚠️  DB trùng: {data['rule_id']}")
                duplicate_hash_count += 1
                continue
            
            # Add to seen
            seen_hashes.add(content_hash)
            seen_urls.add(url)
            new_data.append(data)
        
        logger.info(f"\n📊 Kết quả:")
        logger.info(f"   Mới: {len(new_data)}")
        logger.info(f"   Trùng content: {duplicate_hash_count}")
        logger.info(f"   Trùng URL: {duplicate_url_count}")
        
        return new_data

    def save_to_local(self, contents: list[dict], run_id: str):
        """Lưu nội dung vào local JSON files"""
        # Group by keyword
        by_keyword = {}
        for content in contents:
            kw = content.get("keyword", "unknown")
            if kw not in by_keyword:
                by_keyword[kw] = []
            by_keyword[kw].append(content)
        
        # Save per keyword
        for kw, kw_contents in by_keyword.items():
            from t0_search import T0Search
            searcher = T0Search()
            
            # Update keyword state
            urls = [c["url"] for c in kw_contents]
            self.update_keyword_scraped_urls(kw, urls)
            
            # Save raw data file
            filename = searcher._normalize_keyword(kw)
            raw_path = os.path.join(settings.RAW_DIR, f"{filename}_{run_id}.json")
            
            with open(raw_path, 'w', encoding='utf-8') as f:
                json.dump(kw_contents, f, ensure_ascii=False, indent=2)
            
            logger.info(f"   💾 Saved {len(kw_contents)} items to {raw_path}")

    def save_to_mongodb(self, contents: list[dict], run_id: str):
        """Lưu vào MongoDB (nếu có)"""
        if self.db is None:
            return
        
        try:
            # Save links
            for content in contents:
                self.db[settings.MONGODB_COLLECTION_LINKS].update_one(
                    {"url": content["url"]},
                    {"$set": {
                        "url": content.get("url"),
                        "title": content.get("title"),
                        "keyword": content.get("keyword"),
                        "label": content.get("source_label"),
                        "domain": content.get("domain"),
                        "scraped_at": content.get("scraped_at"),
                        "run_id": run_id
                    }},
                    upsert=True
                )
            
            # Save content
            for content in contents:
                self.db[settings.MONGODB_COLLECTION_CONTENT].insert_one({
                    **content,
                    "run_id": run_id
                })
                
                # Add to local cache
                self.existing_hashes.add(content.get("content_hash"))
            
            logger.info(f"   ✅ Saved {len(contents)} items to MongoDB")
            
        except Exception as e:
            logger.warning(f"   ⚠️  MongoDB save failed: {e}")

    def run(self, normalized_data: list[dict], run_id: str) -> list[dict]:
        """Run full T4 pipeline"""
        # Check duplicates
        new_data = self.check_duplicates(normalized_data)
        
        if new_data:
            # Save to local
            self.save_to_local(new_data, run_id)
            
            # Save to MongoDB
            self.save_to_mongodb(new_data, run_id)
        
        return new_data


def run_t4(normalized_data: list[dict], run_id: str) -> list[dict]:
    """Entry point cho T4"""
    deduper = T4Deduplicate()
    return deduper.run(normalized_data, run_id)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - [T4] %(message)s',
        datefmt='%H:%M:%S'
    )
    
    # Test
    test_data = [{
        "rule_id": "abc123",
        "url": "https://example.com/test",
        "title": "Test",
        "content": "Test content" * 100,
        "content_hash": "def456",
        "keyword": "test"
    }]
    
    result = run_t4(test_data, "test_run")
    print(f"\n✅ Deduplicated: {len(result)} items")
