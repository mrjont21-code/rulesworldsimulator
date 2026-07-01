"""
T1: CLASSIFY LINKS - Phân loại links bằng Python rule-based
"""
import re
import logging
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class T1Classify:
    def __init__(self):
        pass

    def classify_link(self, url: str) -> dict:
        """
        Phân loại link dựa trên URL và domain
        Trả về: {label, scraper_type, priority}
        """
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        path = parsed.path.lower()
        
        # Xác định label
        label = self._determine_label(domain, path)
        
        # Xác định kỹ thuật cào
        scraper_type = self._determine_scraper_type(domain, path)
        
        # Xác định priority
        priority = self._determine_priority(domain, label)
        
        return {
            "label": label,
            "scraper_type": scraper_type,
            "priority": priority,
            "domain": domain
        }

    def _determine_label(self, domain: str, path: str) -> str:
        """Xác định loại nội dung"""
        
        # Academic/Research
        if any(x in domain for x in ["ncbi", "pubmed", "nature.com", "science.org", 
                                      "researchgate", "arxiv", "harvard"]):
            return "academic_paper"
        
        # Wikipedia
        if "wikipedia.org" in domain:
            return "wiki_article"
        
        # Community/Discussion
        if any(x in domain for x in ["reddit.com", "quora.com", "stackexchange"]):
            return "community_discussion"
        
        # Wiki/Fandom
        if any(x in domain for x in ["fandom.com", "wikia.com"]):
            return "wiki_fandom"
        
        # Social Media
        if any(x in domain for x in ["facebook.com", "twitter.com", "youtube.com"]):
            return "social_media"
        
        # Blog/News
        if any(x in path for x in ["blog", "article", "post", "news"]):
            return "blog_article"
        
        # PDF
        if path.endswith(".pdf"):
            return "pdf_document"
        
        # Default
        return "general_article"

    def _determine_scraper_type(self, domain: str, path: str) -> str:
        """Xác định kỹ thuật cào"""
        
        # PDF
        if path.endswith(".pdf"):
            return "pdf"
        
        # Wikipedia/Fandom - HTML thuần
        if any(x in domain for x in ["wikipedia.org", "fandom.com", "wikia.com"]):
            return "html_simple"
        
        # Academic sites - HTML thuần
        if any(x in domain for x in ["ncbi", "pubmed", "nature.com", "science.org"]):
            return "html_simple"
        
        # Reddit - cần đặc biệt
        if "reddit.com" in domain:
            return "reddit"
        
        # Default - HTML thuần
        return "html_simple"

    def _determine_priority(self, domain: str, label: str) -> int:
        """Xác định priority (1 = cao nhất, 5 = thấp nhất)"""
        
        # High priority: Academic, Wikipedia
        if label in ["academic_paper", "wiki_article"]:
            return 1
        
        # Medium priority: Wiki Fandom, Blog
        if label in ["wiki_fandom", "blog_article"]:
            return 2
        
        # Low priority: Community, Social
        if label in ["community_discussion", "social_media"]:
            return 3
        
        # Default
        return 4

    def classify_links(self, links: list[dict]) -> list[dict]:
        """Phân loại tất cả links"""
        logger.info("=" * 80)
        logger.info("🏷️  T1: CLASSIFY LINKS")
        logger.info("=" * 80)
        
        classified = []
        for link in links:
            classification = self.classify_link(link["url"])
            link.update(classification)
            classified.append(link)
            
            logger.info(f"   {link['url'][:60]:<60} → {classification['label']}")
        
        # Sắp xếp theo priority
        classified.sort(key=lambda x: x["priority"])
        
        # Thống kê
        labels = {}
        for link in classified:
            label = link["label"]
            labels[label] = labels.get(label, 0) + 1
        
        logger.info(f"\n📊 Thống kê:")
        for label, count in sorted(labels.items()):
            logger.info(f"   {label}: {count}")
        
        return classified
