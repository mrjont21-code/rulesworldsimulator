"""
OrionsArmScraper - Dùng Playwright để khám phá CMS mới
Áp dụng:
- Kỹ thuật 1 (SSR): Bóc JSON ngầm từ thẻ <script id="__NEXT_DATA__">
- Kỹ thuật 2 (Radar): Đón bắt API ngầm khi browser render
- Kỹ thuật 4 (DOM Extraction): Bóc dữ liệu sau khi JS render
"""
import re
import json
import time
import logging
from playwright.sync_api import sync_playwright
from config import settings

logger = logging.getLogger(__name__)


class OrionsArmScraper:
    def __init__(self):
        self.base_url = settings.ORIONS_ARM_BASE
        self.encyclopedia_url = settings.ORIONS_ARM_ENCYCLOPEDIA
        self.delay = settings.REQUEST_DELAY_SECONDS
        self.found_apis = []

    # ============================================================
    # KỸ THUẬT 2: RADAR ĐÁNH CHẶN MẠNG
    # ============================================================
    def _intercept_response(self, response):
        """Đón bắt tất cả API JSON khi browser render trang"""
        content_type = response.headers.get("content-type", "")
        if "application/json" in content_type:
            url = response.url
            # Lọc bỏ API rác
            if not any(x in url for x in ["google", "analytics", "ads", "tracking"]):
                self.found_apis.append(url)
                logger.debug(f"🎯 Radar bắt được API: {url}")

    # ============================================================
    # KỸ THUẬT 1: BÓC TÁCH SSR
    # ============================================================
    def _extract_ssr_data(self, html_content: str) -> dict | None:
        """Bóc JSON ngầm từ thẻ <script id="__NEXT_DATA__"> hoặc tương tự"""
        # Thử __NEXT_DATA__ (Next.js)
        match = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html_content, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass

        # Thử window.__INITIAL_STATE__
        match = re.search(r'window\.__INITIAL_STATE__\s*=\s*({.*?});', html_content, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass

        # Thử window.__PUBLIC_RUNTIME_CONFIG__
        match = re.search(r'window\.__PUBLIC_RUNTIME_CONFIG__\s*=\s*({.*?});', html_content, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass

        return None

    # ============================================================
    # KHÁM PHÁ CẤU TRÚC SITE BẰNG PLAYWRIGHT
    # ============================================================
    def _discover_site_structure(self) -> dict:
        """
        Dùng Playwright mở trang Encyclopedia, kích hoạt Radar,
        bóc SSR data, và tìm tất cả article links.
        """
        result = {
            "ssr_data": None,
            "found_apis": [],
            "article_links": [],
            "html_content": "",
        }

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=settings.PLAYWRIGHT_HEADLESS)
            page = browser.new_page()

            # Kích hoạt Radar (Kỹ thuật 2)
            page.on("response", self._intercept_response)

            logger.info(f"🌐 Truy cập {self.encyclopedia_url}...")
            try:
                page.goto(self.encyclopedia_url, timeout=settings.PLAYWRIGHT_TIMEOUT, wait_until="networkidle")
                time.sleep(3)  # Đợi JS render xong
            except Exception as e:
                logger.warning(f"Lỗi tải trang: {e}, thử lại với domcontentloaded...")
                page.goto(self.encyclopedia_url, timeout=settings.PLAYWRIGHT_TIMEOUT, wait_until="domcontentloaded")
                time.sleep(5)

            # Lấy HTML content
            html_content = page.content()
            result["html_content"] = html_content

            # Bóc SSR data (Kỹ thuật 1)
            ssr_data = self._extract_ssr_data(html_content)
            result["ssr_data"] = ssr_data
            if ssr_data:
                logger.info(f"✅ Bóc được SSR data: {len(str(ssr_data))} chars")

            # Lưu found APIs
            result["found_apis"] = list(set(self.found_apis))
            logger.info(f"📡 Radar bắt được {len(result['found_apis'])} APIs")

            # Tìm tất cả article links (Kỹ thuật 4: DOM Extraction)
            links = page.eval_on_selector_all("a[href]", "elements => elements.map(e => e.href)")
            article_links = []
            for link in links:
                # Tìm links chứa 'article', 'eg-', 'encyclopedia'
                if any(pattern in link.lower() for pattern in ["article", "eg-", "encyclopedia"]):
                    if link not in article_links:
                        article_links.append(link)

            result["article_links"] = article_links
            logger.info(f"🔗 Tìm thấy {len(article_links)} article links")

            browser.close()

        return result

    # ============================================================
    # LẤY NỘI DUNG BÀI VIẾT
    # ============================================================
    def _get_article_content(self, url: str) -> dict | None:
        """Dùng Playwright để lấy nội dung bài viết sau khi JS render"""
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=settings.PLAYWRIGHT_HEADLESS)
                page = browser.new_page()

                page.goto(url, timeout=settings.PLAYWRIGHT_TIMEOUT, wait_until="domcontentloaded")
                time.sleep(2)

                # Lấy title
                title = page.title()

                # Lấy nội dung chính (thử nhiều selector)
                content = None
                for selector in [
                    "article",
                    "main",
                    ".article-content",
                    ".content",
                    "#content",
                    ".post-content",
                ]:
                    try:
                        element = page.locator(selector).first
                        if element.is_visible():
                            content = element.inner_text()
                            break
                    except:
                        continue

                # Fallback: lấy toàn bộ text
                if not content or len(content) < 100:
                    content = page.locator("body").inner_text()

                browser.close()

                if not content or len(content) < 100:
                    return None

                return {
                    "title": title,
                    "source": "orions_arm",
                    "content": content,
                    "url": url,
                }

        except Exception as e:
            logger.error(f"OrionsArm - Lỗi tải '{url}': {e}")
            return None

    # ============================================================
    # SCRAPE TOÀN BỘ
    # ============================================================
    def scrape_all(self) -> list[dict]:
        """
        Quy trình:
        1. Khám phá cấu trúc site bằng Playwright + Radar
        2. Nếu tìm được SSR data → extract articles từ đó
        3. Nếu tìm được APIs → gọi trực tiếp
        4. Fallback: crawl từ article links
        """
        logger.info("🚀 OrionsArm - Bắt đầu khám phá site structure...")

        # Bước 1: Khám phá cấu trúc
        structure = self._discover_site_structure()

        articles = []

        # Bước 2: Thử extract từ SSR data
        if structure["ssr_data"]:
            logger.info("📦 Thử extract articles từ SSR data...")
            ssr_articles = self._extract_from_ssr(structure["ssr_data"])
            articles.extend(ssr_articles)
            logger.info(f"  → Extract được {len(ssr_articles)} bài từ SSR")

        # Bước 3: Thử gọi APIs bắt được
        if structure["found_apis"] and len(articles) < settings.MAX_ARTICLES_TOTAL:
            logger.info(f"📡 Thử gọi {len(structure['found_apis'])} APIs bắt được...")
            api_articles = self._extract_from_apis(structure["found_apis"])
            articles.extend(api_articles)
            logger.info(f"  → Extract được {len(api_articles)} bài từ APIs")

        # Bước 4: Fallback - crawl từ article links
        if len(articles) < settings.MAX_ARTICLES_TOTAL and structure["article_links"]:
            logger.info(f"🔗 Fallback: crawl từ {len(structure['article_links'])} article links...")
            for i, url in enumerate(structure["article_links"][:settings.MAX_ARTICLES_TOTAL]):
                if len(articles) >= settings.MAX_ARTICLES_TOTAL:
                    break

                logger.info(f"  [{i+1}] {url}")
                article = self._get_article_content(url)
                if article:
                    articles.append(article)
                time.sleep(self.delay)

        logger.info(f"✅ OrionsArm tổng cộng: {len(articles)} bài")
        return articles

    def _extract_from_ssr(self, ssr_data: dict) -> list[dict]:
        """Extract articles từ SSR data (cấu trúc phụ thuộc vào CMS)"""
        articles = []

        # Thử nhiều cấu trúc khả dĩ
        def find_articles_in_dict(data, path=""):
            if isinstance(data, dict):
                # Kiểm tra nếu dict có vẻ là article
                if any(key in data for key in ["title", "content", "body", "text"]):
                    if "title" in data and ("content" in data or "body" in data or "text" in data):
                        articles.append({
                            "title": data.get("title", "Unknown"),
                            "source": "orions_arm",
                            "content": data.get("content") or data.get("body") or data.get("text", ""),
                            "url": data.get("url", data.get("link", "")),
                        })
                        return

                # Recurse vào các nested dicts
                for key, value in data.items():
                    find_articles_in_dict(value, f"{path}.{key}")

            elif isinstance(data, list):
                for i, item in enumerate(data):
                    find_articles_in_dict(item, f"{path}[{i}]")

        find_articles_in_dict(ssr_data)
        return articles

    def _extract_from_apis(self, apis: list[str]) -> list[dict]:
        """Thử gọi các APIs bắt được để lấy articles"""
        import requests

        articles = []
        for api_url in apis[:10]:  # Giới hạn 10 APIs để test
            try:
                resp = requests.get(api_url, timeout=15)
                if resp.status_code == 200:
                    data = resp.json()
                    # Thử extract articles từ response
                    extracted = self._extract_from_ssr(data)
                    articles.extend(extracted)
            except Exception as e:
                logger.debug(f"API {api_url} lỗi: {e}")

        return articles

    # ============================================================
    # PHẦN 2: INCREMENTAL
    # ============================================================
    def scrape_recent(self, since_iso: str) -> list[dict]:
        """
        Chỉ cào bài mới. Vì CMS mới không có API touched timestamp,
        ta crawl lại toàn bộ và so sánh với danh sách đã biết trong MongoDB.
        """
        logger.info(f"OrionsArm - Crawl recent (since {since_iso})...")

        # Crawl toàn bộ
        all_articles = self.scrape_all()

        # So sánh với MongoDB
        from storage import MongoUploader
        try:
            uploader = MongoUploader()
            existing_urls = set(
                doc["url"] for doc in uploader.db[settings.MONGODB_COLLECTION_RAW].find(
                    {"source": "orions_arm"},
                    {"url": 1}
                )
            )
            uploader.close()
        except Exception:
            existing_urls = set()

        # Lọc bài mới
        new_articles = [a for a in all_articles if a.get("url") not in existing_urls]
        logger.info(f"OrionsArm (recent): {len(new_articles)} bài mới")

        return new_articles
