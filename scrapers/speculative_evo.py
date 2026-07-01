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

    def get_category_members(self, category_name, limit=None):
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
            }

            if continue_token:
                params["cmcontinue"] = continue_token

            try:
                response = requests.get(self.api_url, params=params, timeout=30)
                response.raise_for_status()
                data = response.json()

                members = data.get("query", {}).get("categorymembers", [])
                titles = [m["title"] for m in members]
                all_titles.extend(titles)

                continue_token = data.get("continue", {}).get("cmcontinue")
                if not continue_token:
                    break

                time.sleep(self.delay)

            except Exception as e:
                logger.error(f"SpecEvo - Error fetching {category_name}: {e}")
                break

        return all_titles

    def get_page_content(self, title):
        params = {
            "action": "parse",
            "page": title,
            "prop": "wikitext|text|categories",
            "format": "json",
        }

        try:
            response = requests.get(self.api_url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            parse_data = data.get("parse", {})
            wikitext = parse_data.get("wikitext", {}).get("*", "")

            infobox = self._parse_infobox(wikitext)

            return {
                "title": title,
                "source": "speculative_evo",
                "wikitext": wikitext,
                "infobox": infobox,
                "categories": [
                    cat["*"] for cat in parse_data.get("categories", [])
                ],
                "url": f"https://speculativeevolution.fandom.com/wiki/{title.replace(' ', '_')}",
            }

        except Exception as e:
            logger.error(f"SpecEvo - Error fetching '{title}': {e}")
            return None

    def _parse_infobox(self, wikitext):
        infobox = {}
        pattern = r"\|(\w+)\s*=\s*(.+?)(?=\n\||\n\}\})"
        matches = re.findall(pattern, wikitext)

        for key, value in matches:
            clean_value = re.sub(r"\{\{.*?\}\}", "", value).strip()
            clean_value = re.sub(r"\[\[.*?\|(.*?)\]\]", r"\1", clean_value)
            clean_value = re.sub(r"\[\[(.*?)\]\]", r"\1", clean_value)
            if clean_value:
                infobox[key.strip()] = clean_value

        return infobox

    def scrape_all(self):
        articles = []
        seen_titles = set()

        for category in settings.SPEC_EVO_CATEGORIES:
            titles = self.get_category_members(category)

            for title in titles:
                if title in seen_titles:
                    continue
                seen_titles.add(title)

                if len(articles) >= settings.MAX_ARTICLES_TOTAL:
                    break

                article = self.get_page_content(title)
                if article:
                    articles.append(article)

                time.sleep(self.delay)

        logger.info(f"Speculative Evo total: {len(articles)} articles scraped")
        return articles
