# TODO — Việc cần làm trước khi vận hành

File này liệt kê toàn bộ việc Sếp cần làm để đưa hệ thống vào chạy thật,
cộng với những giới hạn/rủi ro đã biết mà em chưa tự xử lý được (cần
quyết định hoặc quyền truy cập của Sếp). Xem `README.md` để biết kiến trúc
tổng thể.

> Lưu ý: file này trước đây tên `readme.md` (chữ thường), đã đổi thành
> `TODO_HANDOFF.md` vì cùng thư mục với `README.md` — trên Windows/Mac
> (ổ đĩa không phân biệt hoa/thường) hai tên chỉ khác hoa/thường sẽ đè
> lên nhau khi giải nén, gây mất nội dung một trong hai file.

---

## 1. Bắt buộc trước khi chạy lần nào cũng được

- [ ] Tạo cluster MongoDB Atlas (free tier M0 là đủ), lấy connection string.
- [ ] Tạo ít nhất 1 API key Gemini tại Google AI Studio (khuyến nghị đủ 7 key để tận dụng xoay vòng).
- [ ] Vào **Settings → Secrets and variables → Actions** trên GitHub repo, thêm:
  - `MONGODB_URI`
  - `GEMINI_KEY_1` … `GEMINI_KEY_7` (thiếu key nào để trống secret đó cũng được, `settings.py` tự lọc key rỗng)
- [ ] Kiểm tra `.gitignore` đã loại trừ `data/` (tránh commit nhầm dữ liệu cào về).

## 2. Chạy Phần 1 — Baseline (chỉ 1 lần)

- [ ] Actions → **Harvest World Lore (Initial Run)** → Run workflow.
- [ ] Theo dõi 4 job: scrape (3 nguồn song song) → plan-batches → extract-batch (matrix) → finalize.
- [ ] Sau khi xong, vào MongoDB Atlas kiểm tra:
  - Collection `harvest_snapshot` có 1 document `_id: "world_lore_master"`.
  - Collection `biology_rules` có ~200-300 document.
  - Collection `harvest_state` — **sẽ chưa có gì** ở bước này vì Phần 1 không ghi state (state chỉ dùng cho Phần 2). Đây là hành vi đúng, không phải lỗi.
- [ ] Nếu job `extract-batch` bị lỗi 1-2 batch lẻ tẻ (rate limit tạm thời), chạy lại thủ công riêng batch đó bằng `python main.py --extract-batch <id>` cục bộ rồi upload thủ công, hoặc chạy lại toàn bộ Initial Run (idempotent nhờ dedup theo `rule_id`).

## 3. Kiểm thử Phần 2 — Incremental trước khi để cron tự chạy

- [ ] Chạy tay: Actions → **Harvest World Lore (Monthly Refresh - Phần 2)** → Run workflow (workflow_dispatch luôn được phép chạy, không cần đợi cuối tháng).
- [ ] Lần chạy tay đầu tiên sẽ coi mọi bài từ `2000-01-01` là "mới" (vì `harvest_state` chưa có `last_refresh_at`) → **sẽ cào gần như toàn bộ lại giống Phần 1**. Đây là hành vi đúng của lần đầu, nhưng tốn thời gian/quota tương đương Phần 1. Sếp cân nhắc: chạy Phần 2 lần đầu ngay sau Phần 1 trong cùng ngày để mốc thời gian còn sát, hoặc chấp nhận lần đầu tốn nhiều hơn.
- [ ] Sau lần chạy tay đó, kiểm tra `harvest_state.last_refresh_at` đã được set trong MongoDB.
- [ ] Chạy tay lần 2 ngay sau đó — lần này phải chỉ tìm thấy rất ít/không có bài mới (0 batch là bình thường), và job `finalize` vẫn chạy để xác nhận cập nhật `last_refresh_at`.
- [ ] Sau khi kiểm thử ổn, để cron `0 2 28-31 * *` tự chạy — không cần làm gì thêm.

## 4. Rủi ro/giới hạn đã biết (chưa tự xử lý được)

- [ ] **Project Rho không có API** — cơ chế incremental dùng content-hash cho *toàn trang*, nghĩa là chỉ cần 1 câu trong trang đổi là cào lại toàn bộ trang đó (không phải chỉ đoạn đổi). Chấp nhận được vì Project Rho chỉ có 4 trang cấu hình sẵn trong `settings.py`.
- [ ] **`touched` timestamp của MediaWiki** phản ánh lần sửa gần nhất của trang, không phân biệt sửa nhỏ (typo) hay sửa lớn (nội dung) — có thể incremental bắt cả những sửa không đáng kể. Không ảnh hưởng tính đúng đắn, chỉ ảnh hưởng hiệu suất nhẹ.
- [ ] Nếu Orion's Arm/Speculative Evo đổi cấu trúc category hoặc chặn bot (User-Agent), scraper sẽ âm thầm trả về danh sách rỗng — nên thỉnh thoảng xem log job `scrape` trong Actions để phát hiện sớm.
- [ ] Prompt trích xuất LLM (`processors/lore_extractor.py`) chưa được Sếp duyệt qua "1 ví dụ chạy thử" như thường lệ — khuyến nghị xem thử 5-10 rule đầu ra của Phần 1 trước khi tin tưởng chạy Phần 2 tự động dài hạn.
- [ ] Chưa có cơ chế cảnh báo (Slack/Telegram/email) khi workflow lỗi — hiện chỉ xem qua GitHub Actions UI. Có thể bổ sung nếu Sếp cần.

## 5. Đã dọn dẹp trong lần review này

- [x] Xoá thư mục rác `{.github/workflows,config,scrapers,processors,normalizer,storage,data}` (do lệnh `mkdir -p {...}` chạy sai shell).
- [x] Xoá `init.py` trùng lặp với `__init__.py` trong `scrapers/`, `normalizer/`, `storage/`.
- [x] Gộp `readme.md` cũ (bản sơ sài) vào `README.md` (bản đầy đủ v2.0 → nay là v3.0).
- [x] Thêm logic incremental thật sự cho Phần 2 (trước đó `harvest-monthly.yml` chỉ gọi lại y hệt Phần 1 mỗi tháng, không hề tiết kiệm tài nguyên như tài liệu chiến lược mô tả).

## 6. Đóng gói lần này (bản giao tiếp theo)

- [x] Đổi tên `readme.md` → `TODO_HANDOFF.md` (tránh xung đột với `README.md`
      khi giải nén trên Windows/Mac — hai tên chỉ khác hoa/thường sẽ đè lên
      nhau, mất nội dung 1 trong 2 file).
- [x] Sửa `README.md`: tên workflow trong tài liệu (`baseline_harvest.yml`,
      `monthly_refresh.yml`) không khớp tên file thật trong
      `.github/workflows/` (`harvest-initial.yml`, `harvest-monthly.yml`,
      `harvest-core.yml`). Cập nhật lại đúng tên + giải thích kiến trúc
      reusable workflow (`harvest-core.yml` chứa 4 job thật, 2 file kia chỉ
      là lớp vỏ chọn `mode`).
- [x] Rà soát toàn bộ mã nguồn (`main.py`, `scrapers/`, `processors/`,
      `normalizer/`, `storage/`, `config/settings.py`): biên dịch sạch, mọi
      hàm được gọi trong `main.py` đều tồn tại trong module tương ứng, không
      còn TODO/stub/placeholder nào sót lại trong code.
- [x] Kiểm tra `data/` rỗng, đúng như `.gitignore` mô tả.
