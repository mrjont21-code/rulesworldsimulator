"""
T1: CLASSIFY LINKS - Phân loại links với extended sources
Pattern Tinnhanh + Rulesworld sources
Yêu cầu 100% file chỉnh sửa là file code đầy đủ
"""
import re
import logging
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class T1Classify:
    def __init__(self):
        # Bảng ưu tiên nguồn — đảo ngược so với thiết kế "nhà khoa học" cũ.
        # Pipeline này không xây bách khoa toàn thư, nó xây kho vũ khí thị
        # giác và drama cho kịch bản. Các trang thiết kế giả tưởng/tropes đã
        # có sẵn văn phong kịch tính, hệ sinh thái phân tầng giai cấp, kẻ đi
        # săn/mồi nguy hiểm — đốt cháy xung đột cho kịch bản. Academic/gov
        # viết quá trung lập, khô khan -> hạ xuống hàng thứ yếu (tư liệu tham
        # chiếu khi cần một cơ chế vật lý cụ thể, không phải nguồn chính).
        self.domain_rules = {
            # Worldbuilding / Speculative fiction / Tropes - TOP priority.
            # Đây là nguồn chất liệu chính: nguyên mẫu sinh vật, cơ chế di
            # chuyển/chiến đấu/cái chết, xã hội hư cấu ngoài carbon.
            "orionsarm.com": {"label": "worldbuilding_fiction", "scraper_type": "html_simple", "priority": 1},
            "worldanvil.com": {"label": "worldbuilding_fiction", "scraper_type": "html_simple", "priority": 1},
            "projectperditus.com": {"label": "worldbuilding_fiction", "scraper_type": "html_simple", "priority": 1},
            "spec-evo.fandom.com": {"label": "worldbuilding_fiction", "scraper_type": "html_simple", "priority": 1},
            "speculativeevolution.fandom.com": {"label": "worldbuilding_fiction", "scraper_type": "html_simple", "priority": 1},
            "amphiterra.weebly.com": {"label": "worldbuilding_fiction", "scraper_type": "html_simple", "priority": 1},
            "tvtropes.org": {"label": "worldbuilding_fiction", "scraper_type": "html_simple", "priority": 1},
            "mythcreants.com": {"label": "worldbuilding_fiction", "scraper_type": "html_simple", "priority": 1},
            "worldbuildingschool.com": {"label": "worldbuilding_fiction", "scraper_type": "html_simple", "priority": 1},
            "projectrho.com": {"label": "worldbuilding_fiction", "scraper_type": "html_simple", "priority": 1},

            # Wikipedia - vẫn cao vì cung cấp luật nền vật lý/sinh học đáng
            # tin cậy để "neo" các cơ chế giả tưởng, nhưng không còn số 1 mặc
            # định như academic paper trước đây.
            "wikipedia.org": {"label": "wiki_article", "scraper_type": "html_simple", "priority": 2},

            # Community/Discussion - nguồn ý tưởng sáng tạo, giọng văn tự
            # nhiên, giàu tính kịch (r/worldbuilding, r/speculativeevolution).
            "reddit.com": {"label": "community_discussion", "scraper_type": "reddit", "priority": 2},

            # Wiki/Fandom generic - nâng từ 5 lên 2 vì phần lớn traffic vẫn là
            # fandom khoa học viễn tưởng/quái vật hữu ích cho concept art, chỉ
            # còn hạ nhẹ so với worldbuilding chuyên biệt ở trên.
            "fandom.com": {"label": "wiki_fandom", "scraper_type": "html_simple", "priority": 2},
            "wikia.com": {"label": "wiki_fandom", "scraper_type": "html_simple", "priority": 2},
            "wikidot.com": {"label": "wiki_fandom", "scraper_type": "html_simple", "priority": 2},
            "stackexchange.com": {"label": "community_discussion", "scraper_type": "html_simple", "priority": 3},
            "quora.com": {"label": "community_discussion", "scraper_type": "html_simple", "priority": 3},

            # Science News/Magazines - hạ xuống priority 3: vẫn hữu ích để
            # "vay mượn" một hiệu ứng thị giác/cơ chế môi trường cụ thể, nhưng
            # không còn là nguồn ưu tiên hàng đầu.
            "scientificamerican.com": {"label": "science_news", "scraper_type": "html_simple", "priority": 3},
            "space.com": {"label": "science_news", "scraper_type": "html_simple", "priority": 3},
            "universetoday.com": {"label": "science_news", "scraper_type": "html_simple", "priority": 3},
            "astrobio.net": {"label": "science_news", "scraper_type": "html_simple", "priority": 3},
            "phys.org": {"label": "science_news", "scraper_type": "html_simple", "priority": 3},
            "sciencedaily.com": {"label": "science_news", "scraper_type": "html_simple", "priority": 3},
            "newscientist.com": {"label": "science_news", "scraper_type": "html_simple", "priority": 3},
            "quantamagazine.org": {"label": "science_news", "scraper_type": "html_simple", "priority": 3},
            "wired.com": {"label": "science_news", "scraper_type": "html_simple", "priority": 3},
            "theverge.com": {"label": "science_news", "scraper_type": "html_simple", "priority": 3},

            # Academic/Research - hạ xuống thấp nhất trong nhóm có nhãn riêng.
            # Văn phong quá trung lập/khô khan để LLM học cách viết kịch tính,
            # nhưng vẫn giữ lại làm tư liệu đối chiếu khi cần độ chính xác.
            "arxiv.org": {"label": "academic_paper", "scraper_type": "html_simple", "priority": 4},
            "nature.com": {"label": "academic_paper", "scraper_type": "html_simple", "priority": 4},
            "science.org": {"label": "academic_paper", "scraper_type": "html_simple", "priority": 4},
            "ncbi.nlm.nih.gov": {"label": "academic_paper", "scraper_type": "html_simple", "priority": 4},
            "pubmed.ncbi.nlm.nih.gov": {"label": "academic_paper", "scraper_type": "html_simple", "priority": 4},
            "researchgate.net": {"label": "academic_paper", "scraper_type": "html_simple", "priority": 4},
            "academia.edu": {"label": "academic_paper", "scraper_type": "html_simple", "priority": 4},
            "scholar.google.com": {"label": "academic_paper", "scraper_type": "html_simple", "priority": 4},
            "doi.org": {"label": "academic_paper", "scraper_type": "html_simple", "priority": 4},
            "springer.com": {"label": "academic_paper", "scraper_type": "html_simple", "priority": 4},
            "wiley.com": {"label": "academic_paper", "scraper_type": "html_simple", "priority": 4},
            "elsevier.com": {"label": "academic_paper", "scraper_type": "html_simple", "priority": 4},
            "plos.org": {"label": "academic_paper", "scraper_type": "html_simple", "priority": 4},

            # Government/Space Agencies - thấp nhất. Văn phong báo cáo chính
            # thức gần như không có giá trị kịch tính trực tiếp.
            "nasa.gov": {"label": "government_research", "scraper_type": "html_simple", "priority": 5},
            "esa.int": {"label": "government_research", "scraper_type": "html_simple", "priority": 5},
            "jaxa.jp": {"label": "government_research", "scraper_type": "html_simple", "priority": 5},
        }

        # Path-based rules (đồng bộ thang ưu tiên mới: worldbuilding/tropes=1,
        # wiki/community=2, science news=3, academic=4)
        self.path_rules = [
            (r"/wiki/|/species/|/lore/|/world/", "worldbuilding_fiction", "html_simple", 1),
            (r"\.pdf$", "pdf_document", "pdf", 2),
            (r"/blog/", "blog_article", "html_simple", 2),
            (r"/article/", "blog_article", "html_simple", 2),
            (r"/news/", "science_news", "html_simple", 3),
            (r"/research/", "academic_paper", "html_simple", 4),
            (r"/paper/", "academic_paper", "html_simple", 4),
            (r"/publication/", "academic_paper", "html_simple", 4),
        ]

    def classify_link(self, url: str) -> dict:
        """Phân loại link dựa trên URL và domain"""
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        path = parsed.path.lower()

        # Check domain rules first
        for domain_pattern, rule in self.domain_rules.items():
            if domain_pattern in domain:
                return {
                    "label": rule["label"],
                    "scraper_type": rule["scraper_type"],
                    "priority": rule["priority"],
                    "domain": domain
                }

        # Check path rules
        for pattern, label, scraper_type, priority in self.path_rules:
            if re.search(pattern, path):
                return {
                    "label": label,
                    "scraper_type": scraper_type,
                    "priority": priority,
                    "domain": domain
                }

        # Default
        return {
            "label": "general_article",
            "scraper_type": "html_simple",
            "priority": 4,
            "domain": domain
        }

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

            # Log ngắn gọn
            priority_icon = {1: "🔴", 2: "🟡", 3: "🟢", 4: "⚪", 5: "⚫"}.get(classification["priority"], "⚪")
            logger.info(f"   {priority_icon} {link['domain'][:30]:<30} → {classification['label']}")

        # Sắp xếp theo priority (1 = cao nhất)
        classified.sort(key=lambda x: x["priority"])

        # Thống kê
        labels = {}
        for link in classified:
            label = link["label"]
            labels[label] = labels.get(label, 0) + 1

        logger.info(f"\n📊 Thống kê:")
        for label, count in sorted(labels.items(), key=lambda x: -x[1]):
            logger.info(f"   {label}: {count}")

        return classified


def run_t1(links: list[dict]) -> list[dict]:
    """Entry point cho T1"""
    classifier = T1Classify()
    return classifier.classify_links(links)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - [T1] %(message)s',
        datefmt='%H:%M:%S'
    )

    # Test
    test_links = [
        {"url": "https://arxiv.org/abs/2301.12345"},
        {"url": "https://en.wikipedia.org/wiki/Astrobiology"},
        {"url": "https://speculativeevolution.fandom.com/wiki/Aerosaur"},
        {"url": "https://www.nasa.gov/mission/"},
        {"url": "https://example.com/random-page"},
    ]

    classified = run_t1(test_links)
    print(f"\n✅ Classified {len(classified)} links")
