"""
Config - Foundational Knowledge Engine (World Simulator)
=========================================================
Pipeline này là hệ thống thu thập tri thức khoa học khách quan để xây dựng
nền tảng quy luật vũ trụ mô phỏng. Mọi hằng số ở đây phục vụ mục tiêu đó.
"""
import logging
import os
import sys

logger = logging.getLogger(__name__)


class Settings:
    # === TIMER POMODORO ===
    WORK_MINUTES = 25
    BREAK_MINUTES = 15

    # === SEARCH ===
    LINKS_PER_SEARCH = 20
    SEARCH_DELAY_SECONDS = 0  # Không dùng nữa, dùng stealth.human_delay()

    # === ANTI-BAN DELAYS ===
    DELAY_BETWEEN_REQUESTS = 0   # Không dùng nữa
    MIN_REQUEST_DELAY = 8.0      # Tối thiểu 8 giây giữa các request
    MAX_REQUEST_DELAY = 20.0     # Tối đa 20 giây
    MIN_KEYWORD_BREAK = 30.0     # Nghỉ tối thiểu 30s giữa keywords
    MAX_KEYWORD_BREAK = 60.0     # Nghỉ tối đa 60s giữa keywords

    # === KEYWORDS ===
    KEYWORDS_FILE = "keywords.json"
    KEYWORD_STATE_DIR = "keyword_states"

    # === SCRAPING ===
    MIN_CONTENT_LENGTH = 300
    # Ngưỡng lọc chất lượng tại T2 — đặt thấp (2) vì văn phong academic/báo
    # cáo khoa học thường ngắn gọn, không lặp từ khóa dày như nội dung phổ thông.
    # Nâng lên 3–4 chỉ khi pipeline nhập quá nhiều nội dung không liên quan
    # sau khi đã xác nhận bằng dữ liệu mẫu thật.
    MIN_ONTOLOGY_KEYWORDS = 2

    # === FILES ===
    ENGINES_FILE = "search_engines.json"
    BLACKBOOK_FILE = "blackbook.json"

    # === PRE-UPLOAD HARD FILTER (MVP — chưa cần AI lọc) ===
    # LƯU Ý: KHÁC với MIN_CONTENT_LENGTH (300) ở mục SCRAPING phía trên —
    # hằng số đó dùng cho T2 (content quality gate lúc scrape, dựa trên
    # SCIENCE_ONTOLOGY_KEYWORDS). Bộ hằng số dưới đây dùng cho bước lọc
    # rác cứng NGAY TRƯỚC KHI UPLOAD lên MongoDB (T5). Đặt tên riêng
    # (FILTER_MIN_CONTENT_LENGTH) để không đè lên logic T2 đã có.
    MIN_TITLE_LENGTH = 10
    FILTER_MIN_CONTENT_LENGTH = 200
    ALLOWED_LANGUAGES = ["en"]  # Tạm thời chỉ lấy tiếng Anh

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

    # === SCIENCE ONTOLOGY KEYWORDS ===
    # Single source of truth cho cả T2 (content quality gate) lẫn T3
    # (extractive_summary, boost câu có cấu trúc nhân quả).
    #
    # Cấu trúc từ điển chia theo nhóm Ontology để dễ mở rộng theo từng lĩnh
    # vực khoa học. Nhóm "Cause-Effect markers" KHÔNG boost theo chủ đề mà
    # boost theo cấu trúc câu logic — đây là nguyên liệu trực tiếp cho Rule
    # Object (điều kiện kích hoạt / đầu ra / tác động).
    #
    # LƯU Ý MIGRATION: Nếu đổi tên field "matched_keywords" trong output
    # MongoDB, cần script riêng migrate collection permanent.* — không tự
    # động đổi ngầm trong code này.
    SCIENCE_ONTOLOGY_KEYWORDS = [
        # --- Energy / Matter exchange ---
        "energy transfer", "metabolic pathway", "thermodynamic", "entropy",
        "catalyst", "chemical gradient", "exothermic", "endothermic",
        "activation energy", "redox reaction", "oxidation", "reduction",
        "potential energy", "kinetic energy", "conservation of energy",
        "heat exchange", "thermal equilibrium", "phase transition",

        # --- Adaptation / Evolution / Mutation ---
        "natural selection", "mutation rate", "adaptive trait",
        "fitness landscape", "speciation", "convergent evolution",
        "selective pressure", "genetic drift", "evolutionary pressure",
        "phenotypic plasticity", "horizontal gene transfer",
        "punctuated equilibrium", "arms race", "coevolution",
        "molecular clock", "phylogenetic", "common ancestor",

        # --- Reproduction / Core Biology ---
        "reproductive strategy", "homeostasis", "symbiotic relationship",
        "metabolism", "cellular process", "mitosis", "meiosis",
        "gene expression", "protein synthesis", "enzyme activity",
        "membrane transport", "osmosis", "diffusion", "active transport",
        "immune response", "allele frequency", "phenotype", "genotype",
        "epigenetic", "dna replication", "transcription factor",

        # --- Cooperation / Conflict (Game Theory) ---
        "zero-sum", "nash equilibrium", "cooperative strategy",
        "resource competition", "tragedy of the commons", "payoff matrix",
        "prisoner's dilemma", "tit-for-tat", "evolutionary stable strategy",
        "arms race dynamics", "mutualism", "parasitism", "commensalism",
        "altruism", "kin selection", "group selection", "defection",

        # --- Society / Network Theory ---
        "network effect", "social hierarchy", "emergent behavior",
        "collective intelligence", "feedback loop", "social network",
        "information cascade", "tipping point", "phase transition",
        "critical mass", "self-organization", "decentralization",
        "stigmergy", "swarm intelligence", "distributed cognition",

        # --- Physics / Astronomy / Environment ---
        "gravitational force", "orbital mechanics", "electromagnetic",
        "quantum state", "wave function", "nuclear fusion", "stellar evolution",
        "habitable zone", "atmospheric composition", "magnetic field",
        "plate tectonics", "geological time", "extinction event",
        "carbon cycle", "nitrogen cycle", "water cycle", "nutrient cycle",
        "solar radiation", "cosmic radiation", "tidal force",

        # --- Information / Intelligence / Cognition ---
        "information processing", "signal transduction", "neural pathway",
        "cognitive load", "pattern recognition", "decision making",
        "memory consolidation", "learning rate", "synaptic plasticity",
        "computational complexity", "algorithmic", "optimization",

        # --- Cause-Effect structural markers ---
        # Nhóm này boost theo CẤU TRÚC CÂU LOGIC, không phải chủ đề.
        # Được dùng trong extractive_summary để ưu tiên câu nhân quả —
        # đây là nguyên liệu cho Rule Object: điều kiện → biến đổi → kết quả.
        "results in", "leads to", "due to", "caused by",
        "as a consequence", "if then", "depends on", "correlates with",
        "threshold", "trigger condition", "sufficient condition",
        "necessary condition", "enables", "prevents", "inhibits",
        "promotes", "accelerates", "decelerates", "modulates",
        "regulates", "constrains", "amplifies", "attenuates",
        "because", "therefore", "thus", "hence",
    ]

    # Alias tương thích ngược: các module chưa migrate vẫn import
    # DRAMA_KEYWORDS sẽ nhận đúng SCIENCE_ONTOLOGY_KEYWORDS thay vì list cũ.
    # Xóa alias này sau khi toàn bộ codebase đã chuyển sang tên mới.
    DRAMA_KEYWORDS = property(lambda self: self.SCIENCE_ONTOLOGY_KEYWORDS)

    # Alias tương thích ngược cho MIN_DRAMA_KEYWORDS
    MIN_DRAMA_KEYWORDS = property(lambda self: self.MIN_ONTOLOGY_KEYWORDS)


settings = Settings()

for d in [settings.DATA_DIR, settings.RAW_DIR, settings.QUEUE_DIR, settings.KEYWORD_STATE_DIR]:
    os.makedirs(d, exist_ok=True)


def validate_startup_config() -> None:
    """Config & Database Guard — kiểm tra TOÀN BỘ điều kiện tối thiểu để
    pipeline chạy được TRƯỚC KHI làm bất cứ việc gì tốn thời gian/quota
    (search, scrape, gọi LLM...). Nếu thiếu 1 điều kiện bắt buộc ->
    log lỗi RÕ RÀNG và `sys.exit(1)` ngay (chống "chết lén" giữa chừng).

    Không raise exception — cố tình dùng sys.exit(1) để dừng tiến trình
    dứt khoát, kể cả khi được gọi từ trong try/except ở nơi khác.
    """
    is_valid = True

    # 1. MONGODB_URI không được rỗng
    if not settings.MONGODB_URI:
        logger.error("❌ [CONFIG] MONGODB_URI đang rỗng — chưa set biến môi trường MONGODB_URI.")
        is_valid = False

    # 2. KEYWORDS_FILE phải tồn tại trên disk
    if not os.path.isfile(settings.KEYWORDS_FILE):
        logger.error(f"❌ [CONFIG] KEYWORDS_FILE không tồn tại: '{settings.KEYWORDS_FILE}'")
        is_valid = False

    # 3. ENGINES_FILE phải tồn tại trên disk
    if not os.path.isfile(settings.ENGINES_FILE):
        logger.error(f"❌ [CONFIG] ENGINES_FILE không tồn tại: '{settings.ENGINES_FILE}'")
        is_valid = False

    # 4. Thư mục output — tự tạo nếu chưa có, KHÔNG báo lỗi cho trường hợp này
    for output_dir in [settings.RAW_DIR, settings.KEYWORD_STATE_DIR]:
        try:
            os.makedirs(output_dir, exist_ok=True)
        except Exception as e:
            logger.error(f"❌ [CONFIG] Không thể tạo thư mục output '{output_dir}': {e}")
            is_valid = False

    if not is_valid:
        logger.error("🛑 [CONFIG] Startup config validation THẤT BẠI — dừng tiến trình.")
        sys.exit(1)

    logger.info("✅ [CONFIG] Startup config validation OK — đủ điều kiện chạy pipeline.")
