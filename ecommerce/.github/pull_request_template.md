## 経緯/課題 | Context / Issue

<!-- Mô tả ngắn gọn bối cảnh và vấn đề cần giải quyết. Dán link issue/ticket nếu có. -->
<!-- Briefly describe the background and the problem being solved. Link to issue/ticket if available. -->

Closes #

---

## 対応内容 | Changes

<!-- Liệt kê những thay đổi chính đã thực hiện. -->
<!-- List the main changes made in this PR. -->

- 

---

## 未対応内容 及び そのタスク | Incomplete / Future tasks

<!-- Những gì chưa được xử lý trong PR này và lý do. Ghi rõ issue/ticket theo dõi nếu có. -->
<!-- What is NOT handled in this PR and why. Reference follow-up issues if applicable. -->

- [ ] 

---

## スクリーンショットまたはムービー | Screenshots or movies

<!-- Đính kèm ảnh chụp màn hình hoặc video demo. Xóa section này nếu không có thay đổi UI. -->
<!-- Attach screenshots or a demo video. Remove this section if there are no UI changes. -->

| Before | After |
|--------|-------|
| —      | —     |

---

## 水平展開 | Cross-coverage

<!-- Những component/module/endpoint khác có thể bị ảnh hưởng bởi thay đổi này không? -->
<!-- Are there other components, modules, or endpoints that might be affected by this change? -->

- [ ] Không có ảnh hưởng chéo / No cross-impact
- [ ] Đã kiểm tra / Checked:

---

## Checklist

### Code
- [ ] Code theo đúng coding standard (`ruff check`, `ruff format`, ESLint, Prettier pass)
- [ ] Không có `print()`, `console.log()`, `debugger` thừa
- [ ] Không có secret / credential hardcode

### Test
- [ ] Đã viết unit/integration test cho logic mới
- [ ] `pytest` pass (backend)
- [ ] `npm run test` pass (frontend)
- [ ] `npm run build` pass

### Database
- [ ] Migration đã tạo và đặt tên rõ ràng (nếu có thay đổi schema)
- [ ] Migration có thể rollback an toàn

### API & Docs
- [ ] OpenAPI schema còn hợp lệ (`python manage.py spectacular --validate`)
- [ ] Đã cập nhật `docs/` nếu có thay đổi nghiệp vụ hoặc API

### Security (bắt buộc với auth/payment/upload)
- [ ] Input đã được validate phía server
- [ ] Permission/ownership đã kiểm tra
- [ ] Không lộ thông tin nhạy cảm trong response/log
