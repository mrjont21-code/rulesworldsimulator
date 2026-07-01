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
    MIN_BIOLOGY_KEYWORDS = 2
    
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
    MONGODB_COLLECTION_RULES = "biology_rules"
    MONGODB_COLLECTION_RUNS = "run_logs"
    
    # === BIOLOGY KEYWORDS ===
    BIOLOGY_KEYWORDS = [
        "biochemistry", "carbon", "silicon", "ammonia", "methane", 
        "protein", "dna", "rna", "cell", "organism", "evolution",
        "metabolism", "enzyme", "amino acid", "lipid", "carbohydrate",
        "photosynthesis", "respiration", "reproduction", "genome",
        "extremophile", "astrobiology", "xenobiology", "exobiology",
        "alternative life", "hypothetical life", "alien biology",
        "non-carbon", "non-terrestrial", "speculative evolution",
        "hypercycles", "autocatalysis", "protocell", "origin of life",
        "prebiotic", "abiogenesis", "panspermia", "fermentation",
        "sulfur", "phosphorus", "nitrogen", "hydrogen", "oxygen",
        "solvent", "temperature", "pressure", "radiation"
    ]

settings = Settings()

for d in [settings.DATA_DIR, settings.RAW_DIR, settings.QUEUE_DIR, settings.KEYWORD_STATE_DIR]:
    os.makedirs(d, exist_ok=True)
