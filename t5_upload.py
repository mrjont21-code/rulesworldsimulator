"""
T5: UPLOAD MONGODB - Đẩy Dữ Liệu Lên DB & Báo Cáo GitHub Actions
Yêu cầu 100% file chỉnh sửa là file code đầy đủ
Nhiệm vụ: Ghi các luật mới vào DB và tạo bảng thống kê Markdown trực quan.
"""
import os
import logging
from datetime import datetime, timezone
from config import settings
from mongo_shared import get_shared_db
logger = logging.getLogger(__name__)
class T5Upload:
    def __init__(self):
        # BUG-3 fix: dùng client dùng chung cho toàn tiến trình
        # (mongo_shared.py) thay vì mở MongoClient riêng mỗi lần
        # T5Upload được khởi tạo (main.py khởi tạo lại cho MỖI keyword).
        self.db = get_shared_db()
    def upload_rules(self, contents: list[dict], run_id: str) -> int:
        """Đẩy bản ghi sạch từ T4 vào MongoDB collection world_rules.

        BUG-5 fix: trả về SỐ THỰC SỰ ghi thành công (không phải len(contents)
        được cộng dồn trước khi biết insert_many() có thành công hay không).
        Dùng ordered=False để 1 lỗi trong batch không chặn các document còn
        lại, và bắt BulkWriteError để đọc số lượng đã ghi thành công thật từ
        `bwe.details["nInserted"]`.
        """
        logger.info("=" * 80)
        logger.info("📤 T5: UPLOAD MONGODB")
        logger.info("=" * 80)

        if self.db is None:
            logger.warning("⚠️ Không có kết nối MongoDB, bỏ qua upload.")
            return 0

        if not contents:
            logger.info("ℹ️ Không có bản ghi mới nào để tải lên.")
            return 0

        # Bổ sung metadata về lịch sử chạy cho từng document trước khi upload
        for content in contents:
            content["run_id"] = run_id
            content["uploaded_at"] = datetime.now(timezone.utc).isoformat()

        from pymongo.errors import BulkWriteError

        try:
            # Ghi hàng loạt, ordered=False: 1 document lỗi (vd trùng key)
            # không chặn các document hợp lệ khác trong cùng batch.
            result = self.db[settings.MONGODB_COLLECTION_RULES].insert_many(
                contents, ordered=False
            )
            inserted = len(result.inserted_ids)
            logger.info(f"   ✅ Đã ghi thành công {inserted}/{len(contents)} luật mới vào MongoDB.")
            return inserted
        except BulkWriteError as bwe:
            inserted = bwe.details.get("nInserted", 0)
            logger.warning(
                f"   ⚠️ Ghi MongoDB một phần: {inserted}/{len(contents)} thành công, "
                f"{len(contents) - inserted} lỗi (xem chi tiết: {bwe.details.get('writeErrors')})"
            )
            return inserted
        except Exception as e:
            logger.warning(f"   ⚠️ Lỗi khi ghi MongoDB: {e}")
            return 0
    def save_run_log(self, run_id: str, stats: dict):
        """Lưu lịch sử chạy vào DB và kết xuất báo cáo GitHub"""
        
        # 1. Lưu log vào Database để theo dõi hệ thống
        if self.db is not None:
            try:
                self.db[settings.MONGODB_COLLECTION_RUNS].insert_one({
                    "run_id": run_id,
                    "started_at": stats.get("started_at"),
                    "ended_at": datetime.now(timezone.utc).isoformat(),
                    "keywords_used": stats.get("keywords_used", []),
                    "links_found": stats.get("links_found", 0),
                    "links_scraped": stats.get("links_scraped", 0),
                    "contents_validated": stats.get("contents_validated", 0),
                    "duplicates_removed": stats.get("duplicates_removed", 0),
                    "rules_uploaded": stats.get("rules_uploaded", 0),
                    "duration_seconds": stats.get("duration_seconds", 0),
                    "status": "success"
                })
                logger.info(f"✅ Đã lưu log của Run ID {run_id} vào database.")
            except Exception as e:
                logger.warning(f"⚠️ Lỗi khi lưu log hệ thống: {e}")
        # 2. Sinh báo cáo trực quan cho GitHub Job Summaries
        self._generate_github_summary(run_id, stats)
    def _generate_github_summary(self, run_id: str, stats: dict):
        """Tạo bảng Markdown thống kê cho giao diện GitHub Actions"""
        summary_path = os.getenv("GITHUB_STEP_SUMMARY")
        
        if not summary_path:
            logger.info("ℹ️ Không tìm thấy biến môi trường GitHub Actions, bỏ qua UI Report.")
            return
        duration = stats.get("duration_seconds", 0)
        minutes, seconds = divmod(duration, 60)
        time_str = f"{int(minutes)} phút {int(seconds)} giây"
        
        keywords_str = ", ".join(stats.get("keywords_used", [])) if stats.get("keywords_used") else "N/A"

        # BUG-5 fix: badge T5 động dựa trên rules_uploaded thực tế so với
        # rules_attempted (số đã cố ghi), thay vì hardcode "🚀 Đã lưu DB"
        # bất kể insert_many() có thành công thật hay không.
        uploaded = stats.get("rules_uploaded", 0)
        attempted = stats.get("rules_attempted", 0)
        if attempted == 0:
            t5_badge = "⚪ Không có bản ghi mới"
        elif uploaded == attempted:
            t5_badge = "🟢 Hoàn tất"
        elif uploaded > 0:
            t5_badge = "🟠 Một phần"
        else:
            t5_badge = "🔴 Thất bại"

        markdown_content = f"""## 📊 Báo Cáo Thu Thập World Lore (Run ID: `{run_id}`)
**Thời gian xử lý:** {time_str}
**Từ khóa:** `{keywords_str}`
### 📈 Thống Kê Pipeline T0 - T5

| Trạm Xử Lý | Khối Lượng | Trạng Thái |
| :--- | :--- | :--- |
| **T0: Search API** | Tìm thấy {stats.get("links_found", 0)} URLs | 🟢 Hoàn tất |
| **T2: Data Scrape** | Cào thành công {stats.get("links_scraped", 0)} links | 🟢 Hoàn tất |
| **T3: Normalize** | {stats.get("contents_validated", 0)} bài đạt chuẩn | 🟢 Hoàn tất |
| **T4: Deduplicate** | Loại bỏ {stats.get("duplicates_removed", 0)} trùng lặp | 🟢 Hoàn tất |
| **T5: DB Upload** | **Lưu mới {uploaded}/{attempted} quy luật** | {t5_badge} |

> *Pipeline không xây bách khoa toàn thư — nó cào nguyên liệu thô (summary + key_facts) cho một thế giới sự sống thông minh phi-carbon, để hệ thống LLM downstream dùng dựng nhân vật, môi trường và kịch bản.*
"""
        try:
            with open(summary_path, "a", encoding="utf-8") as f:
                f.write(markdown_content + "\n")
            logger.info("✅ Đã ghi báo cáo lên màn hình GitHub Action.")
        except Exception as e:
            logger.warning(f"⚠️ Không thể ghi file báo cáo Markdown: {e}")
def run_t5(contents: list[dict], run_id: str, stats: dict):
    """Entry point cho T5

    BUG-5 fix: trước đây `stats["rules_uploaded"]` được cộng dồn bằng
    `len(contents)` NGAY khi vào hàm, trước khi biết `insert_many()` có
    thành công hay không — báo cáo GitHub Summary hiện thành công toàn bộ
    dù giữa batch có `BulkWriteError`. Giờ chỉ cộng dồn SỐ THỰC SỰ ghi
    thành công (trả về từ `upload_rules()`), và theo dõi thêm
    `rules_attempted` để so sánh thành công/thất bại ở tầng báo cáo.
    """
    uploader = T5Upload()

    attempted_count = len(contents) if contents else 0
    stats["rules_attempted"] = stats.get("rules_attempted", 0) + attempted_count

    # duplicates_removed: lấy từ stats (đã được main.py ghi đúng từ T4),
    # không tính lại ở đây tránh overwrite sai khi contents=[] (gọi lúc cuối session).
    if "duplicates_removed" not in stats:
        stats["duplicates_removed"] = 0
    if "rules_uploaded" not in stats:
        stats["rules_uploaded"] = 0

    if contents:
        inserted_count = uploader.upload_rules(contents, run_id)
        stats["rules_uploaded"] = stats.get("rules_uploaded", 0) + inserted_count

    uploader.save_run_log(run_id, stats)
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - [T5] %(message)s',
        datefmt='%H:%M:%S'
    )
    
    # Test mô phỏng dữ liệu truyền từ Main Pipeline
    test_stats = {
        "started_at": datetime.now(timezone.utc).isoformat(),
        "keywords_used": ["alternative biochemistry", "silicon lifeform"],
        "links_found": 150,
        "links_scraped": 45,
        "contents_validated": 12, # 12 bài qua T3
        "duration_seconds": 312,
        "rules_uploaded": 0,
        "rules_attempted": 0,
    }
    
    # 2 luật mới được giữ lại sau khi qua T4
    test_unique_contents = [
        {"content_hash": "hash_123", "rule_type": "biochemistry"},
        {"content_hash": "hash_456", "rule_type": "biochemistry"}
    ]
    
    run_t5(test_unique_contents, "local_test_run_999", test_stats)
