# After-sales module

Hiện thực CUS-18 và ADM-18: yêu cầu trả hàng theo từng `ShopOrder`, item/evidence, seller
chấp thuận hoặc từ chối, customer leo thang và Admin quyết định hoàn toàn bộ, hoàn một phần
hoặc từ chối. Thời hạn mặc định là 7 ngày và có thể đổi bằng `SiteSetting` key
`returns.window_days`. Quyết định Admin được ghi vào `AuditLog`.

