# AI Rules

Nguồn: `PROJECT_CONSTITUTION.md` mục 7 & 27, `CODING_STANDARDS.md` mục 16, `ARCHITECTURE.md` mục 6, `api_design.md` mục 10, `database_design.md` mục 9 (nhóm AI).

File này gồm hai phần độc lập, đừng nhầm lẫn:

- **Phần A** — quy tắc hành xử khi **dùng AI để sinh code** cho dự án (áp dụng cho Claude/Copilot/... khi hỗ trợ lập trình).
- **Phần B** — quy tắc kỹ thuật của **tầng `AIService`**, tức tính năng AI *là một phần của sản phẩm* (smart search, chatbot, tóm tắt, gợi ý...).

---

## Phần A — Quy tắc khi AI hỗ trợ sinh code

Áp dụng cho mọi lần AI viết/sửa code trong dự án này:

1. **Giải thích trước khi viết** — nêu cách tiếp cận, không nhảy thẳng vào code.
2. **Giải thích sau khi viết** — tóm tắt logic, quyết định thiết kế, các case đã xử lý.
3. **Không bỏ qua bước phân tích yêu cầu.**
4. **Không viết toàn bộ business logic trong View/component trang** — luôn đẩy xuống Service Layer (BE) hoặc composable/store (FE).
5. **Tuân thủ kiến trúc đã định nghĩa** ở `ARCHITECTURE.md` — không tự ý đổi cấu trúc thư mục, pattern, hay layer.
6. **Ưu tiên khả năng mở rộng** (Open-Closed) — tránh code kiểu `if provider == "x"` lặp lại, ưu tiên interface/strategy khi có nhiều biến thể cùng loại (payment provider, AI provider...).
7. **Nếu có nhiều phương án khả thi, phải so sánh ưu/nhược điểm rồi mới chọn**, nêu rõ lý do chọn phương án cuối.
8. **Chủ động đề xuất cải tiến** nếu phát hiện thiết kế hiện tại (kể cả thiết kế đã được yêu cầu làm theo) chưa hợp lý — không im lặng làm sai theo yêu cầu nếu biết rõ hậu quả.
9. Không dùng Design Pattern chỉ để "cho giống người ta" (KISS) — chỉ dùng khi thật sự cần.
10. Mọi task chỉ được coi là xong khi khớp Definition of Done ở `system_prompt.md` mục 5.

---

## Phần B — Kiến trúc & quy tắc bắt buộc của `AIService`

### B.1 Nguyên tắc tổng thể

```
View / Consumer  (không bao giờ gọi thẳng provider)
      ↓
AIService   ← tầng DUY NHẤT được phép gọi ra provider bên ngoài
      ↓
Provider interface (provider-agnostic)
      ├── OpenAIProvider
      ├── ClaudeProvider
      └── GeminiProvider
```

Đổi provider chỉ cần đổi implementation, không đổi code gọi ở nơi khác (khớp AI-15, provider-agnostic).

### B.2 Yêu cầu bắt buộc đối với `AIService` (không phải tùy chọn)

| # | Yêu cầu | Ghi chú |
|---|---|---|
| 1 | **Retry & timeout** | Mọi lời gọi provider phải có timeout + retry có backoff. |
| 2 | **Đếm token & chi phí** | Ghi số token input/output và chi phí ước tính mỗi lần gọi. |
| 3 | **Log prompt/response** | Lưu vào bảng `AIRequestLog` (model, prompt, response, token, latency, lỗi) — phục vụ debug & báo cáo. |
| 4 | **Cache kết quả** | Với tác vụ không đổi theo thời gian thực (tóm tắt mô tả, tóm tắt review): cache theo hash nội dung, tránh gọi lại thừa. |
| 5 | **Fallback khi provider lỗi** | Degrade gracefully — VD: ẩn khối gợi ý AI, KHÔNG để lỗi AI làm sập luồng nghiệp vụ chính (checkout, xem sản phẩm vẫn phải chạy được dù AI service down). |
| 6 | **Tính số bằng SQL trước** | Với AI Sales Analytics (AI-14): tính số liệu bằng SQL trước, chỉ đưa số đã tính sẵn vào prompt để LLM diễn giải — không để LLM tự tính toán số. |
| 7 | **Gắn nhãn nội dung AI sinh** | Mọi nội dung AI hiển thị cho người dùng cuối phải có nhãn rõ ràng, VD "Tạo bởi AI" (AI-07). |
| 8 | **Feature flag** | Tính năng AI nên bật/tắt được qua `SiteSetting` (key-value, có cache) mà không cần deploy lại — giảm rủi ro khi AI lỗi/tốn chi phí bất thường (ADM-26). |

### B.3 Các bảng dữ liệu liên quan (`database_design.md` mục 9)

- `AIRequestLog` (AI-15) — log mọi lời gọi provider.
- `ProductEmbedding` (AI-02) — embeddings cho semantic search.
- `ProductAISummary` (AI-07, AI-08) — cache kết quả tóm tắt.
- `ProductTranslation` (AI-12) — bản dịch lưu bảng riêng, **không ghi đè** bản gốc, giữ nguyên format HTML/rich-text.

### B.4 Danh sách endpoint AI (`api_design.md` mục 10, base `/api/v1/ai`)

| Endpoint | Auth | Mã YC | Mô tả |
|---|---|---|---|
| `GET /ai/smart-search` | Public | AI-01 | Tìm kiếm theo nhu cầu tự nhiên |
| `GET /ai/semantic-search` | Public | AI-02 | Semantic search bằng embeddings |
| `GET /products/{id}/recommendations` | Public/Owner | AI-03 | Gợi ý cá nhân hóa |
| `GET /products/{id}/similar` | Public | AI-04 | Sản phẩm tương tự |
| `POST /ai/assistant/chat` | Owner (Customer) | AI-05 | AI Shopping Assistant (stream SSE/WS) |
| `POST /ai/support/auto-reply` | Nội bộ | AI-06 | Tự động trả lời trong chat |
| `GET /products/{id}/ai-review-summary` | Public | AI-07 | Tóm tắt AI từ đánh giá |
| `GET /products/{id}/ai-summary` | Public | AI-08 | Tóm tắt nhanh mô tả sản phẩm |
| `POST /ai/compare` | Public | AI-09 | So sánh 2-4 sản phẩm |
| `POST /seller/ai/generate-description` | Seller | AI-10 | Sinh tiêu đề/mô tả/SEO |
| `POST /seller/ai/auto-tag` | Seller | AI-11 | Đề xuất tag/danh mục/từ khóa |
| `POST /seller/products/{id}/ai/translate` | Seller | AI-12 | Dịch mô tả sản phẩm |
| `GET /seller/products/{id}/ai/price-suggestion` | Seller | AI-13 | Đề xuất khoảng giá bán |
| `GET /admin/ai/sales-analytics` | Admin | AI-14 | Nhận định AI — dashboard Admin |
| `GET /seller/ai/sales-analytics` | Seller | AI-14 | Nhận định AI — dashboard Seller |

Ghi chú thiết kế: endpoint AI nên có timeout ngắn ở tầng gateway/Nginx và luôn có phản hồi fallback nếu `AIService` lỗi — không để request treo (`api_design.md` mục 13).

### B.5 Mẫu code tham khảo

Pattern cụ thể (provider interface, `AIService`, exception handling) nằm ở `coding_patterns.md` mục 5 — "Backend — AI Provider Pattern". Tham khảo trước khi hiện thực để giữ nhất quán.

### B.6 Tài liệu liên quan

- `ARCHITECTURE.md` mục 6 — sơ đồ kiến trúc AI.
- `PROJECT_CONSTITUTION.md` mục 7 — nguồn gốc các yêu cầu bắt buộc ở Phần B.2.
- `database_design.md` mục 9 — schema chi tiết nhóm AI.
- `api_design.md` mục 10 — hợp đồng API AI đầy đủ.
- `feature_checklist.md` — trạng thái/độ ưu tiên từng mã AI-xx.
