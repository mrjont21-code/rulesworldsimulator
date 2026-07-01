# World Lore Harvester v2.0

Thu thập và chuẩn hóa **Quy luật sinh học giả tưởng** từ 3 nguồn, tự động hàng tháng qua GitHub Actions.

---

## Kiến trúc Pipeline

```
[Orion's Arm]  [Speculative Evo]  [Project Rho]
      ↓               ↓                 ↓
   Scrape          Scrape            Scrape
      └──────────────┴─────────────────┘
                      ↓
              raw_*.json (artifact)
                      ↓
         LLM Extract (7 key xoay vòng)
         gemini-2.5-flash, 15 article/batch
                      ↓
              extracted_batch_*.json
                      ↓
              Normalize + Dedup
                      ↓
           MongoDB Atlas (upsert)
           ┌──────────────────────┐
           │ harvest_snapshot     │ ← 1 document master
           │ biology_rules        │ ← per-rule (searchable)
           │ harvest_state        │ ← progress tracking
           └──────────────────────┘
```

---

## Cách hoạt động

### GitHub Actions (hàng tháng)

Workflow `harvest.yml` chạy tự động vào ngày 1 mỗi tháng:

1. **Job 1A/1B/1C** (song song): Cào 3 nguồn, ~5-10 phút mỗi job
2. **Job 2**: Tính số batches cần thiết
3. **Job 3** (matrix, tối đa 7 song song): LLM extraction, mỗi job ≤ 25 phút
4. **Job 4**: Normalize + upload MongoDB

**Chạy thủ công:**
> Actions → Harvest World Lore → Run workflow

---

## Thiết kế Free Tier Gemini

| Vấn đề | Giải pháp |
|--------|-----------|
| Rate limit 15 req/min/key | 7 key xoay vòng, delay 4s giữa calls |
| Quota hết giữa chừng | Cooldown per-key (65s), tự động chuyển key tiếp theo |
| Job > 25 phút | Mỗi batch chỉ 15 articles, time-check 22 phút |
| Key không hợp lệ | Cooldown 24h, không retry vô ích |
| Không dùng `say_hi()` | Mỗi article chỉ tốn 1 API call (không phải 2) |

**Model:** `gemini-2.5-flash` (free tier ổn định, không dùng pro/heavy)

---

## MongoDB - Chiến lược lưu trữ

**1 document master** trong collection `harvest_snapshot`:
```json
{
  "_id": "world_lore_master",
  "metadata": {
    "total_rules": 287,
    "run_count": 5,
    "last_updated": "2025-02-01T02:45:00Z"
  },
  "rules": [ ... ]
}
```

- Mỗi lần chạy **merge** rules mới vào document này (không ghi đè)
- Collection `biology_rules`: mỗi rule 1 document riêng, upsert by `rule_id`
- Index: `rule_id` (unique), `categories`, `source`, `quality_score`

---

## Secrets cần cấu hình

Vào **Settings → Secrets and variables → Actions**:

| Secret | Giá trị |
|--------|---------|
| `GEMINI_KEY_1` đến `GEMINI_KEY_7` | API keys từ Google AI Studio |
| `MONGODB_URI` | `mongodb+srv://user:pass@cluster.mongodb.net/` |

Tối thiểu cần 1 GEMINI_KEY. Càng nhiều key → throughput càng cao.

---

## Chạy cục bộ

```bash
pip install -r requirements.txt

# Scrape từng nguồn
python main.py --scrape orions_arm
python main.py --scrape spec_evo
python main.py --scrape project_rho

# Kiểm tra số batches
python main.py --count-batches

# Extract batch (cần GEMINI_KEY_1 trong env)
export GEMINI_KEY_1="AIza..."
python main.py --extract-batch 0
python main.py --extract-batch 1
# ...

# Finalize (cần MONGODB_URI trong env)
export MONGODB_URI="mongodb+srv://..."
python main.py --finalize
```

---

## Cấu trúc thư mục

```
rulesworldsimulator/
├── .github/workflows/
│   └── harvest.yml          # GitHub Actions workflow
├── config/
│   └── settings.py          # Cấu hình tập trung
├── scrapers/
│   ├── orions_arm.py        # MediaWiki API scraper
│   ├── speculative_evo.py   # Fandom API scraper
│   └── project_rho.py       # HTML scraper
├── processors/
│   ├── gemini_rotator.py    # Key rotation + rate limit
│   └── lore_extractor.py    # LLM extraction logic
├── normalizer/
│   └── json_builder.py      # Dedup + categorize + package
├── storage/
│   └── mongo_uploader.py    # MongoDB upsert + state
├── main.py                  # Entry point
└── requirements.txt
```

---

## Output JSON mỗi rule

```json
{
  "rule_id": "rule_a1b2c3d4e5",
  "rule_type": "silicon_based_life",
  "source": "orions_arm",
  "source_title": "Silicon-Based Life Forms",
  "source_url": "https://orionsarm.com/wiki/...",
  "quality_score": 0.85,
  "categories": ["body_composition", "respiration", "habitat"],
  "parameters": {
    "body_composition": "silicon-oxygen polymers",
    "breathes": ["fluorine", "sulfur dioxide"],
    "temperature_range": {"min": 200, "max": 800, "unit": "celsius"},
    "pressure_range": {"min": 5, "max": 50, "unit": "atm"},
    "gravity_tolerance": {"min": 0.5, "max": 3.0, "unit": "g"},
    "solvent": "liquid sulfuric acid",
    "energy_source": ["geothermal", "chemical reduction"],
    "weaknesses": ["water", "oxygen", "temperatures below 200°C"],
    "habitat": "volcanic planet surfaces, high-pressure gas giants",
    "reproduction": "binary fission via crystalline budding",
    "diet": "mineral oxidation, sulfur compounds"
  },
  "narrative_potential": {
    "conflict_types": ["incompatible atmosphere with carbon life", "..."],
    "story_hooks": ["First contact misunderstanding", "..."],
    "humor_potential": ["Water is literally toxic to them", "..."]
  },
  "confidence": 0.85,
  "batch_id": 3
}
```
