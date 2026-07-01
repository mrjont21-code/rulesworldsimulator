"""
T0: SEARCH ENGINE - Pattern Tinnhanh
- Xoay vòng 35 từ khóa
- Mỗi từ khóa 1 JSON state riêng
- Mỗi lần gọi 20 links
- Timer 25 phút
"""
import os
import json
import time
import logging
import random
from datetime import datetime, timezone
from urllib.parse import quote_plus, urlparse

import httpx
from bs4 import BeautifulSoup

from config import settings

logger = logging.getLogger(__name__)


class T0Search:
    def __init__(self):
        self.session = httpx.Client(
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
            },
            timeout=20.0,
            follow_redirects=True
        )
        
        # Load keywords
        self.keywords = self._load_keywords()
        
        # Load search engines config
        self.engines_config = self._load_engines_config()
        
        # Load blackbook
        self.blackbook = self._load_blackbook()
        
        # Timer tracking
        self.session_start = None
        self.session_end = None

    def _load_keywords(self) -> list[str]:
        """Load 35 từ khóa từ JSON"""
        path = settings.KEYWORDS_FILE
        if not os.path.exists(path):
            logger.error(f"Không tìm thấy {path}")
            return []
        
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        keywords = data.get("keywords", [])
        logger.info(f"📦 Đã load {len(keywords)} từ khóa")
        return keywords

    def _load_engines_config(self) -> dict:
        """Load config search engines"""
        path = settings.ENGINES_FILE
        if not os.path.exists(path):
            return {"engines": [], "banned_domains": [], "priority_sources": []}
        
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def _load_blackbook(self) -> dict:
        """Load blackbook - track domain failures"""
        path = settings.BLACKBOOK_FILE
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}

    def _save_blackbook(self):
        """Save blackbook"""
        with open(settings.BLACKBOOK_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.blackbook, f, indent=2, ensure_ascii=False)

    def get_keyword_state(self, keyword: str) -> dict:
        """
        Lấy state của 1 từ khóa từ JSON riêng
        File: keyword_states/{normalized_keyword}.json
        """
        normalized = self._normalize_keyword(keyword)
        state_path = os.path.join(settings.KEYWORD_STATE_DIR, f"{normalized}.json")
        
        default_state = {
            "keyword": keyword,
            "normalized": normalized,
            "total_links_found": 0,
            "links_scraped": 0,
            "links_failed": 0,
            "scraped_urls": [],  # URLs đã xử lý
            "last_run": None,
            "run_count": 0,
            "is_exhausted": False  # Đánh dấu khi không còn link mới
        }
        
        if os.path.exists(state_path):
            try:
                with open(state_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return default_state
        
        return default_state

    def save_keyword_state(self, state: dict):
        """Lưu state của từ khóa"""
        normalized = state["normalized"]
        state_path = os.path.join(settings.KEYWORD_STATE_DIR, f"{normalized}.json")
        
        state["last_run"] = datetime.now(timezone.utc).isoformat()
        
        with open(state_path, 'w', encoding='utf-8') as f:
            json.dump(state, f, indent=2, ensure_ascii=False)

    def _normalize_keyword(self, kw: str) -> str:
        """Chuẩn hóa từ khóa làm filename"""
        import re
        kw = kw.lower()
        kw = re.sub(r'[^a-z0-9\s]', '', kw)
        kw = re.sub(r'\s+', '_', kw.strip())
        return kw[:50]  # Giới hạn độ dài

    def _is_time_remaining(self) -> bool:
        """Check còn thời gian trong phiên 25 phút không"""
        if self.session_start is None:
            return True
        
        elapsed = time.time() - self.session_start
        max_seconds = settings.WORK_MINUTES * 60
        
        # Để lại 30 giây buffer
        return elapsed < (max_seconds - 30)

    def _get_next_keyword(self) -> tuple[str, dict] | None:
        """
        Lấy từ khóa tiếp theo theo thứ tự xoay vòng
        Ưu tiên: chưa exhaustive -> đang có link mới
        """
        # Sắp xếp theo: chưa exhausted trước, rồi theo last_run cũ nhất
        keyword_states = []
        
        for kw in self.keywords:
            state = self.get_keyword_state(kw)
            keyword_states.append((kw, state))
        
        # Sort: is_exhausted=False trước, rồi last_run cũ nhất (null = chưa chạy)
        def sort_key(item):
            kw, state = item
            exhausted = state.get("is_exhausted", False)
            last_run = state.get("last_run")
            # 0 = not exhausted, 1 = exhausted
            priority = 0 if not exhausted else 1
            # None = chưa chạy, xếp trước
            run_time = last_run or "0000"
            return (priority, run_time)
        
        keyword_states.sort(key=sort_key)
        
        # Tìm keyword chưa exhausted
        for kw, state in keyword_states:
            if not state.get("is_exhausted", False):
                return (kw, state)
        
        # Nếu tất cả exhausted, reset tất cả và bắt đầu lại
        logger.warning("⚠️  Tất cả từ khóa đã exhausted, reset tất cả")
        for kw, state in keyword_states:
            state["is_exhausted"] = False
            self.save_keyword_state(state)
        
        # Trả về keyword đầu tiên
        return (keyword_states[0][0], keyword_states[0][1])

    def search_startpage(self, keyword: str) -> list[dict]:
        """Search trên Startpage (POST method)"""
        links = []
        
        try:
            encoded_query = quote_plus(keyword)
            resp = self.session.post(
                "https://www.startpage.com/sp/search",
                data={"query": keyword, "cat": "web"},
                timeout=20
            )
            
            soup = BeautifulSoup(resp.text, "lxml")
            
            for a in soup.find_all("a", class_="w-gl__result-url"):
                href = a.get("href", "")
                if href.startswith("http"):
                    links.append({
                        "url": href,
                        "title": a.get_text(strip=True)[:100],
                        "engine": "startpage"
                    })
                    
        except Exception as e:
            logger.warning(f"Startpage failed: {e}")
        
        return links

    def search_brave(self, keyword: str) -> list[dict]:
        """Search trên Brave Search"""
        links = []
        
        try:
            encoded_query = quote_plus(keyword)
            resp = self.session.get(
                f"https://search.brave.com/search?q={encoded_query}",
                timeout=20
            )
            
            soup = BeautifulSoup(resp.text, "lxml")
            
            # Brave dùng div.snippet chứa link
            for div in soup.find_all("div", class_="snippet"):
                a = div.find("a")
                if a and a.get("href", "").startswith("http"):
                    href = a["href"]
                    if "brave.com" not in href:
                        links.append({
                            "url": href,
                            "title": a.get_text(strip=True)[:100],
                            "engine": "brave"
                        })
                        
        except Exception as e:
            logger.warning(f"Brave failed: {e}")
        
        return links

    def search_duckduckgo(self, keyword: str) -> list[dict]:
        """Search trên DuckDuckGo HTML version"""
        links = []
        
        try:
            encoded_query = quote_plus(keyword)
            resp = self.session.get(
                f"https://html.duckduckgo.com/html/?q={encoded_query}",
                timeout=20
            )
            
            soup = BeautifulSoup(resp.text, "lxml")
            
            for a in soup.find_all("a", class_="result__a"):
                href = a.get("href", "")
                if href.startswith("http") and "duckduckgo.com" not in href:
                    links.append({
                        "url": href,
                        "title": a.get_text(strip=True)[:100],
                        "engine": "duckduckgo"
                    })
                    
        except Exception as e:
            logger.warning(f"DuckDuckGo failed: {e}")
        
        return links

    def search_google(self, keyword: str) -> list[dict]:
        """Search trên Google (có thể bị block)"""
        links = []
        
        try:
            encoded_query = quote_plus(keyword)
            resp = self.session.get(
                f"https://www.google.com/search?q={encoded_query}&num=20",
                timeout=20
            )
            
            soup = BeautifulSoup(resp.text, "lxml")
            
            for div in soup.find_all("div", class_="g"):
                a = div.find("a")
                if a and a.get("href", "").startswith("http"):
                    href = a["href"]
                    if "google.com" not in href and not href.startswith("/"):
                        links.append({
                            "url": href,
                            "title": a.get_text(strip=True)[:100],
                            "engine": "google"
                        })
                        
        except Exception as e:
            logger.warning(f"Google failed: {e}")
        
        return links

    def search_cascade(self, keyword: str) -> list[dict]:
        """
        Search cascade qua nhiều engines
        Dừng khi đủ 20 links
        """
        all_links = []
        seen_urls = set()
        banned_domains = self.engines_config.get("banned_domains", [])
        priority_sources = self.engines_config.get("priority_sources", [])
        
        # Danh sách search functions theo priority
        search_functions = [
            ("startpage", self.search_startpage),
            ("brave", self.search_brave),
            ("duckduckgo", self.search_duckduckgo),
            ("google", self.search_google),
        ]
        
        for engine_name, search_fn in search_functions:
            if len(all_links) >= settings.LINKS_PER_SEARCH:
                break
            
            logger.info(f"   🔍 Trying {engine_name}...")
            engine_links = search_fn(keyword)
            
            for link in engine_links:
                url = link["url"]
                domain = urlparse(url).netloc.lower()
                
                # Skip banned domains
                if any(b in domain for b in banned_domains):
                    continue
                
                # Skip banned in blackbook
                if self.blackbook.get(domain, {}).get("status") == "banned":
                    continue
                
                # Skip duplicate URLs
                if url in seen_urls:
                    continue
                
                seen_urls.add(url)
                
                # Add priority flag
                link["is_priority_source"] = any(p in domain for p in priority_sources)
                link["domain"] = domain
                link["keyword"] = keyword
                link["searched_at"] = datetime.now(timezone.utc).isoformat()
                
                all_links.append(link)
            
            logger.info(f"   ✅ {engine_name}: +{len(engine_links)} links (total: {len(all_links)})")
            
            # Delay giữa các engines
            if len(all_links) < settings.LINKS_PER_SEARCH:
                time.sleep(1)
        
        return all_links[:settings.LINKS_PER_SEARCH]

    def filter_already_scraped(self, links: list[dict], state: dict) -> list[dict]:
        """Lọc bỏ links đã từng xử lý"""
        scraped_urls = set(state.get("scraped_urls", []))
        
        new_links = []
        for link in links:
            if link["url"] not in scraped_urls:
                new_links.append(link)
        
        return new_links

    def run_session(self) -> list[dict]:
        """
        Chạy 1 phiên 25 phút
        Xoay vòng qua keywords, mỗi lần 20 links
        """
        self.session_start = time.time()
        self.session_end = self.session_start + (settings.WORK_MINUTES * 60)
        
        logger.info("=" * 80)
        logger.info(f"🔍 T0: SEARCH SESSION (25 phút)")
        logger.info(f"   Start: {datetime.fromtimestamp(self.session_start).strftime('%H:%M:%S')}")
        logger.info(f"   End:   {datetime.fromtimestamp(self.session_end).strftime('%H:%M:%S')}")
        logger.info("=" * 80)
        
        all_new_links = []
        keywords_used = []
        
        while self._is_time_remaining():
            # Lấy keyword tiếp theo
            result = self._get_next_keyword()
            if result is None:
                logger.info("🏁 Không còn từ khóa nào để xử lý")
                break
            
            keyword, state = result
            keywords_used.append(keyword)
            
            logger.info(f"\n{'='*60}")
            logger.info(f"🔑 Keyword: {keyword}")
            logger.info(f"   Đã tìm: {state.get('total_links_found', 0)} links")
            logger.info(f"   Đã cào: {state.get('links_scraped', 0)} links")
            logger.info(f"{'='*60}")
            
            # Search
            links = self.search_cascade(keyword)
            state["total_links_found"] = state.get("total_links_found", 0) + len(links)
            
            # Filter đã xử lý
            new_links = self.filter_already_scraped(links, state)
            
            logger.info(f"   📊 Tìm thấy: {len(links)}, Mới: {len(new_links)}")
            
            if new_links:
                all_new_links.extend(new_links)
                
                # Đánh dấu URLs đã tìm thấy (chưa phải đã scrape)
                for link in new_links:
                    if link["url"] not in state.get("found_urls", []):
                        state.setdefault("found_urls", []).append(link["url"])
            else:
                # Không có link mới -> có thể exhausted
                if state.get("total_links_found", 0) > 50:  # Nếu đã tìm >50 links mà hết mới
                    logger.warning(f"   ⚠️ Keyword có vẻ đã exhausted")
                    # Không đánh dấu exhausted ngay, chờ vài lần nữa
            
            state["run_count"] = state.get("run_count", 0) + 1
            self.save_keyword_state(state)
            
            # Delay giữa các keywords
            time.sleep(settings.SEARCH_DELAY_SECONDS)
        
        elapsed = time.time() - self.session_start
        logger.info(f"\n{'='*80}")
        logger.info(f"📊 T0 SESSION SUMMARY")
        logger.info(f"   Thời gian: {elapsed/60:.1f} phút")
        logger.info(f"   Keywords đã dùng: {len(keywords_used)}")
        logger.info(f"   Links mới tìm được: {len(all_new_links)}")
        logger.info(f"{'='*80}")
        
        # Save blackbook
        self._save_blackbook()
        
        return all_new_links


def run_t0() -> list[dict]:
    """Entry point cho T0"""
    searcher = T0Search()
    return searcher.run_session()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - [T0] %(message)s',
        datefmt='%H:%M:%S'
    )
    
    links = run_t0()
    print(f"\n✅ Tìm được {len(links)} links mới")
