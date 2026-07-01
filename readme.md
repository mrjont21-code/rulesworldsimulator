# World Lore Harvester

Thu thập và chuẩn hóa dữ liệu "Quy luật sinh tồn" giả tưởng từ 3 nguồn:
- Orion's Arm (MediaWiki API)
- Speculative Evolution (Fandom API)
- Project Rho (HTML scraping)

## Cách hoạt động

1. **Scrape** bài viết thô từ 3 nguồn
2. **LLM** (7 Gemini keys xoay vòng) trích xuất quy luật sinh học
3. **Chuẩn hóa** thành JSON tinh gọn
4. **Upload** vào MongoDB Atlas

## Secrets cần cấu hình

- GEMINI_KEY_1 đến GEMINI_KEY_7
- MONGODB_URI

## Chạy thủ công

Vào Actions -> Harvest World Lore -> Run workflow
