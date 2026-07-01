"""
T0: SEARCH ENGINE - Startpage
Sinh từ khóa bằng Python thuần (KHÔNG dùng LLM)
Search trên Startpage, trả về 20 links
"""
import requests
import time
import json
import re
import hashlib
import logging
import random
from datetime import datetime, timezone
from urllib.parse import quote_plus
from config import settings

logger = logging.getLogger(__name__)


class T0Search:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        })
        
        # Handle MongoDB connection
        self.mongo = None
        self.db = None
        
        if settings.MONGODB_URI:
            try:
                from pymongo import MongoClient
                self.mongo = MongoClient(settings.MONGODB_URI, serverSelectionTimeoutMS=5000)
                self.mongo.admin.command('ping')
                self.db = self.mongo[settings.MONGODB_DB_NAME]
                logger.info("✅ MongoDB connected successfully")
            except Exception as e:
                logger.warning(f"⚠️  MongoDB connection failed: {e}")
                self.mongo = None
                self.db = None

    def get_used_keywords(self) -> list[str]:
        """Lấy danh sách từ khóa đã dùng từ MongoDB"""
        if self.db is None:
            return []
        
        try:
            keywords = list(self.db[settings.MONGODB_COLLECTION_KEYWORDS].find())
            return [kw["keyword"] for kw in keywords]
        except Exception as e:
            logger.warning(f"Không thể đọc keywords từ MongoDB: {e}")
            return []

    def generate_keywords_python(self, count: int = 5) -> list[str]:
        """
        Sinh từ khóa bằng Python thuần - TỪ KHÓA THỰC TẾ
        KHÔNG dùng LLM
        """
        # Danh sách từ khóa THỰC TẾ (đã kiểm chứng có kết quả)
        REAL_KEYWORDS = [
            # Từ khóa rộng, phổ biến
            "silicon based life",
            "alternative biochemistry",
            "extraterrestrial life",
            "hypothetical biochemistry",
            "astrobiology",
            "xenobiology",
            "carbon based life",
            "extremophiles",
            
            # Từ khóa cụ thể hơn nhưng vẫn thực tế
            "silicon biology",
            "ammonia based life",
            "methane based life",
            "non carbon life",
            "alien biochemistry",
            "exotic biology",
            "alternative life forms",
            "speculative evolution",
            "theoretical biology",
            "astrobiology research",
            "extremophile organisms",
            "space biology",
            
            # Từ khóa học thuật
            "alternative biochemistry wikipedia",
            "silicon life scientific analysis",
            "extraterrestrial biochemistry research",
            "hypothetical life forms",
            "non terrestrial biology",
            "exotic life chemistry",
            "theoretical astrobiology",
            "xenobiology studies",
            
            # Từ khóa cộng đồng
            "worldbuilding alien biology",
            "speculative biology forum",
            "alien life discussion",
            "exobiology community",
            "theoretical alien life",
        ]
        
        # Lấy từ khóa đã dùng
        used_keywords = self.get_used_keywords()
        used_set = set(used_keywords)
        
        # Lọc ra từ khóa chưa dùng
        available_keywords = [kw for kw in REAL_KEYWORDS if kw not in used_set]
        
        # Nếu hết từ khóa chưa dùng, reset (cho phép dùng lại)
        if len(available_keywords) < count:
            logger.warning("⚠️  Hết từ khóa mới, cho phép dùng lại từ khóa cũ")
            available_keywords = REAL_KEYWORDS
        
        # Random chọn từ khóa
        selected = random.sample(available_keywords, min(count, len(available_keywords)))
        
        return selected

    def search_startpage(self, keyword: str) -> list[dict]:
        """Search trên Startpage, trả về danh sách links"""
        data = {"query": keyword, "cat": "web"}
        
        try:
            resp = self.session.post(
                settings.SEARCH_URL,
                data=data,
                timeout=20
            )
            resp.raise_for_status()
            
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(resp.text, "lxml")
            
            links = []
            
            # Thử tìm với class cụ thể
            for a in soup.find_all("a", class_="w-gl__result-url"):
                href = a.get("href", "")
                if href.startswith("http"):
                    links.append({
                        "url": href,
                        "title": a.get_text(strip=True),
                        "keyword": keyword,
                        "searched_at": datetime.now(timezone.utc).isoformat()
                    })
            
            # Fallback: tìm tất cả links
            if not links:
                for a in soup.find_all("a", href=True):
                    href = a["href"]
                    if href.startswith("http") and "startpage.com" not in href:
                        # Lọc bỏ links nội bộ của startpage
                        if not any(x in href for x in ["startpage.com", "ixquick.com"]):
                            links.append({
                                "url": href,
                                "title": a.get_text(strip=True)[:100],
                                "keyword": keyword,
                                "searched_at": datetime.now(timezone.utc).isoformat()
                            })
            
            return links[:settings.MAX_RESULTS_PER_SEARCH]
            
        except Exception as e:
            logger.error(f"Lỗi search '{keyword}': {e}")
            return []

    def save_keywords(self, keywords: list[str], run_id: str):
        """Lưu từ khóa đã dùng vào MongoDB"""
        if self.db is None:
            return
        
        try:
            for kw in keywords:
                self.db[settings.MONGODB_COLLECTION_KEYWORDS].insert_one({
                    "keyword": kw,
                    "normalized": self._normalize_keyword(kw),
                    "used_at": datetime.now(timezone.utc).isoformat(),
                    "run_id": run_id
                })
        except Exception as e:
            logger.warning(f"Không thể lưu keywords vào MongoDB: {e}")

    def _normalize_keyword(self, kw: str) -> str:
        """Chuẩn hóa từ khóa để so sánh"""
        kw = kw.lower()
        kw = re.sub(r'[^a-z0-9\s]', '', kw)
        words = sorted(kw.split())
        return ' '.join(words)

    def run(self, run_id: str) -> list[dict]:
        """
        Chạy T0: sinh từ khóa + search
        Trả về danh sách links (tối đa LINKS_PER_RUN)
        """
        logger.info("=" * 80)
        logger.info("🔍 T0: SEARCH ENGINE")
        logger.info("=" * 80)
        
        # Sinh từ khóa (Python thuần, KHÔNG LLM)
        keywords = self.generate_keywords_python(count=5)
        logger.info(f"✅ Sinh được {len(keywords)} từ khóa:")
        for i, kw in enumerate(keywords, 1):
            logger.info(f"   {i}. {kw}")
        
        # Lưu từ khóa
        self.save_keywords(keywords, run_id)
        
        # Search từng từ khóa
        all_links = []
        for keyword in keywords:
            logger.info(f"\n🔎 Searching: {keyword}")
            links = self.search_startpage(keyword)
            logger.info(f"   ✅ Tìm được {len(links)} links")
            all_links.extend(links)
            time.sleep(settings.SEARCH_DELAY_SECONDS)
            
            if len(all_links) >= settings.LINKS_PER_RUN:
                break
        
        # Giới hạn số links
        all_links = all_links[:settings.LINKS_PER_RUN]
        
        logger.info(f"\n📊 TỔNG: {len(all_links)} links")
        
        return all_links
