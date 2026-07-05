"""
MONGO_SHARED — Client MongoDB & cache hash dùng chung toàn tiến trình
======================================================================
BUG-3 FIX (QA Audit): trước đây `T4Deduplicate` và `T5Upload` mỗi class
tự mở 1 `MongoClient` riêng, và `main.py` khởi tạo lại 2 class này cho
MỖI keyword trong vòng lặp Pomodoro (tối đa MAX_LOOPS session × N keyword
mỗi session) — không bao giờ đóng connection (resource leak), và
`T4Deduplicate.__init__` quét TOÀN BỘ collection `world_rules` (không có
TTL, phình to theo thời gian) mỗi lần khởi tạo (lỗ hổng hiệu năng).

Module này cung cấp:
  - `get_shared_client()`  : 1 `MongoClient` DUY NHẤT cho toàn tiến trình,
                             tái sử dụng qua mọi session/keyword.
  - `get_shared_db()`      : database handle dựa trên client dùng chung.
  - `get_existing_hashes()`: nạp `content_hash` từ `world_rules` ĐÚNG 1
                             LẦN (cache module-level), các lần gọi sau
                             trả về cùng 1 set đối tượng (mutate tại chỗ
                             khi có hash mới, không query lại DB).
  - `close_shared_client()`: đóng connection — gọi trong khối `finally`
                             của `main.py` (`--loop` hoặc `--once`), đảm
                             bảo connection luôn được giải phóng dù chạy
                             thành công hay lỗi giữa chừng.
"""
import logging

from config import settings

logger = logging.getLogger(__name__)

_client = None
_db = None
_existing_hashes: set[str] | None = None


def get_shared_client():
    """Trả về MongoClient dùng chung — chỉ tạo mới nếu chưa có hoặc chưa
    kết nối được (MONGODB_URI rỗng). Idempotent qua nhiều lần gọi."""
    global _client
    if _client is not None:
        return _client

    if not settings.MONGODB_URI:
        return None

    try:
        from pymongo import MongoClient

        _client = MongoClient(settings.MONGODB_URI, serverSelectionTimeoutMS=5000)
        _client.admin.command("ping")
        logger.info("✅ MongoDB connected (shared client — dùng chung toàn tiến trình).")
    except Exception as e:
        logger.warning(f"⚠️ MongoDB connection failed (shared client): {e}")
        _client = None

    return _client


def get_shared_db():
    """Trả về database handle dựa trên client dùng chung. None nếu không
    kết nối được (chạy offline / MONGODB_URI rỗng)."""
    global _db
    if _db is not None:
        return _db

    client = get_shared_client()
    if client is None:
        return None

    _db = client[settings.MONGODB_DB_NAME]
    ensure_indexes(_db)
    return _db


def ensure_indexes(db) -> None:
    """Đảm bảo các Index cần thiết cho collection `world_rules` tồn tại.
    Idempotent — `create_index` không lỗi nếu index cùng cấu hình đã có,
    nên gọi lại nhiều lần (mỗi lần `get_shared_db()` kết nối lần đầu) là
    an toàn.

    - `content_hash`: unique -> chống trùng lặp ở TẦNG DB (defense-in-depth
      bên cạnh dedup ở tầng ứng dụng qua `get_existing_hashes()`).
    - `keyword`, `rule_type`: tăng tốc truy vấn lọc theo các trường này.

    `background=True` để không khóa collection khi tạo index trên dữ
    liệu đã có sẵn.
    """
    try:
        coll = db[settings.MONGODB_COLLECTION_RULES]
        coll.create_index("content_hash", unique=True, background=True)
        coll.create_index("keyword", background=True)
        coll.create_index("rule_type", background=True)
        logger.info("✅ Đã đảm bảo indexes (content_hash unique, keyword, rule_type) cho 'world_rules'.")
    except Exception as e:
        logger.warning(f"⚠️ Không thể tạo indexes cho 'world_rules': {e}")


def get_existing_hashes() -> set[str]:
    """Nạp toàn bộ `content_hash` đã tồn tại trong `world_rules` — CHỈ 1
    LẦN cho toàn tiến trình (full collection scan tốn kém, không lặp lại
    mỗi khi T4Deduplicate được khởi tạo lại cho keyword mới). Các bản ghi
    mới thêm vào set này bằng `.add()` tại nơi gọi (T4), không query lại
    DB để đồng bộ.

    Trả về set rỗng (không raise) nếu không có kết nối DB — pipeline vẫn
    chạy được ở chế độ offline, chỉ mất khả năng dedup chống trùng với dữ
    liệu cũ đã có trên DB (dedup trong-batch vẫn hoạt động qua set này).
    """
    global _existing_hashes
    if _existing_hashes is not None:
        return _existing_hashes

    _existing_hashes = set()
    db = get_shared_db()
    if db is None:
        return _existing_hashes

    try:
        for doc in db[settings.MONGODB_COLLECTION_RULES].find({}, {"content_hash": 1}):
            if "content_hash" in doc:
                _existing_hashes.add(doc["content_hash"])
        logger.info(f"✅ Đã nạp {len(_existing_hashes)} content_hash hiện có từ DB (1 lần duy nhất).")
    except Exception as e:
        logger.warning(f"⚠️ Không thể nạp existing_hashes từ MongoDB: {e}")

    return _existing_hashes


def close_shared_client():
    """Đóng MongoClient dùng chung — gọi trong `finally` ở `main.py` để
    đảm bảo connection luôn được giải phóng, dù pipeline chạy `--loop`
    hay `--once`, dù kết thúc thành công hay lỗi giữa chừng."""
    global _client, _db, _existing_hashes
    if _client is not None:
        try:
            _client.close()
            logger.info("🔒 Đã đóng MongoDB shared client.")
        except Exception as e:
            logger.warning(f"⚠️ Lỗi khi đóng MongoDB shared client: {e}")
    _client = None
    _db = None
    _existing_hashes = None
