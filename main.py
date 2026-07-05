"""
MAIN: Orchestrator - TUẦN TỰ TỪNG KEYWORD
Flow: Keyword A → Search → Classify → Scrape → Normalize → Dedup → Upload → Keyword B → ...
"""
import os
import re
import sys
import time
import logging
import uuid
import json
import argparse
from datetime import datetime, timezone

from config import settings
from t0_search import run_t0_single_keyword
from t1_classify import run_t1
from t2_scrape import run_t2
from t3_normalize import run_t3
from t4_deduplicate import run_t4
from t5_upload import run_t5
from t6_rule_engine_bridge import forge_and_validate_uploaded_rules
from stealth import keyword_break
from mongo_shared import close_shared_client

MAX_LOOPS = int(os.getenv("MAX_LOOPS", "8"))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(name)s] %(message)s',
    datefmt='%H:%M:%S',
    stream=sys.stderr
)
logger = logging.getLogger("MAIN")

# ============================================================
# CHECKPOINT: cơ chế phục hồi thô sơ, chống mất tiến độ khi
# tiến trình bị dừng giữa chừng ở T2 (scrape - chậm 8-20s/link).
# Mỗi keyword có 1 file JSON riêng trong data/checkpoints/.
# ============================================================
CHECKPOINT_DIR = os.path.join("data", "checkpoints")


def _checkpoint_path(keyword: str) -> str:
    """Chuẩn hoá keyword thành tên file an toàn (giữ ký tự chữ/số/gạch dưới)."""
    safe = re.sub(r'[^\w\-]+', '_', keyword.strip(), flags=re.UNICODE)
    return os.path.join(CHECKPOINT_DIR, f"{safe}.json")


def save_checkpoint(keyword: str, classified_links: list) -> None:
    """Ghi list links đã classify (sau T1) vào file checkpoint của keyword."""
    os.makedirs(CHECKPOINT_DIR, exist_ok=True)
    path = _checkpoint_path(keyword)
    try:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(
                {"keyword": keyword, "classified_links": classified_links},
                f, ensure_ascii=False, indent=2
            )
        logger.info(f"💾 Đã lưu checkpoint '{keyword}' ({len(classified_links)} links)")
    except OSError as e:
        logger.error(f"❌ Lỗi lưu checkpoint '{keyword}': {e}")


def load_checkpoint(keyword: str):
    """Đọc checkpoint của keyword. Trả về list nếu có, None nếu không có/lỗi."""
    path = _checkpoint_path(keyword)
    if not os.path.exists(path):
        return None
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data.get("classified_links")
    except (json.JSONDecodeError, OSError) as e:
        logger.warning(f"⚠️ Checkpoint '{keyword}' đọc lỗi ({e}), bỏ qua")
        return None


def clear_checkpoint(keyword: str) -> None:
    """Xóa file checkpoint của keyword (khi đã xử lý xong hoặc không cần nữa)."""
    path = _checkpoint_path(keyword)
    if os.path.exists(path):
        try:
            os.remove(path)
            logger.info(f"🧹 Đã xóa checkpoint '{keyword}'")
        except OSError as e:
            logger.error(f"❌ Lỗi xóa checkpoint '{keyword}': {e}")


def _find_pending_checkpoint():
    """
    Quét data/checkpoints/ tìm phiên dở dang.
    Lưu ý: keyword chỉ được T0 xác định SAU khi chạy (round-robin nội bộ),
    nên không thể "load_checkpoint(keyword) trước run_t0" theo đúng nghĩa đen -
    thay vào đó ta quét file để biết keyword nào đang dang dở, nếu có.
    Trả về (keyword, classified_links) hoặc None.
    """
    if not os.path.isdir(CHECKPOINT_DIR):
        return None
    for fname in sorted(os.listdir(CHECKPOINT_DIR)):
        if not fname.endswith(".json"):
            continue
        fpath = os.path.join(CHECKPOINT_DIR, fname)
        try:
            with open(fpath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            keyword = data.get("keyword")
            classified_links = data.get("classified_links")
            if keyword and classified_links is not None:
                return keyword, classified_links
        except (json.JSONDecodeError, OSError):
            continue
    return None


def load_keywords() -> list[str]:
    """Load 35 keywords"""
    path = settings.KEYWORDS_FILE
    if not os.path.exists(path):
        logger.error(f"Không tìm thấy {path}")
        sys.exit(1)
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f).get("keywords", [])


def process_single_keyword(keywords: list[str], run_id: str, stats: dict) -> bool:
    """
    Xử lý 1 keyword hoàn chỉnh: Search → Classify → Scrape → Normalize → Dedup → Upload
    Trả về True nếu xử lý thành công, False nếu hết keyword/thời gian
    """
    # === CHECKPOINT: kiểm tra phiên dở dang trước khi chạy T0 ===
    pending = _find_pending_checkpoint()

    if pending is not None:
        keyword, classified = pending
        stats["keywords_used"].append(keyword)
        logger.info("🔄 Phục hồi Checkpoint, bỏ qua T0 & T1")
    else:
        # === T0: Search 1 keyword ===
        result = run_t0_single_keyword(keywords)
        if result is None:
            return False

        keyword, links, state = result
        stats["keywords_used"].append(keyword)
        stats["links_found"] += len(links)

        # === T1: Classify ===
        classified = run_t1(links)

        # Lưu checkpoint ngay sau T1, trước khi vào T2 (chậm, dễ bị dừng giữa chừng)
        save_checkpoint(keyword, classified)

    # === T2: Scrape (CHẬM - 8-20s/link) ===
    scraped = run_t2(classified)
    stats["links_scraped"] += len(scraped)
    
    if not scraped:
        clear_checkpoint(keyword)
        return True  # Vẫn trả về True để chuyển keyword khác
    
    # === T3: Normalize ===
    normalized = run_t3(scraped)
    stats["contents_validated"] += len(normalized)  # T3 output = số bài đạt chuẩn

    # === T4: Deduplicate & Save ===
    unique = run_t4(normalized, run_id)
    stats["duplicates_removed"] += len(normalized) - len(unique)

    # === T5: Upload ===
    # T5 sẽ cộng dồn rules_uploaded nội bộ; không cộng thêm ở đây tránh double-count
    run_t5(unique, run_id, stats)

    # === CHECKPOINT: T5 thành công -> xóa checkpoint, không cần phục hồi nữa ===
    clear_checkpoint(keyword)

    # === T6 -> rule_engine: Forge Blueprint & kiểm tra tính nhất quán ===
    # BẮT BUỘC chạy sau khi T5 hoàn thành, trước khi vòng lặp keyword kết
    # thúc (xem t6_rule_engine_bridge.py để biết chi tiết adapter và các
    # giới hạn đã biết giữa 2 bộ schema khác nhau của T6 và rule_engine).
    forge_and_validate_uploaded_rules(unique, stats)

    return True


def run_pomodoro_loop():
    """Loop Pomodoro với xử lý tuần tự từng keyword"""
    keywords = load_keywords()
    logger.info("🎯 RULESWORLD SCRAPER - ANTI-BAN MODE")
    logger.info(f"   Keywords: {len(keywords)}")
    logger.info(f"   Delay/req: {settings.MIN_REQUEST_DELAY}-{settings.MAX_REQUEST_DELAY}s")
    logger.info(f"   Break/kw: {settings.MIN_KEYWORD_BREAK}-{settings.MAX_KEYWORD_BREAK}s")
    logger.info(f"   Max loops: {MAX_LOOPS}")
    logger.info("")
    
    session_count = 0
    
    try:
        while session_count < MAX_LOOPS:
            session_count += 1
            run_id = f"run_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
            session_start = time.time()
            
            logger.info("\n" + "🟢" * 40)
            logger.info(f"📝 SESSION #{session_count}/{MAX_LOOPS}")
            logger.info(f"   Run ID: {run_id}")
            logger.info(f"   Start: {datetime.now().strftime('%H:%M:%S')}")
            logger.info("🟢" * 40 + "\n")
            
            stats = {
                "started_at": datetime.now(timezone.utc).isoformat(),
                "keywords_used": [],
                "links_found": 0,
                "links_scraped": 0,
                "contents_validated": 0,
                "duplicates_removed": 0,
                "rules_uploaded": 0,
                "rules_attempted": 0,
                "blueprints_forged": 0,
                "blueprints_validation_errors": 0,
                "blueprints_validation_warnings": 0,
                "blueprints_validation_skipped": 0,
            }
            
            # XỬ LÝ TUẦN TỰ TỪNG KEYWORD
            while True:
                # Check thời gian 25 phút
                elapsed = time.time() - session_start
                if elapsed >= (settings.WORK_MINUTES * 60 - 30):
                    logger.info(f"\n⏰ Hết 25 phút (đã dùng {elapsed/60:.1f} phút)")
                    break
                
                # Xử lý 1 keyword
                success = process_single_keyword(keywords, run_id, stats)
                
                if not success:
                    logger.info("🏁 Hết keyword hoặc không tìm được link mới")
                    break
                
                # NGHỈ DÀI giữa các keywords
                keyword_break(
                    min_sec=settings.MIN_KEYWORD_BREAK,
                    max_sec=settings.MAX_KEYWORD_BREAK
                )
            
            # Session summary
            stats["duration_seconds"] = time.time() - session_start
            logger.info("\n" + "=" * 80)
            logger.info(f"📊 SESSION #{session_count} SUMMARY")
            logger.info("=" * 80)
            logger.info(f"   Duration:    {stats['duration_seconds']/60:.1f} phút")
            logger.info(f"   Keywords:    {len(stats['keywords_used'])}")
            logger.info(f"   Links:       {stats['links_found']} found → {stats['links_scraped']} scraped")
            logger.info(f"   Contents:    {stats['contents_validated']} valid ({stats['duplicates_removed']} dup)")
            logger.info(
                f"   Blueprints:  {stats['blueprints_forged']} forged "
                f"({stats['blueprints_validation_errors']} lỗi, "
                f"{stats['blueprints_validation_warnings']} cảnh báo, "
                f"{stats['blueprints_validation_skipped']} bỏ qua)"
            )
            logger.info("=" * 80)
            
            # Save run log
            run_t5([], run_id, stats)
            
            # Nghỉ Pomodoro nếu chưa phải vòng cuối
            if session_count < MAX_LOOPS:
                break_sec = settings.BREAK_MINUTES * 60
                logger.info("\n" + "🔴" * 40)
                logger.info(f"☕ POMODORO BREAK - {settings.BREAK_MINUTES} phút")
                next_t = datetime.fromtimestamp(time.time() + break_sec).strftime('%H:%M:%S')
                logger.info(f"   Next session: {next_t}")
                logger.info("🔴" * 40 + "\n")
                time.sleep(break_sec)
            else:
                logger.info("\n🏁 ĐẠT GIỚI HẠN VÒNG LẶP")
                
    except KeyboardInterrupt:
        logger.info("\n🛑 Dừng bởi người dùng")


def run_single_session():
    """Chạy 1 session (test)"""
    global MAX_LOOPS
    MAX_LOOPS = 1
    keywords = load_keywords()
    
    run_id = f"test_{uuid.uuid4().hex[:8]}"
    stats = {
        "started_at": datetime.now(timezone.utc).isoformat(),
        "keywords_used": [], "links_found": 0, "links_scraped": 0,
        "contents_validated": 0, "duplicates_removed": 0, "rules_uploaded": 0,
        "rules_attempted": 0, "blueprints_forged": 0,
        "blueprints_validation_errors": 0, "blueprints_validation_warnings": 0,
        "blueprints_validation_skipped": 0,
    }
    
    process_single_keyword(keywords, run_id, stats)
    
    logger.info(f"\n📊 Test hoàn tất: {stats}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--loop", action="store_true", help="Chạy loop Pomodoro")
    parser.add_argument("--once", action="store_true", help="Chạy 1 keyword (test)")
    args = parser.parse_args()

    # BUG-3 fix: đảm bảo MongoClient dùng chung (mongo_shared.py) luôn
    # được đóng khi tiến trình kết thúc — chạy dù --loop hay --once, dù
    # thành công hay có exception bay ra giữa chừng.
    try:
        if args.loop:
            run_pomodoro_loop()
        else:
            run_single_session()
    finally:
        close_shared_client()
