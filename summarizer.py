"""
Extractive Summarizer - THUẦN PYTHON, KHÔNG LLM, KHÔNG ML MODEL
=================================================================
Kỹ thuật: Luhn's Algorithm (1958) cải tiến
- Tách câu bằng regex (không cần nltk/spacy tải model)
- Tính điểm mỗi từ theo tần suất xuất hiện (loại stopword)
- Boost điểm cho câu chứa DRAMA_KEYWORDS (từ config.py)
- Boost nhẹ câu ở đầu đoạn văn (thường chứa luận điểm chính)
- Chọn N câu điểm cao nhất, giữ đúng thứ tự gốc -> đọc tự nhiên
Mục đích: rút gọn content thô thành "summary" + "key_facts" để dùng làm
tư liệu tham khảo cho LLM viết kịch bản, KHÔNG cần gọi API nào ở bước này.
"""
import re
from collections import Counter

# Stopword tiếng Anh tối giản (đủ dùng cho văn bản khoa học/wiki, không cần
# tải corpus nltk -> tránh phụ thuộc network lúc chạy trong GitHub Actions)
STOPWORDS = set("""
a an the and or but if then else for while of to in on at by with from
as is are was were be been being this that these those it its it's they
them their there here what which who whom whose when where why how not
no nor so than too very can will just should would could may might must
do does did doing have has had having i you he she we you're i'm we're
also into about over under between among more most some such only own
same other than through during before after above below up down out off
""".split())

SENTENCE_SPLIT_RE = re.compile(r'(?<=[.!?])\s+(?=[A-Z"\u2018\u201c])')
WORD_RE = re.compile(r"[a-zA-Z][a-zA-Z\-']+")


def _split_sentences(text: str) -> list[str]:
    text = re.sub(r'\s+', ' ', text.strip())
    if not text:
        return []
    raw = SENTENCE_SPLIT_RE.split(text)
    # Bỏ câu quá ngắn (thường là rác: nav menu, "Read more", v.v.)
    return [s.strip() for s in raw if len(s.strip()) >= 40]


def _word_frequencies(sentences: list[str]) -> Counter:
    freq = Counter()
    for sent in sentences:
        for w in WORD_RE.findall(sent.lower()):
            if w not in STOPWORDS and len(w) > 2:
                freq[w] += 1
    return freq


def extractive_summary(
    text: str,
    domain_keywords: list[str] | None = None,
    max_sentences: int = 6,
    keyword_boost: float = 2.5,
) -> dict:
    """
    Trả về:
      {
        "summary": "...",       # top câu, giữ thứ tự gốc, đọc liền mạch
        "key_facts": [...],     # top câu, sắp theo điểm giảm dần (câu hay nhất trước)
        "matched_keywords": [...]  # domain_keywords nào xuất hiện trong text
      }
    """
    domain_keywords = [k.lower() for k in (domain_keywords or [])]
    sentences = _split_sentences(text)

    if not sentences:
        return {"summary": "", "key_facts": [], "matched_keywords": []}

    if len(sentences) <= max_sentences:
        return {
            "summary": " ".join(sentences),
            "key_facts": sentences,
            "matched_keywords": sorted({k for k in domain_keywords if k in text.lower()}),
        }

    freq = _word_frequencies(sentences)
    if not freq:
        return {"summary": "", "key_facts": [], "matched_keywords": []}

    max_freq = max(freq.values())
    matched_keywords = set()

    scored = []
    for idx, sent in enumerate(sentences):
        words = [w for w in WORD_RE.findall(sent.lower()) if w not in STOPWORDS and len(w) > 2]
        if not words:
            continue

        # 1) Điểm tần suất từ (chuẩn hoá 0-1)
        freq_score = sum(freq[w] for w in words) / (len(words) * max_freq)

        # 2) Boost nếu câu chứa domain keyword (ammonia, silicon, xenobiology...)
        sent_lower = sent.lower()
        kw_hits = [k for k in domain_keywords if k in sent_lower]
        kw_score = min(len(kw_hits), 3) * keyword_boost
        matched_keywords.update(kw_hits)

        # 3) Boost nhẹ câu đầu văn bản (thường là câu định nghĩa/luận điểm)
        position_score = 1.0 if idx < 3 else (0.3 if idx < 8 else 0.0)

        total_score = freq_score + kw_score + position_score
        scored.append((idx, sent, total_score))

    # Top N theo điểm
    top = sorted(scored, key=lambda x: x[2], reverse=True)[:max_sentences]

    key_facts = [s for _, s, _ in top]  # đã sort theo điểm giảm dần
    summary_ordered = [s for _, s, _ in sorted(top, key=lambda x: x[0])]  # theo thứ tự gốc

    return {
        "summary": " ".join(summary_ordered),
        "key_facts": key_facts,
        "matched_keywords": sorted(matched_keywords),
    }
