"""
T2: SCRAPE — Anti-Ban Mode / Foundational Knowledge Engine
===========================================================
- curl_cffi cho HTTP request ngụy trang (fallback httpx)
- Delay 8–20s mỗi request để tránh bị ban
- Playwright chỉ kích hoạt khi HTTP thất bại
- Content quality gate: lọc theo SCIENCE_ONTOLOGY_KEYWORDS thay vì
  từ khóa kịch tính cũ — đảm bảo chỉ nội dung có liên quan đến quy
  luật khoa học/nhân quả mới đi qua được T3.
"""
import os
import json
import time
import logging
from urllib.parse import urlparse
from bs4 import BeautifulSoup

from config import settings
from stealth import get_stealth_headers, human_delay
from skills import extract_spa_json_data
from domain_ban import record_failure, record_success

logger = logging.getLogger(__name__)

try:
    from curl_cffi import requests as cffi_requests
    HAS_CFFI = True
except ImportError:
    import httpx
    HAS_CFFI = False


class T2Scrape:
    def __init__(self):
        self.blackbook = self._load_blackbook()
        self._playwright = None
        self._browser = None
        self._context = None

    def _load_blackbook(self) -> dict:
        path = settings.BLACKBOOK_FILE
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def _save_blackbook(self):
        with open(settings.BLACKBOOK_FILE, "w", encoding="utf-8") as f:
            json.dump(self.blackbook, f, indent=2, ensure_ascii=False)

    def _create_session(self):
        """Tạo HTTP session mới với headers ngụy trang trình duyệt thật."""
        headers = get_stealth_headers()
        if HAS_CFFI:
            return cffi_requests.Session(impersonate="chrome120", headers=headers)
        else:
            return httpx.Client(headers=headers, timeout=15.0, follow_redirects=True)

    def _init_playwright(self):
        if self._context is not None:
            return
        try:
            from playwright.sync_api import sync_playwright
            self._playwright = sync_playwright().start()
            self._browser = self._playwright.chromium.launch(
                headless=True,
                args=["--disable-blink-features=AutomationControlled", "--no-sandbox"],
            )
            self._context = self._browser.new_context(
                user_agent=get_stealth_headers()["User-Agent"]
            )
        except Exception as e:
            logger.warning(f"Playwright init thất bại: {e}")
            self._context = None

    def _close_playwright(self):
        if self._context:
            self._context.close()
        if self._browser:
            self._browser.close()
        if self._playwright:
            self._playwright.stop()
        self._context = None

    def is_valid_content(self, text: str) -> bool:
        """Kiểm tra nội dung không phải trang chặn/captcha."""
        if not text or len(text) < 150:
            return False
        traps = [
            "enable javascript and cookies", "just a moment",
            "checking the site connection", "verify you are human",
            "access denied", "403 forbidden", "cloudflare", "captcha",
            "attention required", "unusual traffic", "are you a robot",
            "ddos protection by", "please wait while we verify",
        ]
        return not any(t in text.lower() for t in traps)

    def _scrape_http(self, url: str) -> tuple[str | None, str]:
        """Skill 1: HTTP với curl_cffi/httpx và HTML parsing đa tầng."""
        session = self._create_session()
        try:
            resp = session.get(url, timeout=15.0)
            html_text = resp.text

            # Sub-skill: SPA JSON (ưu tiên vì thường sạch hơn HTML soup)
            spa_text = extract_spa_json_data(html_text)
            if spa_text and self.is_valid_content(spa_text):
                return spa_text[:8000], "SPA_JSON"

            # Sub-skill: HTML parsing theo selector ưu tiên
            soup = BeautifulSoup(html_text, "lxml")
            for tag in soup.find_all(["script", "style", "nav", "footer", "header", "aside"]):
                tag.decompose()

            selectors = [
                "article", "main", ".content", "#content",
                ".post-content", ".article-body", ".entry-content",
                ".mw-parser-output", "[itemprop='articleBody']",
            ]

            content = None
            for sel in selectors:
                el = soup.select_one(sel)
                if el:
                    ps = el.find_all(["p", "li", "h2", "h3", "blockquote"])
                    if ps:
                        content = "\n".join(
                            [p.get_text(strip=True) for p in ps if len(p.get_text(strip=True)) > 20]
                        )
                    if content and len(content) > 200:
                        break

            if not content or len(content) < 200:
                if soup.body:
                    ps = soup.body.find_all("p")
                    content = "\n".join(
                        [p.get_text(strip=True) for p in ps if len(p.get_text(strip=True)) > 30]
                    )

            if content and self.is_valid_content(content):
                return content[:8000], "HTTP_SOUP"

            return None, None
        except Exception as e:
            logger.debug(f"HTTP thất bại: {e}")
            return None, None
        finally:
            session.close()

    def _scrape_playwright(self, url: str) -> str | None:
        """Skill 2: Playwright headless (chỉ kích hoạt khi HTTP thất bại).

        Dùng "domcontentloaded" thay vì "networkidle" để tránh timeout trên
        trang có analytics/video/ads liên tục ping — DOM sẵn sàng đọc text
        là đủ cho mục đích thu thập văn bản.
        """
        self._init_playwright()
        if not self._context:
            return None
        page = self._context.new_page()
        try:
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=15000)
            except Exception as e:
                logger.debug(f"Playwright goto timeout/error (thử đọc DOM hiện có): {e}")
            page.wait_for_timeout(2500)
            text = page.locator("body").inner_text()
            if self.is_valid_content(text):
                return text[:8000]
            return None
        except Exception as e:
            logger.debug(f"Playwright thất bại: {e}")
            return None
        finally:
            page.close()

    def _scrape_reddit(self, url: str) -> dict | None:
        """Scraper chuyên dụng cho Reddit JSON API."""
        session = self._create_session()
        try:
            json_url = url.rstrip("/") + ".json"
            resp = session.get(json_url, timeout=15.0)
            data = resp.json()
            post = data[0]["data"]["children"][0]["data"]
            title = post["title"]
            content = post.get("selftext", "")
            comments = []
            if len(data) > 1:
                for child in data[1]["data"]["children"][:10]:
                    if child["kind"] == "t1":
                        body = child["data"].get("body", "")
                        if body and len(body) > 50:
                            comments.append(body)
            full = f"{title}\n\n{content}\n\n--- COMMENTS ---\n" + "\n---\n".join(comments)
            return {
                "url": url,
                "title": title,
                "content": full,
                "content_length": len(full),
                "scraped_at": time.time(),
                "skill_used": "REDDIT_JSON",
            }
        except Exception:
            return None
        finally:
            session.close()

    # URL patterns chỉ trỏ tới media/video — không có text để thu thập,
    # tốn slot request + delay vô ích.
    SKIP_URL_PATTERNS = (
        "/video/", "/videos/", "/watch", "youtube.com", "vimeo.com",
        # Trang phụ trợ MediaWiki/Fandom (edit/login/history/special) không
        # chứa nội dung thực sự — bỏ qua để không lãng phí slot scraping.
        "action=edit", "action=history", "special:", "veaction=",
        "/user:", "/talk:", "printable=yes", "oldid=",
    )

    def _is_skip_url(self, url: str) -> bool:
        u = url.lower()
        return any(p in u for p in self.SKIP_URL_PATTERNS)

    def process_link(self, link: dict) -> dict | None:
        """Xử lý một link — HTTP trước, Playwright nếu HTTP thất bại."""
        url = link["url"]
        domain = link.get("domain", urlparse(url).netloc)
        scraper_type = link.get("scraper_type", "html_simple")

        if self._is_skip_url(url):
            logger.info("         ⏭️  URL media-only, bỏ qua")
            return None

        if domain not in self.blackbook:
            self.blackbook[domain] = {"failures": 0, "status": "active", "skill": "HTTP"}

        # Reddit dùng JSON API riêng
        if scraper_type == "reddit":
            result = self._scrape_reddit(url)
            if result:
                record_success(self.blackbook, domain)
                return result
            if record_failure(self.blackbook, domain):
                logger.warning(f"         🚫 Domain bị cách ly (7 ngày): {domain}")
            return None

        # Flow thông thường: HTTP → Playwright
        current_skill = self.blackbook[domain].get("skill", "HTTP")
        skill_chain = ["HTTP", "PLAYWRIGHT"]
        start_idx = skill_chain.index(current_skill) if current_skill in skill_chain else 0

        data, skill_used = None, None

        for skill in skill_chain[start_idx:]:
            if skill == "HTTP":
                data, spec = self._scrape_http(url)
                if data:
                    skill_used = spec
                    break
            elif skill == "PLAYWRIGHT":
                logger.info("         [PLAYWRIGHT] Khởi động headless browser...")
                data = self._scrape_playwright(url)
                if data:
                    skill_used = "PLAYWRIGHT"
                    break

        if data:
            self.blackbook[domain]["skill"] = skill_used if skill_used != "SPA_JSON" else "HTTP"
            record_success(self.blackbook, domain)
            title = link.get("title", "")
            if not title or len(title) < 10:
                title = data.split("\n")[0][:100]
            return {
                "url": url,
                "title": title,
                "content": data,
                "content_length": len(data),
                "scraped_at": time.time(),
                "skill_used": skill_used,
            }
        else:
            if record_failure(self.blackbook, domain):
                logger.warning(f"         🚫 Domain bị cách ly (7 ngày): {domain}")
            return None

    def validate_content(self, content_data: dict) -> bool:
        """Content quality gate — lọc theo SCIENCE_ONTOLOGY_KEYWORDS.

        Ngưỡng MIN_ONTOLOGY_KEYWORDS đặt thấp (mặc định 2) vì văn phong
        học thuật thường súc tích, không lặp từ khóa dày đặc như nội dung
        thông thường. Nâng ngưỡng chỉ sau khi xác nhận bằng dữ liệu mẫu
        thật rằng quá nhiều nội dung không liên quan lọt qua.
        """
        content = content_data.get("content", "")
        if len(content) < settings.MIN_CONTENT_LENGTH:
            return False
        content_lower = content.lower()
        count = sum(1 for kw in settings.SCIENCE_ONTOLOGY_KEYWORDS if kw in content_lower)
        return count >= settings.MIN_ONTOLOGY_KEYWORDS

    def scrape_links(self, links: list[dict]) -> list[dict]:
        """Cào toàn bộ danh sách link với anti-ban delay."""
        logger.info("=" * 80)
        logger.info("📥 T2: SCRAPE — Anti-Ban Mode")
        logger.info("=" * 80)

        scraped = []

        # BUG-4 fix: trước đây `_close_playwright()`/`_save_blackbook()`
        # chỉ được gọi ở CUỐI vòng lặp — nếu 1 exception lạ (chưa được
        # try/except trong process_link() bắt) bay ra giữa vòng lặp,
        # Chromium subprocess trở thành zombie process (không bao giờ
        # đóng). Bọc toàn bộ vòng lặp trong try/finally đảm bảo
        # _save_blackbook() + _close_playwright() LUÔN chạy, dù thành
        # công, dù lỗi biết trước, hay dù exception lạ bay ra giữa chừng.
        try:
            for i, link in enumerate(links, 1):
                logger.info(f"\n   [{i}/{len(links)}] {link['url'][:70]}")

                content_data = self.process_link(link)

                if content_data:
                    if self.validate_content(content_data):
                        content_data.update({
                            "keyword":  link.get("keyword"),
                            "label":    link.get("label"),
                            "priority": link.get("priority"),
                            "domain":   link.get("domain"),
                        })
                        scraped.append(content_data)
                        logger.info(
                            f"         ✅ {content_data['content_length']} chars "
                            f"[{content_data['skill_used']}]"
                        )
                    else:
                        content = content_data.get("content", "")
                        content_lower = content.lower()
                        kw_count = sum(
                            1 for kw in settings.SCIENCE_ONTOLOGY_KEYWORDS if kw in content_lower
                        )
                        logger.warning(
                            f"         ⚠️  Nội dung không đạt ngưỡng — "
                            f"len={len(content)} (min={settings.MIN_CONTENT_LENGTH}), "
                            f"ontology_kw={kw_count} (min={settings.MIN_ONTOLOGY_KEYWORDS})"
                        )
                else:
                    logger.error("         ❌ Scrape thất bại (HTTP + Playwright đều không thành công)")

                # Lưu blackbook sau mỗi 3 link để không mất trạng thái nếu crash
                if i % 3 == 0:
                    self._save_blackbook()

                # Delay giữa các request (bỏ qua link cuối)
                if i < len(links):
                    human_delay(
                        min_sec=settings.MIN_REQUEST_DELAY,
                        max_sec=settings.MAX_REQUEST_DELAY,
                    )
        finally:
            self._save_blackbook()
            self._close_playwright()

        logger.info(f"\n📊 TỔNG: {len(scraped)} / {len(links)} link đạt tiêu chuẩn")
        return scraped


def run_t2(links: list[dict]) -> list[dict]:
    """Entry point cho T2."""
    scraper = T2Scrape()
    return scraper.scrape_links(links)
