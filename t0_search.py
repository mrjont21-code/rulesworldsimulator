"""
T0: SEARCH - Anti-Ban Mode (Playwright edition)
- Dùng Chromium thật (Playwright) thay vì curl_cffi/httpx giả header
- --disable-blink-features=AutomationControlled để xoá navigator.webdriver
- Retry per engine với backoff ngắn (giống tinnhanh/t1_search.py)
- Chỉ xử lý 1 keyword mỗi lần gọi
- Delay 8-20s giữa các engines (stealth.human_delay)
"""
import os
import json
import logging
import random
import urllib.parse
from datetime import datetime, timezone

from playwright.sync_api import sync_playwright

from config import settings
from stealth import get_random_ua, human_delay
from domain_ban import is_banned

logger = logging.getLogger(__name__)

# Trials per engine trước khi bỏ cuộc. IP của GitHub Actions bị rate-limit/
# CAPTCHA thường xuyên hơn IP dân dụng -> 1 lần retry với backoff ngắn cứu
# được một phần đáng kể các lần bị chặn tạm thời.
MAX_ENGINE_ATTEMPTS = 2
RETRY_DELAY_RANGE_MS = (1500, 3500)


class T0Search:
    def __init__(self):
        self.engines_config = self._load_engines_config()
        self.blackbook = self._load_blackbook()
        self.session_start = None

    def _load_engines_config(self) -> dict:
        path = settings.ENGINES_FILE
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {"engines": [], "banned_domains": [], "priority_sources": []}

    def _load_blackbook(self) -> dict:
        path = settings.BLACKBOOK_FILE
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}

    def _save_blackbook(self):
        with open(settings.BLACKBOOK_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.blackbook, f, indent=2, ensure_ascii=False)

    def get_keyword_state(self, keyword: str) -> dict:
        normalized = self._normalize_keyword(keyword)
        state_path = os.path.join(settings.KEYWORD_STATE_DIR, f"{normalized}.json")

        default_state = {
            "keyword": keyword,
            "normalized": normalized,
            "total_links_found": 0,
            "links_scraped": 0,
            "scraped_urls": [],
            "found_urls": [],
            "last_run": None,
            "run_count": 0,
            "is_exhausted": False
        }

        if os.path.exists(state_path):
            try:
                with open(state_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                return default_state
        return default_state

    def save_keyword_state(self, state: dict):
        normalized = state["normalized"]
        state_path = os.path.join(settings.KEYWORD_STATE_DIR, f"{normalized}.json")
        state["last_run"] = datetime.now(timezone.utc).isoformat()
        with open(state_path, 'w', encoding='utf-8') as f:
            json.dump(state, f, indent=2, ensure_ascii=False)

    def _normalize_keyword(self, kw: str) -> str:
        import re
        kw = kw.lower()
        kw = re.sub(r'[^a-z0-9\s]', '', kw)
        kw = re.sub(r'\s+', '_', kw.strip())
        return kw[:50]

    def _is_time_remaining(self) -> bool:
        if self.session_start is None:
            return True
        elapsed = (datetime.now(timezone.utc) - datetime.fromtimestamp(self.session_start, timezone.utc)).total_seconds()
        return elapsed < (settings.WORK_MINUTES * 60 - 30)

    def _get_next_keyword(self, keywords: list[str]) -> tuple[str, dict] | None:
        """Lấy keyword tiếp theo chưa exhausted"""
        keyword_states = [(kw, self.get_keyword_state(kw)) for kw in keywords]

        def sort_key(item):
            kw, state = item
            exhausted = state.get("is_exhausted", False)
            last_run = state.get("last_run") or "0000"
            return (0 if not exhausted else 1, last_run)

        keyword_states.sort(key=sort_key)

        for kw, state in keyword_states:
            if not state.get("is_exhausted", False):
                return (kw, state)

        logger.warning("⚠️  Tất cả keywords exhausted, reset tất cả")
        for kw, state in keyword_states:
            state["is_exhausted"] = False
            self.save_keyword_state(state)
        return (keyword_states[0][0], keyword_states[0][1])

    def _unwrap_redirect(self, href: str) -> str:
        """Google/Startpage đôi khi bọc link thật trong /url?q=<real>&..."""
        if href.startswith("/url?") or "google.com/url?" in href:
            parsed = urllib.parse.urlparse(href)
            qs = urllib.parse.parse_qs(parsed.query)
            if "q" in qs and qs["q"]:
                href = qs["q"][0]
        # Bỏ fragment (#anchor) để tránh trùng lặp cùng trang với anchor khác
        # Ví dụ: Wikipedia trả về 4 URL cùng /wiki/Carbon-based_life chỉ khác #section
        parsed = urllib.parse.urlparse(href)
        return urllib.parse.urlunparse(parsed._replace(fragment=""))

    def _build_search_url(self, engine: dict, keyword: str) -> str:
        encoded = urllib.parse.quote_plus(keyword)
        return engine["url_template"].format(query=encoded)

    def _fetch_links_from_engine(self, page, engine: dict, keyword: str) -> list[dict]:
        """
        Mở trang search bằng Chromium thật (Playwright), đọc DOM đã render.
        Retry MAX_ENGINE_ATTEMPTS lần với backoff ngắn nếu bị chặn/timeout.
        """
        engine_name = engine.get("name", "Engine")
        link_selector = engine.get("link_selector", "a[href]")
        exclude_domain = engine.get("exclude_domain_in_href", "")
        timeout_ms = 20000

        # POST (Startpage) không đi qua page.goto trực tiếp được -> dùng GET
        # tương đương của Startpage khi cần (fallback query string).
        if engine.get("method", "GET").upper() == "POST":
            search_url = engine["url_template"] + "?query=" + urllib.parse.quote_plus(keyword) + "&cat=web"
        else:
            search_url = self._build_search_url(engine, keyword)

        last_error = None
        for attempt in range(1, MAX_ENGINE_ATTEMPTS + 1):
            try:
                page.goto(search_url, wait_until="domcontentloaded", timeout=timeout_ms)
                page.wait_for_timeout(random.randint(1200, 2500))  # để JS render xong

                found, seen = [], set()
                for a in page.locator(link_selector).all():
                    href = a.get_attribute("href") or ""
                    href = self._unwrap_redirect(href)
                    title = (a.inner_text() or "").strip()

                    if not href.startswith("http"):
                        continue
                    if exclude_domain and exclude_domain in href.lower():
                        continue
                    if href in seen:
                        continue

                    seen.add(href)
                    found.append({"url": href, "title": title[:100], "engine": engine_name.lower()})

                return found
            except Exception as e:
                last_error = e
                logger.warning(f"   {engine_name} attempt {attempt}/{MAX_ENGINE_ATTEMPTS} failed: {e}")
                page.wait_for_timeout(random.randint(*RETRY_DELAY_RANGE_MS))

        logger.warning(f"   {engine_name} gave up after {MAX_ENGINE_ATTEMPTS} tries ({last_error})")
        return []

    def search_single_keyword(self, keyword: str) -> list[dict]:
        """
        Search 1 keyword qua cascade engines bằng Chromium thật.
        Dừng khi đủ LINKS_PER_SEARCH links. Delay 8-20s giữa các engines.
        """
        all_links = []
        seen_urls = set()
        banned_domains = self.engines_config.get("banned_domains", [])
        priority_sources = self.engines_config.get("priority_sources", [])
        engines = sorted(self.engines_config.get("engines", []), key=lambda x: x.get("priority", 99))

        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-blink-features=AutomationControlled",  # xoá navigator.webdriver
                    "--disable-dev-shm-usage",
                ],
            )
            context = browser.new_context(
                user_agent=get_random_ua(),
                viewport={"width": 1366, "height": 768},
                locale="en-US",
            )
            page = context.new_page()

            for engine in engines:
                if len(all_links) >= settings.LINKS_PER_SEARCH:
                    break

                logger.info(f"   🔍 Thử {engine.get('name')}...")
                engine_links = self._fetch_links_from_engine(page, engine, keyword)

                new_count = 0
                for link in engine_links:
                    url = link["url"]
                    domain = urllib.parse.urlparse(url).netloc.lower()

                    if any(b in domain for b in banned_domains):
                        continue
                    if is_banned(self.blackbook, domain):
                        continue
                    if url in seen_urls:
                        continue

                    seen_urls.add(url)
                    link["is_priority_source"] = any(p in domain for p in priority_sources)
                    link["domain"] = domain
                    link["keyword"] = keyword
                    link["searched_at"] = datetime.now(timezone.utc).isoformat()
                    all_links.append(link)
                    new_count += 1

                logger.info(f"   ✅ {engine.get('name')}: +{new_count} links (tổng: {len(all_links)})")

                if len(all_links) < settings.LINKS_PER_SEARCH:
                    human_delay(min_sec=settings.MIN_REQUEST_DELAY, max_sec=settings.MAX_REQUEST_DELAY)

            page.close()
            browser.close()

        return all_links[:settings.LINKS_PER_SEARCH]

    def filter_new_links(self, links: list[dict], state: dict) -> list[dict]:
        seen = set(state.get("found_urls", []))
        return [l for l in links if l["url"] not in seen]


# Module-level singleton: giữ session_start qua nhiều lần gọi run_t0_single_keyword()
# Mỗi lần gọi tạo T0Search() mới (instance attribute luôn None) nên phải lưu ở đây.
_SESSION_START: float | None = None


def run_t0_single_keyword(keywords: list[str]) -> tuple[str, list[dict], dict] | None:
    """
    T0 Entry Point: Chỉ search 1 keyword
    Trả về: (keyword, new_links, state) hoặc None nếu hết giờ/hết keyword
    """
    global _SESSION_START

    searcher = T0Search()

    # Khởi tạo session timer 1 lần duy nhất cho toàn bộ vòng lặp trong main.py
    if _SESSION_START is None:
        _SESSION_START = datetime.now(timezone.utc).timestamp()
        logger.info(f"   🕐 Session timer bắt đầu: {datetime.fromtimestamp(_SESSION_START).strftime('%H:%M:%S')}")

    searcher.session_start = _SESSION_START

    if not searcher._is_time_remaining():
        logger.info("   ⏰ Session timer hết giờ, dừng T0.")
        _SESSION_START = None  # Reset cho session Pomodoro tiếp theo
        return None

    result = searcher._get_next_keyword(keywords)
    if result is None:
        return None

    keyword, state = result

    logger.info(f"\n{'='*60}")
    logger.info(f"🔑 KEYWORD: {keyword}")
    logger.info(f"   Lịch sử: Tìm {state.get('total_links_found',0)} / Cào {state.get('links_scraped',0)}")
    logger.info(f"{'='*60}")

    links = searcher.search_single_keyword(keyword)
    state["total_links_found"] = state.get("total_links_found", 0) + len(links)

    new_links = searcher.filter_new_links(links, state)

    for link in new_links:
        if link["url"] not in state.get("found_urls", []):
            state.setdefault("found_urls", []).append(link["url"])

    # Threshold 10: thực tế mỗi lần search trả về ~20 links, nếu tìm được >= 10
    # mà không có URL mới thì keyword đã khai thác đủ → đánh dấu exhausted để
    # chuyển sang keyword khác, tránh lãng phí delay 30-60s mỗi vòng lặp.
    if not new_links and state.get("total_links_found", 0) >= 10:
        state["is_exhausted"] = True
        logger.warning("   ⚠️ Keyword EXHAUSTED (đã khai thác đủ)")

    state["run_count"] = state.get("run_count", 0) + 1
    searcher.save_keyword_state(state)
    searcher._save_blackbook()

    logger.info(f"   📊 Tìm: {len(links)}, Mới: {len(new_links)}")

    if not new_links:
        return None

    return (keyword, new_links, state)
