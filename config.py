"""
Config cho Rulesworld Scraper - Anti-Ban Mode
"""
import os

class Settings:
    # === TIMER POMODORO ===
    WORK_MINUTES = 25
    BREAK_MINUTES = 15
    
    # === SEARCH (CHẬM LẠI) ===
    LINKS_PER_SEARCH = 20
    SEARCH_DELAY_SECONDS = 0  # Không dùng nữa, dùng stealth.human_delay()
    
    # === ANTI-BAN DELAYS ===
    DELAY_BETWEEN_REQUESTS = 0  # Không dùng nữa
    MIN_REQUEST_DELAY = 8.0     # Tối thiểu 8 giây giữa các request
    MAX_REQUEST_DELAY = 20.0    # Tối đa 20 giây
    MIN_KEYWORD_BREAK = 30.0    # Nghỉ tối thiểu 30s giữa keywords
    MAX_KEYWORD_BREAK = 60.0    # Nghỉ tối đa 60s giữa keywords
    
    # === KEYWORDS ===
    KEYWORDS_FILE = "keywords.json"
    KEYWORD_STATE_DIR = "keyword_states"
    
    # === SCRAPING ===
    MIN_CONTENT_LENGTH = 300
    MIN_DRAMA_KEYWORDS = 2
    
    # === FILES ===
    ENGINES_FILE = "search_engines.json"
    BLACKBOOK_FILE = "blackbook.json"
    
    # === DATA DIRS ===
    DATA_DIR = "data"
    RAW_DIR = "data/raw"
    QUEUE_DIR = "data/queue"
    
    # === MONGODB (Optional) ===
    MONGODB_URI = os.getenv("MONGODB_URI", "")
    MONGODB_DB_NAME = os.getenv("MONGODB_DB_NAME", "rulesworld")
    MONGODB_COLLECTION_KEYWORDS = "keywords"
    MONGODB_COLLECTION_LINKS = "links"
    MONGODB_COLLECTION_CONTENT = "content"
    MONGODB_COLLECTION_RULES = "world_rules"
    MONGODB_COLLECTION_RUNS = "run_logs"
    
    # === DRAMA / VISUAL / CIVILIZATION KEYWORDS ===
    # Trước đây gọi là BIOLOGY_KEYWORDS: bám thuật ngữ hàn lâm (biochemistry,
    # enzyme, genome...) khiến pipeline hành xử như nhà khoa học, không phải
    # nguồn nguyên liệu thô cho một thế giới SỰ SỐNG THÔNG MINH phi-carbon.
    # Mục tiêu KHÔNG phải xây bách khoa toàn thư sinh vật học, mà cào nguyên
    # liệu để hệ thống downstream (LLM khác, ngoài pipeline này) dựng nhân
    # vật, môi trường sống và "quy luật sống" cho thế giới mô phỏng — bao
    # gồm cả cơ chế sinh tồn LẪN cấu trúc xã hội/văn minh, vì đây là giống
    # loài có trí tuệ, không phải chỉ là quái vật/hệ sinh thái.
    # Đây là single source of truth cho cả T2 (validate_content, cổng chặn
    # nội dung không đạt) lẫn T3 (extractive_summary, boost điểm câu).
    DRAMA_KEYWORDS = [
        # Chuyển động / sinh tồn (thể chất cá thể)
        "locomotion", "hydraulic joint", "ambush", "camouflage", "predator",
        "prey", "hunting", "stalking", "burrow",
        # Chiến đấu / tổn thương / điểm yếu
        "acid spray", "corrode", "corrosive", "venom", "claw", "exoskeleton",
        "armor plate", "regenerate", "mutation", "weak point", "fatal flaw",
        "vulnerable", "wound", "scar",
        # Cái chết / biến đổi hình thái
        "shatter", "crystallize", "dissolve", "disintegrate", "crumble",
        "molt", "decay", "consume", "devour", "sacrifice",
        # Hiệu ứng thị giác
        "bioluminescent", "glow", "pulse", "crack", "fracture", "shimmer",
        "iridescent", "translucent", "pulsating", "writhing",
        # Xã hội / văn minh / trí tuệ (giống loài THÔNG MINH, không chỉ quái
        # vật) — cấu trúc quyền lực, công nghệ, văn hóa, xung đột chính trị
        "caste", "hierarchy", "faction", "rebellion", "betrayal", "symbiosis",
        "colony", "empire", "war", "alliance", "ritual", "civilization",
        "technology", "architecture", "governance", "diplomacy", "trade",
        "religion", "belief system", "taboo", "language", "communication",
        "philosophy", "tradition", "clan", "dynasty", "revolution",
        "swarm", "hive mind", "parasite", "infect",
        # Môi trường / thảm họa (móc nối với dữ liệu thời tiết/tin tức đời thực
        # ở hệ thống downstream — pipeline này chỉ cào vocab, không tự dịch)
        "storm", "eruption", "radiation", "toxic atmosphere", "cataclysm",
        "extremophile", "hazard", "hostile environment",
    ]

    # Alias tương thích ngược cho code cũ chưa migrate (không dùng cho logic mới)
    BIOLOGY_KEYWORDS = DRAMA_KEYWORDS

settings = Settings()

for d in [settings.DATA_DIR, settings.RAW_DIR, settings.QUEUE_DIR, settings.KEYWORD_STATE_DIR]:
    os.makedirs(d, exist_ok=True)
