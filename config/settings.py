import os

# ============================================
# GEMINI API KEYS - 7 keys xoay vòng
# ============================================
GEMINI_KEYS = [
    os.getenv("GEMINI_KEY_1", ""),
    os.getenv("GEMINI_KEY_2", ""),
    os.getenv("GEMINI_KEY_3", ""),
    os.getenv("GEMINI_KEY_4", ""),
    os.getenv("GEMINI_KEY_5", ""),
    os.getenv("GEMINI_KEY_6", ""),
    os.getenv("GEMINI_KEY_7", ""),
]

GEMINI_MODEL = "gemini-2.0-flash"
GEMINI_MODEL_HEAVY = "gemini-2.0-pro-exp-02-05"

# ============================================
# MONGODB ATLAS
# ============================================
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb+srv://user:pass@cluster.mongodb.net/")
MONGODB_DB_NAME = "world_lore_db"
MONGODB_COLLECTION_RULES = "biology_rules"
MONGODB_COLLECTION_RAW = "raw_articles"

# ============================================
# SCRAPE SOURCES
# ============================================
ORIONS_ARM_API = "https://orionsarm.com/api.php"
ORIONS_ARM_CATEGORIES = [
    "Xenobiology",
    "Non-Carbon_Based_Life",
    "Silicon_Based_Life",
    "Exotic_Biology",
    "Biochemistry",
]

SPEC_EVO_API = "https://speculativeevolution.fandom.com/api.php"
SPEC_EVO_CATEGORIES = [
    "Species",
    "Ecosystems",
]

PROJECT_RHO_BASE = "http://www.projectrho.com/public_html/rocket/"
PROJECT_RHO_PAGES = [
    "aliens.html",
    "alienbiology.html",
    "exoticbiology.html",
    "nonhuman.html",
]

# ============================================
# SCRAPE SETTINGS
# ============================================
REQUEST_DELAY_SECONDS = 1.5
MAX_ARTICLES_PER_CATEGORY = 200
MAX_ARTICLES_TOTAL = 1500

# ============================================
# OUTPUT
# ============================================
RAW_OUTPUT_PATH = "data/raw_articles.json"
FINAL_OUTPUT_PATH = "data/biology_rules_final.json"
MIN_QUALITY_SCORE = 0.6
MAX_FINAL_RULES = 300
