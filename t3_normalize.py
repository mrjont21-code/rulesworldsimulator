"""
T3: NORMALIZE DATA — Foundational Knowledge Engine
====================================================
Chuẩn hóa nội dung thô từ T2 sang schema chuẩn để T4 (deduplicate) và
T5 (upload) xử lý. Bước này tập trung trích xuất cấu trúc nhân quả khoa
học — không phải làm giàu tính kịch hay mô tả hình thái thị giác.

Thay đổi so với phiên bản cũ:
- extractive_summary nhận ontology_keywords (thay vì domain_keywords cũ)
  từ settings.SCIENCE_ONTOLOGY_KEYWORDS — ưu tiên câu nhân quả thay vì
  câu mô tả hiệu ứng thị giác.
- Bổ sung field "causal_sentences" trong output để T4/T5 trực tiếp trích
  xuất Rule Object theo schema: Điều kiện → Biến đổi → Kết quả → Hiệu ứng.

LƯU Ý MIGRATION: Field "matched_keywords" trong output được giữ nguyên
tên để không phá vỡ schema MongoDB hiện tại. Nếu muốn đổi sang tên mô tả
hơn (ví dụ "matched_ontology_terms"), phải tạo migration script riêng cho
collection permanent.* trước khi deploy.
"""
import re
import hashlib
import logging
from datetime import datetime, timezone

from config import settings
from summarizer import extractive_summary

logger = logging.getLogger(__name__)


class T3Normalize:
    def __init__(self):
        pass

    def clean_text(self, text: str) -> str:
        """Chuẩn hóa whitespace và loại bỏ khoảng trắng thừa."""
        text = re.sub(r'[ \t]+', ' ', text)
        text = re.sub(r'\n[ \t]+', '\n', text)
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text.strip()

    def normalize_content(self, content_data: dict) -> dict:
        """Chuẩn hóa một item nội dung sang schema Rule Object chuẩn.

        Quy trình:
        1. Làm sạch văn bản thô.
        2. Tạo content_hash (dùng cho deduplication ở T4).
        3. Chạy extractive_summary với SCIENCE_ONTOLOGY_KEYWORDS để ưu
           tiên câu chứa cấu trúc nhân quả (Cause-Effect markers).
        4. Đóng gói kết quả cùng metadata nguồn.
        """
        content = self.clean_text(content_data.get("content", ""))

        # Hash nội dung — T4 dùng để phát hiện bản sao
        content_hash = hashlib.md5(content.encode()).hexdigest()

        url   = content_data.get("url", "")
        title = content_data.get("title", "")

        # rule_id: fingerprint ngắn từ URL + title
        rule_id = hashlib.md5(f"{url}_{title}".encode()).hexdigest()[:12]

        # Trích xuất câu quan trọng bằng Luhn's Algorithm cải tiến.
        # Câu chứa cấu trúc nhân quả (results in, leads to, due to...)
        # được ưu tiên cao hơn câu chỉ chứa từ khóa chủ đề thông thường —
        # vì đây là nguyên liệu trực tiếp cho Rule Object ở T4/T5.
        summary_data = extractive_summary(
            content,
            ontology_keywords=settings.SCIENCE_ONTOLOGY_KEYWORDS,
            max_sentences=6,
            keyword_boost=2.5,
            causal_boost=3.5,
        )

        return {
            "rule_id":          rule_id,
            "url":              url,
            "title":            title[:200],
            "content":          content,
            "content_length":   len(content),
            "content_hash":     content_hash,
            "summary":          summary_data["summary"],
            "key_facts":        summary_data["key_facts"],
            # Câu nhân quả tách riêng — T4/T5 dùng để xây Rule Object
            # theo schema: Điều kiện → Biến đổi → Kết quả → Hiệu ứng phụ.
            "causal_sentences": summary_data["causal_sentences"],
            # Giữ tên "matched_keywords" để tương thích schema MongoDB cũ.
            # Đổi tên field này cần migration script riêng (xem docstring module).
            "matched_keywords": summary_data["matched_keywords"],
            "source_label":     content_data.get("label", "unknown"),
            "keyword":          content_data.get("keyword", ""),
            "domain":           content_data.get("domain", ""),
            "skill_used":       content_data.get("skill_used", ""),
            "scraped_at":       content_data.get("scraped_at"),
            "normalized_at":    datetime.now(timezone.utc).isoformat(),
        }

    def normalize_all(self, contents: list[dict]) -> list[dict]:
        """Chuẩn hóa toàn bộ batch nội dung từ T2."""
        logger.info("=" * 80)
        logger.info("🔧 T3: NORMALIZE DATA — Knowledge Rule Extraction")
        logger.info("=" * 80)

        normalized = []
        for content_data in contents:
            norm_data = self.normalize_content(content_data)
            normalized.append(norm_data)
            causal_count = len(norm_data.get("causal_sentences", []))
            logger.info(
                f"   ✅ {norm_data['rule_id']}: {norm_data['title'][:50]} "
                f"[causal={causal_count}]"
            )

        logger.info(f"\n📊 Đã chuẩn hóa {len(normalized)} mục nội dung")
        return normalized


def run_t3(contents: list[dict]) -> list[dict]:
    """Entry point cho T3."""
    normalizer = T3Normalize()
    return normalizer.normalize_all(contents)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - [T3] %(message)s",
        datefmt="%H:%M:%S",
    )

    # === Test với nội dung chứa cấu trúc nhân quả rõ ràng ===
    test_content = [
        {
            "url": "https://arxiv.org/abs/2301.00001",
            "title": "Adaptive Trait Evolution Under Selective Pressure",
            "label": "physics_biology_rule_source",
            "domain": "arxiv.org",
            "skill_used": "HTTP_SOUP",
            "scraped_at": 1720000000,
            "content": (
                # Câu nhân quả — phải được ưu tiên
                "Natural selection results in the gradual accumulation of adaptive traits "
                "in a population when environmental pressure exceeds reproductive tolerance. "
                "When resource competition intensifies, organisms with higher metabolic efficiency "
                "gain fitness advantage, which leads to speciation over geological time. "
                "Due to genetic drift in small populations, allele frequencies shift independently "
                "of selective pressure, causing founder effects. "
                "Convergent evolution occurs because unrelated lineages face identical environmental "
                "constraints, enabling similar phenotypic solutions to emerge independently. "
                "If mutation rate exceeds repair capacity, genomic instability accelerates, "
                "therefore cancer risk correlates with exposure to mutagenic agents. "
                "Symbiotic relationships modulate the fitness landscape for both partners, "
                "as a consequence altering the trajectory of coevolution. "
                # Câu mô tả thuần — ít quan trọng hơn
                "The organism displays bioluminescent patterns across its dorsal surface. "
                "Its exoskeleton appears iridescent under polarized light. "
                "The colony structure consists of segmented chambers. "
                "The creature moves with a hydraulic joint mechanism. "
                "The specimen measures approximately 2.3 meters in length. "
                "Surface coloration varies between individuals in the same cohort. "
            ) * 5,  # lặp để đủ câu test thuật toán ranking
        }
    ]

    normalized = run_t3(test_content)

    print("\n" + "=" * 60)
    print("KIỂM TRA KẾT QUẢ NORMALIZE:")
    print("=" * 60)
    for item in normalized:
        print(f"\nrule_id      : {item['rule_id']}")
        print(f"content_hash : {item['content_hash']}")
        print(f"matched_kw   : {item['matched_keywords'][:5]}...")
        print(f"\ncausal_sentences ({len(item['causal_sentences'])}):")
        for s in item["causal_sentences"][:3]:
            print(f"  ▶ {s[:100]}")
        print(f"\nkey_facts (top 3):")
        for kf in item["key_facts"][:3]:
            print(f"  • {kf[:100]}")

    print(f"\n✅ Normalized {len(normalized)} items")

    # Kiểm tra câu nhân quả được ưu tiên cao hơn câu mô tả thuần
    if normalized:
        key_facts = normalized[0]["key_facts"]
        causal_sents = set(normalized[0]["causal_sentences"])
        if key_facts:
            top_fact = key_facts[0]
            if top_fact in causal_sents:
                print("✅ PASS: Câu nhân quả được xếp đầu key_facts")
            else:
                # Kiểm tra top 3
                top3_causal = sum(1 for kf in key_facts[:3] if kf in causal_sents)
                if top3_causal >= 2:
                    print(f"✅ PASS: {top3_causal}/3 key_facts đầu là câu nhân quả")
                else:
                    print("⚠️  WARN: Câu nhân quả chưa chiếm đa số top key_facts — "
                          "kiểm tra lại causal_boost hoặc nội dung test")
