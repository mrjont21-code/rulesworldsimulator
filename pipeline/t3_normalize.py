"""
T3: NORMALIZE DATA - Chuẩn hóa data về format chuẩn
"""
import re
import hashlib
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class T3Normalize:
    def __init__(self):
        pass

    def normalize_content(self, content_data: dict) -> dict:
        """Chuẩn hóa nội dung"""
        content = content_data.get("content", "")
        
        # Clean text
        content = re.sub(r'\s+', ' ', content)  # Remove extra whitespace
        content = re.sub(r'\n+', '\n', content)  # Normalize newlines
        content = content.strip()
        
        # Generate content hash (để deduplicate)
        content_hash = hashlib.md5(content.encode()).hexdigest()
        
        # Extract metadata
        url = content_data.get("url", "")
        title = content_data.get("title", "")
        
        # Generate rule_id
        rule_id = hashlib.md5(f"{url}_{title}".encode()).hexdigest()[:12]
        
        return {
            "rule_id": rule_id,
            "url": url,
            "title": title,
            "content": content,
            "content_length": len(content),
            "content_hash": content_hash,
            "source_label": content_data.get("label", "unknown"),
            "keyword": content_data.get("keyword", ""),
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
