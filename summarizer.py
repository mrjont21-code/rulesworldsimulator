"""
Extractive Summarizer — Thuần Python, Không LLM, Không ML
==========================================================
Kỹ thuật: Luhn's Algorithm (1958) cải tiến cho mục tiêu trích xuất
quy luật nhân quả khoa học.

Thay đổi so với phiên bản cũ:
- Tham số "domain_keywords" đổi tên thành "ontology_keywords" để phản
  ánh đúng nguồn từ khóa (SCIENCE_ONTOLOGY_KEYWORDS từ config.py).
- Bổ sung bộ đếm điểm riêng cho Cause-Effect Pattern Matching: câu chứa
  cấu trúc điều kiện (if/when/results in/leads to/due to/because/causes/
  enables/prevents/requires/therefore/thus...) được boost điểm cao hơn
  câu chứa từ khóa chủ đề thông thường.
  Lý do: câu nhân quả là nguyên liệu trực tiếp cho Rule Object theo
  schema Điều kiện → Biến đổi → Kết quả → Hiệu ứng phụ.
- Câu chỉ mô tả hình thái/thị giác thuần túy (không có cấu trúc nhân
  quả) vẫn có thể vào key_facts nhưng không được ưu tiên đứng đầu.

Output fields:
  summary          — top câu giữ thứ tự gốc, đọc liên tục
  key_facts        — top câu sắp theo điểm giảm dần (câu tốt nhất trước)
  matched_keywords — ontology_keywords nào xuất hiện trong text
  causal_sentences — câu được nhận diện có cấu trúc nhân quả (tách riêng
                     để T4/T5 dễ trích xuất Rule Object)

LƯU Ý MIGRATION: Nếu đổi tên field "matched_keywords" trong collection
MongoDB permanent.*, cần script migrate riêng — không đổi ngầm ở đây.
"""
import re
from collections import Counter

# Stopword tiếng Anh tối giản — đủ cho văn bản khoa học/wiki, không cần
# tải corpus nltk (tránh phụ thuộc network khi chạy trong GitHub Actions).
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

# Các marker cấu trúc nhân quả — dùng để nhận diện câu chứa quan hệ
# điều kiện/nguyên nhân/kết quả, không phải để match chủ đề.
# Đây là cầu nối tới Cause-Effect Engine (Mục XI) và Formula Engine
# (Mục VII: Điều kiện → Biến đổi → Kết quả → Hiệu ứng phụ).
CAUSAL_MARKERS = re.compile(
    r"\b("
    r"results?\s+in|leads?\s+to|due\s+to|caused?\s+by|because(\s+of)?|"
    r"as\s+a\s+(result|consequence)|therefore|thus|hence|"
    r"if\b.+\bthen\b|when\b.+\bthen\b|depends?\s+on|"
    r"enables?|prevents?|inhibits?|promotes?|requires?|"
    r"triggers?|accelerates?|decelerates?|modulates?|regulates?|"
    r"constrains?|amplifies?|attenuates?|correlates?\s+with|"
    r"threshold|sufficient\s+condition|necessary\s+condition"
    r")\b",
    re.IGNORECASE,
)


def _split_sentences(text: str) -> list[str]:
    text = re.sub(r'\s+', ' ', text.strip())
    if not text:
        return []
    raw = SENTENCE_SPLIT_RE.split(text)
    # Loại câu quá ngắn (thường là mảnh nav menu, "Read more", v.v.)
    return [s.strip() for s in raw if len(s.strip()) >= 40]


def _word_frequencies(sentences: list[str]) -> Counter:
    freq = Counter()
    for sent in sentences:
        for w in WORD_RE.findall(sent.lower()):
            if w not in STOPWORDS and len(w) > 2:
                freq[w] += 1
    return freq


def _has_causal_structure(sentence: str) -> bool:
    """Kiểm tra câu có chứa marker nhân quả không."""
    return bool(CAUSAL_MARKERS.search(sentence))


def extractive_summary(
    text: str,
    ontology_keywords: list[str] | None = None,
    max_sentences: int = 6,
    keyword_boost: float = 2.5,
    causal_boost: float = 3.5,
) -> dict:
    """Trích xuất câu quan trọng theo Luhn's Algorithm cải tiến.

    Parameters
    ----------
    text : str
        Văn bản thô cần tóm tắt.
    ontology_keywords : list[str] | None
        Từ điển từ khóa ontology (từ settings.SCIENCE_ONTOLOGY_KEYWORDS).
        Câu chứa từ khóa này được boost điểm.
    max_sentences : int
        Số câu tối đa trong output.
    keyword_boost : float
        Hệ số boost cho mỗi từ khóa ontology khớp trong câu.
    causal_boost : float
        Hệ số boost cho câu chứa cấu trúc nhân quả. Cao hơn keyword_boost
        vì câu nhân quả là nguyên liệu trực tiếp cho Rule Object.

    Returns
    -------
    dict với các field:
        summary          — top câu theo thứ tự gốc
        key_facts        — top câu theo điểm giảm dần
        matched_keywords — ontology keyword nào xuất hiện
        causal_sentences — câu có cấu trúc nhân quả (tách riêng cho T4/T5)
    """
    ontology_keywords = [k.lower() for k in (ontology_keywords or [])]
    sentences = _split_sentences(text)

    if not sentences:
        return {
            "summary": "",
            "key_facts": [],
            "matched_keywords": [],
            "causal_sentences": [],
        }

    if len(sentences) <= max_sentences:
        causal_sents = [s for s in sentences if _has_causal_structure(s)]
        return {
            "summary": " ".join(sentences),
            "key_facts": sentences,
            "matched_keywords": sorted({k for k in ontology_keywords if k in text.lower()}),
            "causal_sentences": causal_sents,
        }

    freq = _word_frequencies(sentences)
    if not freq:
        return {
            "summary": "",
            "key_facts": [],
            "matched_keywords": [],
            "causal_sentences": [],
        }

    max_freq = max(freq.values())
    matched_keywords: set[str] = set()
    causal_sentences: list[str] = []

    scored = []
    for idx, sent in enumerate(sentences):
        words = [
            w for w in WORD_RE.findall(sent.lower())
            if w not in STOPWORDS and len(w) > 2
        ]
        if not words:
            continue

        # 1) Điểm tần suất từ (chuẩn hóa 0–1)
        freq_score = sum(freq[w] for w in words) / (len(words) * max_freq)

        # 2) Boost nếu câu chứa ontology keyword
        sent_lower = sent.lower()
        kw_hits = [k for k in ontology_keywords if k in sent_lower]
        kw_score = min(len(kw_hits), 3) * keyword_boost
        matched_keywords.update(kw_hits)

        # 3) Boost cấu trúc nhân quả — quan trọng hơn keyword chủ đề
        #    vì câu nhân quả mã hóa quan hệ Nguyên nhân → Kết quả,
        #    là đơn vị cơ bản của Rule Object.
        causal_score = 0.0
        if _has_causal_structure(sent):
            causal_score = causal_boost
            causal_sentences.append(sent)

        # 4) Boost nhẹ câu đầu văn bản (thường là câu định nghĩa/luận điểm)
        position_score = 1.0 if idx < 3 else (0.3 if idx < 8 else 0.0)

        total_score = freq_score + kw_score + causal_score + position_score
        scored.append((idx, sent, total_score))

    # Top N theo điểm giảm dần
    top = sorted(scored, key=lambda x: x[2], reverse=True)[:max_sentences]

    key_facts = [s for _, s, _ in top]
    summary_ordered = [s for _, s, _ in sorted(top, key=lambda x: x[0])]

    return {
        "summary": " ".join(summary_ordered),
        "key_facts": key_facts,
        "matched_keywords": sorted(matched_keywords),
        "causal_sentences": causal_sentences,
    }
