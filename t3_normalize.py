"""
T3: NORMALIZE DATA - Chuẩn hóa data về format chuẩn
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
        """Clean text"""
        # Remove extra whitespace
        text = re.sub(r'[ \t]+', ' ', text)
        text = re.sub(r'\n[ \t]+', '\n', text)
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text.strip()

    def normalize_content(self, content_data: dict) -> dict:
        """Chuẩn hóa nội dung"""
        content = self.clean_text(content_data.get("content", ""))

        # Generate content hash (để deduplicate)
        content_hash = hashlib.md5(content.encode()).hexdigest()

        # Extract metadata
        url = content_data.get("url", "")
        title = content_data.get("title", "")

        # Generate rule_id
        rule_id = hashlib.md5(f"{url}_{title}".encode()).hexdigest()[:12]

        # Tóm tắt bằng extractive summarizer (thuần Python, không LLM) - săn
        # lùng câu miêu tả hỗn loạn/điểm yếu/hiệu ứng thị giác (DRAMA_KEYWORDS)
        # thay vì câu chứa nhiều thuật ngữ hóa sinh hàn lâm, để làm tư liệu
        # tham khảo giàu tính kịch cho LLM viết kịch bản ở bước sau.
        summary_data = extractive_summary(
            content,
            domain_keywords=settings.DRAMA_KEYWORDS,
            max_sentences=6,
            keyword_boost=3.0,
        )

        return {
            "rule_id": rule_id,
            "url": url,
            "title": title[:200],  # Giới hạn title
            "content": content,
            "content_length": len(content),
            "content_hash": content_hash,
            "summary": summary_data["summary"],
            "key_facts": summary_data["key_facts"],
            "matched_keywords": summary_data["matched_keywords"],
            "source_label": content_data.get("label", "unknown"),
            "keyword": content_data.get("keyword", ""),
            "domain": content_data.get("domain", ""),
            "skill_used": content_data.get("skill_used", ""),
            "scraped_at": content_data.get("scraped_at"),
            "normalized_at": datetime.now(timezone.utc).isoformat()
        }

    def normalize_all(self, contents: list[dict]) -> list[dict]:
        """Chuẩn hóa tất cả nội dung"""
        logger.info("=" * 80)
        logger.info("🔧 T3: NORMALIZE DATA")
        logger.info("=" * 80)
        
        normalized = []
        for content_data in contents:
            norm_data = self.normalize_content(content_data)
            normalized.append(norm_data)
            logger.info(f"   ✅ {norm_data['rule_id']}: {norm_data['title'][:50]}")
        
        logger.info(f"\n📊 Đã chuẩn hóa {len(normalized)} nội dung")
        
        return normalized


def run_t3(contents: list[dict]) -> list[dict]:
    """Entry point cho T3"""
    normalizer = T3Normalize()
    return normalizer.normalize_all(contents)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - [T3] %(message)s',
        datefmt='%H:%M:%S'
    )
    
    # Test
    test_content = [{
        "url": "https://example.com/test",
        "title": "Test Article",
        "content": "This is a test content about astrobiology and alternative biochemistry." * 100,
        "scraped_at": 1234567890
    }]
    
    normalized = run_t3(test_content)
    print(f"\n✅ Normalized {len(normalized)} items")
