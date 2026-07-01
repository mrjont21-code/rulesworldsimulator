"""
SpeculativeEvoScraper - Fandom MediaWiki API
ĐÃ XÁC NHẬN QUA DEBUG: API vẫn hoạt động (status 200, JSON hợp lệ)
Thêm logic tự động tìm category names đúng
"""
import requests
import time
import re
import logging
from config import settings

logger = logging.getLogger(__name__)


class SpeculativeEvoScraper:
    def __init__(self):
        self.api_url = settings.SPEC_EVO_API
        self.delay = settings.REQUEST_DELAY_SECONDS
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "WorldLoreHarvester/2.0 (research bot; contact via github)"
        })

    def get_category_members(self, category_name: str, limit: int | None = None) -> list[str]:
        if limit is None:
            limit = settings.MAX_ARTICLES_PER_CATEGORY

        all_titles = []
        continue_token = None

        while len(all_titles) < limit:
            params = {
                "action": "query",
                "list": "categorymembers",
                "cmtitle": f"Category:{category_name}",
                "cmlimit": min(500, limit - len(all_titles)),
                "format": "json",
                "cmprop": "title",
            }

            if continue_token:
                params["cmcontinue"] = continue_token

            try:
                resp = self.session.get(self.api_url, params=params, timeout=30)
                resp.raise_for_status()
                data = resp.json()

                members = data.get("query", {}).get("categorymembers", [])
                titles = [m["title"] for m in members if not m["title"].startswith("Category:")]
                all_titles.extend(titles)

                continue_token = data.get("continue", {}).get("cmcontinue")
                if not continue_token:
                    break

                time.sleep(self.delay)

            except Exception as e:
                logger.error(f"SpecEvo - Lỗi category '{category_name}': {e}")
                break

        return all_titles

    def get_page_content(self, title: str) -> dict | None:
        params = {
            "action": "parse",
            "page": title,
            "prop": "wikitext|categories",
            "format": "json",
        }

        try:
            resp = self.session.get(self.api_url, params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()

            if "error" in data:
                return None

            parse_data = data.get("parse", {})
            wikitext = parse_data.get("wikitext", {}).get("*", "")

            if len(wikitext) < 100:
                return None

            infobox = self._parse_infobox(wikitext)

            return {
                "title": title,
                "source": "speculative_evo",
                "wikitext": wikitext,
                "infobox": infobox,
                "categories": [cat["*"] for cat in parse_data.get("categories", [])],
                "url": f"https://speculativeevolution.fandom.com/wiki/{title.replace(' ', '_')}",
            }

        except Exception as e:
            logger.error(f"SpecEvo - Lỗi trang '{title}': {e}")
            return None

    def _parse_infobox(self, wikitext: str) -> dict:
        infobox = {}
        template_match = re.search(r"\{\{([^}]+)\}\}", wikitext, re.DOTALL)
        if template_match:
            content = template_match.group(1)
            for line in content.split("\n"):
                if "=" in line and line.strip().startswith("|"):
                    parts = line.split("=", 1)
                    if len(parts) == 2:
                        key = parts[0].strip().lstrip("|").strip()
                        val = re.sub(r"\[\[(?:[^|\]]*\|)?([^\]]*)\]\]", r"\1", parts[1]).strip()
                        val = re.sub(r"\{\{.*?\}\}", "", val).strip()
                        if key and val:
                            infobox[key] = val
        return infobox

    def _find_valid_categories(self) -> list[str]:
        """Tự động tìm các category names hợp lệ trên wiki"""
        logger.info("🔍 SpecEvo - Đang tìm category names hợp lệ...")

        # Thử nhiều category names khả dĩ
        test_categories = [
            "Species", "Creatures", "Organisms", "Animals", "Plants",
            "Alien_life", "Biology", "Ecosystems", "Xenobiology",
            "Extraterrestrial_life", "Fictional_organisms",
        ]

        valid_categories = []
        for cat in test_categories:
            params = {
                "action": "query",
                "list": "categorymembers",
                "cmtitle": f"Category:{cat}",
                "cmlimit": 1,
                "format": "json",
            }
            try:
                resp = self.session.get(self.api_url, params=params, timeout=15)
                data = resp.json()
                members = data.get("query", {}).get("categorymembers", [])
                if members:
                    valid_categories.append(cat)
                    logger.info(f"  ✅ Category '{cat}': {len(members)}+ bài")
            except Exception as e:
                logger.debug(f"  ❌ Category '{cat}': {e}")

            time.sleep(0.5)

        # Nếu không tìm được category nào, thử lấy tất cả categories
        if not valid_categories:
            logger.info("  ⚠️ Không tìm được category từ danh sách test, thử lấy tất cả...")
            params = {
                "action": "query",
                "list": "allcategories",
                "aclimit": 500,
                "format": "json",
            }
            try:
                resp = self.session.get(self.api_url, params=params, timeout=15)
                data = resp.json()
                all_cats = data.get("query", {}).get("allcategories", [])

                # Lọc categories liên quan đến sinh học
                bio_keywords = ["species", "organism", "creature", "animal", "plant", "life", "bio", "eco"]
                for cat in all_cats:
                    cat_name = cat.get("*", "")
                    if any(kw in cat_name.lower() for kw in bio_keywords):
                        valid_categories.append(cat_name)
                        logger.info(f"  ✅ Tìm thấy: {cat_name}")

            except Exception as e:
                logger.error(f"  ❌ Lỗi lấy allcategories: {e}")

        logger.info(f"📊 Tìm thấy {len(valid_categories)} categories hợp lệ")
        return valid_categories

    def scrape_all(self) -> list[dict]:
        articles = []
        seen_titles: set[str] = set()

        # Tìm category names hợp lệ
        valid_categories = self._find_valid_categories()

        # Nếu vẫn không có, dùng categories từ settings
        if not valid_categories:
            logger.warning("⚠️ Không tìm được category hợp lệ, dùng categories từ settings")
            valid_categories = settings.SPEC_EVO_CATEGORIES

        for category in valid_categories:
            titles = self.get_category_members(category)

            for title in titles:
                if title in seen_titles:
                    continue
                seen_titles.add(title)

                if len(articles) >= settings.MAX_ARTICLES_TOTAL:
                    return articles

                article = self.get_page_content(title)
                if article:
                    articles.append(article)

                time.sleep(self.delay)

        logger.info(f"SpeculativeEvo tổng cộng: {len(articles)} bài")
        return articles

    # ============================================================
    # PHẦN 2: INCREMENTAL
    # ============================================================
    def get_touched_timestamps(self, titles: list[str]) -> dict:
        result = {}
        for i in range(0, len(titles), 50):
            chunk = titles[i:i + 50]
            params = {
                "action": "query",
                "prop": "info",
                "titles": "|".join(chunk),
                "format": "json",
            }
            try:
                resp = self.session.get(self.api_url, params=params, timeout=30)
                resp.raise_for_status()
                data = resp.json()
                pages = data.get("query", {}).get("pages", {})
                for page in pages.values():
                    title = page.get("title")
                    touched = page.get("touched")
                    if title and touched:
                        result[title] = touched
            except Exception as e:
                logger.error(f"SpecEvo - Lỗi lấy touched timestamp: {e}")
            time.sleep(self.delay)
        return result

    def scrape_recent(self, since_iso: str) -> list[dict]:
        articles = []
        seen_titles: set[str] = set()

        valid_categories = self._find_valid_categories()
        if not valid_categories:
            valid_categories = settings.SPEC_EVO_CATEGORIES

        for category in valid_categories:
            titles = self.get_category_members(category)
            new_titles = [t for t in titles if t not in seen_titles]
            seen_titles.update(new_titles)

            if not new_titles:
                continue

            touched_map = self.get_touched_timestamps(new_titles)
            changed_titles = [
                t for t in new_titles
                if touched_map.get(t, "") > since_iso
            ]
            logger.info(
                f"SpecEvo - '{category}': {len(changed_titles)}/{len(new_titles)} "
                f"bài thay đổi sau {since_iso}"
            )

            for title in changed_titles:
                article = self.get_page_content(title)
                if article:
                    articles.append(article)
                time.sleep(self.delay)

        logger.info(f"SpeculativeEvo (recent) tổng cộng: {len(articles)} bài mới/sửa")
        return articles
