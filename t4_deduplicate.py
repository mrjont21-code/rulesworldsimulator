"""
T4: DEDUPLICATE - Bộ Lọc Trùng Lặp
Yêu cầu 100% file chỉnh sửa là file code đầy đủ
Nhiệm vụ: Đối chiếu content_hash với MongoDB, giữ lại các bản ghi chưa từng tồn tại.
"""
import os
import json
import logging
from config import settings

logger = logging.getLogger(__name__)

class T4Deduplicate:
    def __init__(self):
        self.mongo = None
        self.db = None
        self.existing_hashes = set()
        
        if settings.MONGODB_URI:
            try:
                from pymongo import MongoClient
                self.mongo = MongoClient(settings.MONGODB_URI, serverSelectionTimeoutMS=5000)
                self.mongo.admin.command('ping')
                self.db = self.mongo[settings.MONGODB_DB_NAME]
                
                # Nạp toàn bộ content_hash đã tồn tại từ Collection lưu Luật Hóa Sinh
                for doc in self.db[settings.MONGODB_COLLECTION_RULES].find({}, {"content_hash": 1}):
                    if "content_hash" in doc:
                        self.existing_hashes.add(doc["content_hash"])
                
                logger.info(f"✅ MongoDB connected, loaded {len(self.existing_hashes)} existing hashes from DB.")
            except Exception as e:
                logger.warning(f"⚠️ MongoDB connection failed in T4: {e}")
                self.mongo = None
                self.db = None

    def check_duplicates(self, normalized_data: list[dict]) -> list[dict]:
        """Lọc ra các bản ghi mới (chưa có trong DB)"""
        logger.info("=" * 80)
        logger.info("🔍 T4: DEDUPLICATE DATA")
        logger.info("=" * 80)
        
        new_data = []
        duplicates_count = 0
        
        for item in normalized_data:
            # Mã băm được T3 tạo ra
            content_hash = item.get("content_hash")
            
            if not content_hash:
                logger.warning("⚠️ Bản ghi không có content_hash, bỏ qua.")
                continue
                
            if content_hash in self.existing_hashes:
                duplicates_count += 1
            else:
                new_data.append(item)
                # Thêm ngay vào local cache để tránh trùng lặp 2 bài giống nhau trong cùng 1 batch
                self.existing_hashes.add(content_hash)
        
        logger.info(f"📊 Kết quả lọc:")
        logger.info(f"   - Đầu vào: {len(normalized_data)} bản ghi")
        logger.info(f"   - Trùng lặp: {duplicates_count} bản bị loại")
        logger.info(f"   - Giữ lại: {len(new_data)} bản ghi mới tinh")
        
        return new_data

    def run(self, normalized_data: list[dict]) -> list[dict]:
        """Chạy pipeline T4"""
        return self.check_duplicates(normalized_data)

def run_t4(normalized_data: list[dict]) -> list[dict]:
    """Entry point cho T4"""
    deduper = T4Deduplicate()
    return deduper.run(normalized_data)

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - [T4] %(message)s',
        datefmt='%H:%M:%S'
    )
    
    # Test mô phỏng
    test_data = [
        {"content_hash": "hash_silicon_acid_1", "rule_type": "alternative_biochemistry"},
        {"content_hash": "hash_calcium_methane_2", "rule_type": "alternative_biochemistry"},
        {"content_hash": "hash_silicon_acid_1", "rule_type": "alternative_biochemistry"} # Sẽ bị loại vì trùng
    ]
    
    unique_data = run_t4(test_data)
    print(f"\n✅ Dữ liệu sau khi lọc T4 sẵn sàng cho T5: {len(unique_data)} bản ghi")
