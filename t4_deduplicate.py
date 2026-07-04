"""
T4: DEDUPLICATE - Bộ Lọc Trùng Lặp & Lưu JSON Local
Yêu cầu 100% file chỉnh sửa là file code đầy đủ
Nhiệm vụ: Đối chiếu content_hash, loại bỏ trùng lặp và lưu file JSON ra thư mục data/raw/ để GitHub commit.
"""
import os
import json
import logging
from config import settings
from mongo_shared import get_shared_db, get_existing_hashes

logger = logging.getLogger(__name__)

class T4Deduplicate:
    def __init__(self):
        # BUG-3 fix: dùng client + cache hash DÙNG CHUNG cho toàn tiến
        # trình (mongo_shared.py) thay vì mở MongoClient riêng và quét lại
        # toàn bộ collection `world_rules` mỗi lần T4Deduplicate được khởi
        # tạo (main.py khởi tạo lại class này cho MỖI keyword).
        self.db = get_shared_db()
        self.existing_hashes = get_existing_hashes()

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

    def save_to_local(self, contents: list[dict], run_id: str):
        """Lưu nội dung vào local JSON files để GitHub Actions có dữ liệu commit lên repo"""
        if not contents:
            return
            
        # Gom nhóm dữ liệu theo từng keyword
        by_keyword = {}
        for content in contents:
            kw = content.get("keyword", "unknown")
            if kw not in by_keyword:
                by_keyword[kw] = []
            by_keyword[kw].append(content)
        
        # Lưu file theo từng keyword
        for kw, kw_contents in by_keyword.items():
            try:
                from t0_search import T0Search
                searcher = T0Search()
                
                # Cập nhật state (những URL đã cào thành công)
                urls = [c["url"] for c in kw_contents]
                state = searcher.get_keyword_state(kw)
                existing = set(state.get("scraped_urls", []))
                for url in urls:
                    if url not in existing:
                        state.setdefault("scraped_urls", []).append(url)
                state["links_scraped"] = len(state.get("scraped_urls", []))
                searcher.save_keyword_state(state)
                
                # Ghi ra file JSON trong thư mục data/raw
                filename = searcher._normalize_keyword(kw)
                raw_path = os.path.join(settings.RAW_DIR, f"{filename}_{run_id}.json")
                
                with open(raw_path, 'w', encoding='utf-8') as f:
                    json.dump(kw_contents, f, ensure_ascii=False, indent=2)
                
                logger.info(f"   💾 Đã lưu thành công file cục bộ: {raw_path} ({len(kw_contents)} bản ghi)")
            except Exception as e:
                logger.error(f"   ❌ Lỗi khi lưu file JSON cục bộ cho keyword '{kw}': {e}")

    def run(self, normalized_data: list[dict], run_id: str) -> list[dict]:
        """Chạy pipeline T4"""
        new_data = self.check_duplicates(normalized_data)
        if new_data:
            self.save_to_local(new_data, run_id)
        return new_data

def run_t4(normalized_data: list[dict], run_id: str) -> list[dict]:
    """Entry point cho T4 (Nhận đủ 2 biến từ main.py)"""
    deduper = T4Deduplicate()
    return deduper.run(normalized_data, run_id)

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - [T4] %(message)s',
        datefmt='%H:%M:%S'
    )
    
    # Test mô phỏng
    test_data = [
        {"content_hash": "hash_silicon_acid_1", "rule_type": "biochemistry", "keyword": "test_kw", "url": "url1"},
        {"content_hash": "hash_calcium_methane_2", "rule_type": "biochemistry", "keyword": "test_kw", "url": "url2"},
        {"content_hash": "hash_silicon_acid_1", "rule_type": "biochemistry", "keyword": "test_kw", "url": "url1"} # Sẽ bị loại
    ]
    
    unique_data = run_t4(test_data, "run_test_123")
    print(f"\n✅ Dữ liệu sau khi lọc T4 sẵn sàng cho T5: {len(unique_data)} bản ghi")
