"""
T1: CLASSIFY LINKS — Foundational Knowledge Engine
====================================================
Phân loại URL theo bảng ưu tiên nguồn khoa học. Thang ưu tiên phản ánh
đúng mục tiêu hệ thống: thu thập quy luật nhân quả khách quan từ tài liệu
học thuật, sau đó bổ sung bằng nguồn bách khoa và tin tức khoa học.
Tài liệu hư cấu/tham khảo ý tưởng được giữ lại ở mức ưu tiên thấp nhất —
engine downstream (T4/T5) sẽ từ chối tạo Rule Object từ nhãn này trừ khi
có cờ human_review_required = true.
"""
import re
import logging
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class T1Classify:
    def __init__(self):
        # =====================================================================
        # DOMAIN RULES — thứ tự ưu tiên tăng dần (1 = cao nhất, 6 = thấp nhất)
        # =====================================================================
        self.domain_rules = {

            # --- Priority 1: Khoa học nền tảng ---
            # Ontology cốt lõi: Matter, Energy, Space, Time, Biology, Evolution.
            # Đây là nguồn Rule Object chính — mọi quy luật nhân quả lấy từ
            # đây được coi là đáng tin cậy để đưa vào Knowledge Graph.
            "nature.com":              {"label": "physics_biology_rule_source", "scraper_type": "html_simple", "priority": 1},
            "science.org":             {"label": "physics_biology_rule_source", "scraper_type": "html_simple", "priority": 1},
            "arxiv.org":               {"label": "physics_biology_rule_source", "scraper_type": "html_simple", "priority": 1},
            "nasa.gov":                {"label": "astronomy_rule_source",       "scraper_type": "html_simple", "priority": 1},
            "esa.int":                 {"label": "astronomy_rule_source",       "scraper_type": "html_simple", "priority": 1},
            "jaxa.jp":                 {"label": "astronomy_rule_source",       "scraper_type": "html_simple", "priority": 1},
            "ncbi.nlm.nih.gov":        {"label": "biology_rule_source",         "scraper_type": "html_simple", "priority": 1},
            "pubmed.ncbi.nlm.nih.gov": {"label": "biology_rule_source",         "scraper_type": "html_simple", "priority": 1},
            "plos.org":                {"label": "biology_rule_source",         "scraper_type": "html_simple", "priority": 1},

            # --- Priority 2: Khoa học hệ thống / xã hội / nhận thức ---
            # Ontology: Society, Cooperation, Conflict, Intelligence, Information.
            # Bao gồm Game Theory, Network Theory, Systems Theory, Sociology —
            # cung cấp quy luật hành vi tập thể và cấu trúc vận động xã hội.
            "quantamagazine.org":      {"label": "science_secondary_source",    "scraper_type": "html_simple", "priority": 2},
            "sciencedaily.com":        {"label": "science_secondary_source",    "scraper_type": "html_simple", "priority": 2},
            "phys.org":                {"label": "science_secondary_source",    "scraper_type": "html_simple", "priority": 2},
            "astrobio.net":            {"label": "science_secondary_source",    "scraper_type": "html_simple", "priority": 2},
            "researchgate.net":        {"label": "academic_paper",              "scraper_type": "html_simple", "priority": 2},
            "academia.edu":            {"label": "academic_paper",              "scraper_type": "html_simple", "priority": 2},
            "scholar.google.com":      {"label": "academic_paper",              "scraper_type": "html_simple", "priority": 2},
            "springer.com":            {"label": "academic_paper",              "scraper_type": "html_simple", "priority": 2},
            "wiley.com":               {"label": "academic_paper",              "scraper_type": "html_simple", "priority": 2},
            "elsevier.com":            {"label": "academic_paper",              "scraper_type": "html_simple", "priority": 2},
            "doi.org":                 {"label": "academic_paper",              "scraper_type": "html_simple", "priority": 2},
            "santafe.edu":             {"label": "systems_theory_rule_source",  "scraper_type": "html_simple", "priority": 2},
            "pnas.org":                {"label": "systems_theory_rule_source",  "scraper_type": "html_simple", "priority": 2},
            "cell.com":                {"label": "biology_rule_source",         "scraper_type": "html_simple", "priority": 2},
            "frontiersin.org":         {"label": "systems_theory_rule_source",  "scraper_type": "html_simple", "priority": 2},

            # --- Priority 3: Bách khoa toàn thư (định nghĩa gốc / neo khái niệm) ---
            # Wikipedia giữ vai trò xác định ranh giới định nghĩa chuẩn của
            # khái niệm khoa học — không dùng làm nguồn Rule Object chính.
            "wikipedia.org":           {"label": "encyclopedic_reference",      "scraper_type": "html_simple", "priority": 3},

            # --- Priority 4: Tin tức khoa học phổ thông ---
            # Hữu ích để bắt xu hướng nghiên cứu mới, nhưng thiếu độ chính xác
            # học thuật. Chỉ dùng khi không tìm được nguồn Priority 1–2.
            "scientificamerican.com":  {"label": "science_news",                "scraper_type": "html_simple", "priority": 4},
            "space.com":               {"label": "science_news",                "scraper_type": "html_simple", "priority": 4},
            "universetoday.com":       {"label": "science_news",                "scraper_type": "html_simple", "priority": 4},
            "newscientist.com":        {"label": "science_news",                "scraper_type": "html_simple", "priority": 4},
            "wired.com":               {"label": "science_news",                "scraper_type": "html_simple", "priority": 4},
            "theverge.com":            {"label": "science_news",                "scraper_type": "html_simple", "priority": 4},

            # --- Priority 5: Cộng đồng thảo luận ---
            # Chỉ dùng để phát hiện chủ đề / câu hỏi đang được giới nghiên
            # cứu quan tâm. KHÔNG tạo Rule Object trực tiếp từ nguồn này.
            "reddit.com":              {"label": "community_discussion",        "scraper_type": "reddit",      "priority": 5},
            "stackexchange.com":       {"label": "community_discussion",        "scraper_type": "html_simple", "priority": 5},
            "quora.com":               {"label": "community_discussion",        "scraper_type": "html_simple", "priority": 5},

            # --- Priority 6: Hư cấu / Tham khảo ý tưởng (THẤP NHẤT, KHÔNG NÂNG) ---
            # Các nguồn này chỉ được dùng để tham khảo ý tưởng đặt câu hỏi
            # nghiên cứu, KHÔNG BAO GIỜ là nguồn cho Rule Object.
            # Engine T4/T5 phải từ chối xử lý nhãn "fiction_reference_only"
            # trừ khi được gắn cờ human_review_required = true.
            "orionsarm.com":                  {"label": "fiction_reference_only", "scraper_type": "html_simple", "priority": 6},
            "worldanvil.com":                 {"label": "fiction_reference_only", "scraper_type": "html_simple", "priority": 6},
            "projectperditus.com":            {"label": "fiction_reference_only", "scraper_type": "html_simple", "priority": 6},
            "spec-evo.fandom.com":            {"label": "fiction_reference_only", "scraper_type": "html_simple", "priority": 6},
            "speculativeevolution.fandom.com": {"label": "fiction_reference_only", "scraper_type": "html_simple", "priority": 6},
            "amphiterra.weebly.com":          {"label": "fiction_reference_only", "scraper_type": "html_simple", "priority": 6},
            "tvtropes.org":                   {"label": "fiction_reference_only", "scraper_type": "html_simple", "priority": 6},
            "mythcreants.com":                {"label": "fiction_reference_only", "scraper_type": "html_simple", "priority": 6},
            "worldbuildingschool.com":        {"label": "fiction_reference_only", "scraper_type": "html_simple", "priority": 6},
            "projectrho.com":                 {"label": "fiction_reference_only", "scraper_type": "html_simple", "priority": 6},
            "fandom.com":                     {"label": "fiction_reference_only", "scraper_type": "html_simple", "priority": 6},
            "wikia.com":                      {"label": "fiction_reference_only", "scraper_type": "html_simple", "priority": 6},
            "wikidot.com":                    {"label": "fiction_reference_only", "scraper_type": "html_simple", "priority": 6},
        }

        # =====================================================================
        # PATH RULES — ưu tiên theo loại nội dung, không theo nguồn cụ thể
        # =====================================================================
        # Priority 1: đường dẫn chỉ rõ tài liệu học thuật
        # Priority 2: PDF (loại file, độc lập với độ ưu tiên nội dung —
        #             cần scraper riêng, không mix vào HTML pipeline)
        # Priority 3: bách khoa / tin tức / blog trung tính
        # Priority 6: lore / world — tham khảo ý tưởng, không phải Rule source
        self.path_rules = [
            (r"/research/|/paper/|/publication/|/study/",  "academic_paper",       "html_simple", 1),
            (r"\.pdf$",                                    "pdf_document",         "pdf",         2),
            (r"/news/",                                    "science_news",         "html_simple", 3),
            (r"/blog/|/article/",                          "blog_article",         "html_simple", 3),
            (r"/wiki/",                                    "encyclopedic_reference","html_simple", 3),
            (r"/lore/|/world/",                            "fiction_reference_only","html_simple", 6),
        ]

    def classify_link(self, url: str) -> dict:
        """Phân loại một URL theo thang ưu tiên khoa học."""
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        path = parsed.path.lower()

        # Ưu tiên kiểm tra domain trước (độ chính xác cao hơn path)
        for domain_pattern, rule in self.domain_rules.items():
            if domain_pattern in domain:
                return {
                    "label": rule["label"],
                    "scraper_type": rule["scraper_type"],
                    "priority": rule["priority"],
                    "domain": domain,
                }

        # Kiểm tra path nếu domain không khớp
        for pattern, label, scraper_type, priority in self.path_rules:
            if re.search(pattern, path):
                return {
                    "label": label,
                    "scraper_type": scraper_type,
                    "priority": priority,
                    "domain": domain,
                }

        # Fallback: priority 5 (không xác định — thấp hơn science_news,
        # cao hơn fiction_reference_only, không nên chiếm slot ưu tiên cao)
        return {
            "label": "general_article",
            "scraper_type": "html_simple",
            "priority": 5,
            "domain": domain,
        }

    def classify_links(self, links: list[dict]) -> list[dict]:
        """Phân loại tất cả links và sắp xếp theo thang ưu tiên."""
        logger.info("=" * 80)
        logger.info("🏷️  T1: CLASSIFY LINKS — Knowledge Source Prioritization")
        logger.info("=" * 80)

        classified = []
        for link in links:
            classification = self.classify_link(link["url"])
            link.update(classification)
            classified.append(link)

            priority_icon = {
                1: "🔵",  # Khoa học nền tảng
                2: "🟢",  # Academic / hệ thống
                3: "🟡",  # Bách khoa / tin tức
                4: "🟠",  # Tin tức phổ thông
                5: "⚪",  # Cộng đồng / không xác định
                6: "🔴",  # Tham khảo hư cấu — không tạo Rule Object
            }.get(classification["priority"], "⚪")

            logger.info(
                f"   {priority_icon} [{classification['priority']}] "
                f"{link['domain'][:35]:<35} → {classification['label']}"
            )

        # Sắp xếp theo priority tăng dần (1 = cao nhất xử lý trước)
        classified.sort(key=lambda x: x["priority"])

        # Thống kê phân phối nhãn
        label_counts: dict[str, int] = {}
        for link in classified:
            lbl = link["label"]
            label_counts[lbl] = label_counts.get(lbl, 0) + 1

        logger.info("\n📊 Phân phối nhãn nguồn:")
        for label, count in sorted(label_counts.items(), key=lambda x: -x[1]):
            logger.info(f"   {label}: {count}")

        fiction_count = label_counts.get("fiction_reference_only", 0)
        if fiction_count > 0:
            logger.info(
                f"\n⚠️  {fiction_count} link(s) có nhãn 'fiction_reference_only' — "
                f"T4/T5 sẽ từ chối tạo Rule Object từ các nguồn này."
            )

        return classified


def run_t1(links: list[dict]) -> list[dict]:
    """Entry point cho T1."""
    classifier = T1Classify()
    return classifier.classify_links(links)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - [T1] %(message)s",
        datefmt="%H:%M:%S",
    )

    # === Kiểm tra thang ưu tiên mới ===
    test_links = [
        # Priority 1 — phải lên đầu
        {"url": "https://arxiv.org/abs/2301.12345"},
        {"url": "https://www.nature.com/articles/s41586-023-00001-x"},
        {"url": "https://www.nasa.gov/mission/artemis/"},
        {"url": "https://pubmed.ncbi.nlm.nih.gov/12345678/"},
        # Priority 2
        {"url": "https://www.quantamagazine.org/evolution-article-2024"},
        {"url": "https://www.santafe.edu/research/complexity"},
        # Priority 3
        {"url": "https://en.wikipedia.org/wiki/Astrobiology"},
        # Priority 4
        {"url": "https://www.scientificamerican.com/article/some-topic"},
        # Priority 5
        {"url": "https://www.reddit.com/r/biology/comments/xyz"},
        # Priority 6 — phải xuống đáy
        {"url": "https://speculativeevolution.fandom.com/wiki/Aerosaur"},
        {"url": "https://www.worldanvil.com/w/some-world"},
        {"url": "https://tvtropes.org/pmwiki/pmwiki.php/Main/SomeTrope"},
        # Path rules
        {"url": "https://example.com/research/paper-on-systems"},
        {"url": "https://example.com/lore/history-of-faction"},
    ]

    classified = run_t1(test_links)

    print("\n" + "=" * 60)
    print("KIỂM TRA KẾT QUẢ PHÂN LOẠI:")
    print("=" * 60)
    for link in classified:
        p = link["priority"]
        expected_ok = True
        # Xác nhận các trường hợp quan trọng
        if "arxiv.org" in link["url"] and p != 1:
            expected_ok = False
        if "fandom.com" in link["url"] and p != 6:
            expected_ok = False
        if "worldanvil.com" in link["url"] and p != 6:
            expected_ok = False
        if "tvtropes.org" in link["url"] and p != 6:
            expected_ok = False
        if "nasa.gov" in link["url"] and p != 1:
            expected_ok = False

        status = "✅" if expected_ok else "❌ PRIORITY SAI"
        print(f"   {status} [{p}] {link['label']:<35} {link['url'][:55]}")

    print(f"\n✅ Đã phân loại {len(classified)} links")
