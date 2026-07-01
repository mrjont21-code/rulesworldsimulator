# World Lore Harvester v3.0

Thu thập và chuẩn hóa **Quy luật sinh học giả tưởng** từ 3 nguồn, theo chiến lược 2 giai đoạn:
Phần 1 cào nền tảng một lần, Phần 2 cập nhật gia tăng hàng tháng qua GitHub Actions.

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

## Cách hoạt động — 2 workflow riêng biệt

### 1. `harvest-initial.yml` — Phần 1, chạy MỘT LẦN

Chỉ trigger thủ công (`workflow_dispatch`). Cào toàn bộ ~1000-2000 bài từ 3 nguồn,
tạo "bộ gen gốc" ~200-300 quy luật. Chạy đúng 1 lần khi khởi động dự án.

1. **Job `scrape`** (matrix 3 nguồn song song): ~5-10 phút mỗi job
2. **Job `count_batches`**: tính số batches LLM cần thiết
3. **Job `extract`** (matrix, tối đa 7 song song): LLM extraction, mỗi job ≤ 25 phút
4. **Job `finalize`**: normalize + upload MongoDB

> Actions → Harvest World Lore (Initial Run) → Run workflow

### 2. `harvest-monthly.yml` — Phần 2, chạy định kỳ

Tự động vào ngày cuối mỗi tháng (`cron: 0 2 28-31 * *`, có job `check_last_day`
lọc lại để chỉ chạy đúng ngày cuối tháng thật). Chỉ cào bài **mới/thay đổi**
kể từ lần refresh trước — dùng `touched` timestamp (Orion's Arm, Speculative
Evo) hoặc content-hash (Project Rho, vì không có API). State lưu trong
MongoDB collection `harvest_state`.

1. **Job `check_last_day`**: chặn cron chạy sai ngày (chạy tay thì luôn cho phép)
2. **Job `scrape_recent`** (matrix 3 nguồn): chỉ lấy nội dung mới
3. **Job `count_batches`** / **Job `extract`**: giống Phần 1 nhưng dữ liệu nhỏ hơn nhiều
4. **Job `finalize`**: merge vào MongoDB + cập nhật `last_refresh_at`

> Actions → Harvest World Lore (Monthly Refresh - Phần 2) → Run workflow (để chạy ngay, không cần đợi cuối tháng)

`harvest-initial.yml` và `harvest-monthly.yml` chỉ là lớp vỏ mỏng (chọn `mode: full`
hoặc `mode: incremental`) gọi vào workflow tái sử dụng `harvest-core.yml`, nơi
chứa toàn bộ 4 job thật sự (scrape → plan-batches → extract-batch → finalize).
Việc này tránh lặp code giữa 2 workflow.

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

### Phần 1 — Baseline (1 lần)

```bash
pip install -r requirements.txt

python main.py --scrape orions_arm
python main.py --scrape spec_evo
python main.py --scrape project_rho

python main.py --count-batches

export GEMINI_KEY_1="AIza..."
python main.py --extract-batch 0
python main.py --extract-batch 1
# ...

export MONGODB_URI="mongodb+srv://..."
python main.py --finalize
```

### Phần 2 — Monthly refresh (chạy lại bất cứ lúc nào)

```bash
export MONGODB_URI="mongodb+srv://..."

python main.py --scrape-recent orions_arm
python main.py --scrape-recent spec_evo
python main.py --scrape-recent project_rho

python main.py --count-batches --prefix incr

export GEMINI_KEY_1="AIza..."
python main.py --extract-batch 0 --prefix incr

python main.py --finalize --update-state
```

---

## Cấu trúc thư mục

```
rulesworldsimulator/
├── .github/workflows/
│   ├── harvest-initial.yml  # Phần 1 - chạy 1 lần (thủ công), gọi harvest-core.yml
│   ├── harvest-monthly.yml  # Phần 2 - cron cuối tháng + chạy tay, gọi harvest-core.yml
│   └── harvest-core.yml     # Workflow tái sử dụng chứa 4 job thật (scrape/plan/extract/finalize)
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
