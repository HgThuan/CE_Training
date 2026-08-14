---
version: 1
slug: "commerce-frontend-src-layouts-storefrontlayout-vue"
primary_target: "ecommerce/frontend/src/layouts/StorefrontLayout.vue"
related_targets: ["ecommerce/frontend/src/features/home/pages/HomePage.vue","ecommerce/frontend/src/features/product/pages/ProductListPage.vue","ecommerce/frontend/src/features/product/pages/ProductDetailPage.vue","ecommerce/frontend/src/features/checkout/CheckoutPage.vue","ecommerce/frontend/src/features/auth/pages/ProfilePage.vue"]
---

# Customer storefront redesign

- Scope: toàn bộ storefront công khai và khu vực Customer; mode chính Persuade ở Home, Operate ở catalog, checkout và account.
- Audience/job: khách Việt Nam mua điện tử, thời trang và hàng tiêu dùng; tìm nhanh, so sánh, săn ưu đãi và checkout tin cậy.
- Direction: Mercato Market Ledger. Composition được duyệt: `.impeccable/mocks/home-a.png`.
- Memorable moment: một “bàn tuyển chọn” đa ngành hàng dẫn thẳng vào category, deal và catalog bằng giá/ảnh rõ ràng.
- Constraints: giữ nguyên route/API/store/nghiệp vụ; không phát minh claim, giá hay dữ liệu; mobile đầy đủ; WCAG 2.2 AA.

## Implementation grammar

- Components: surface giấy khoáng sáng; field xanh chai; CTA cam hồng; nhãn giá vàng nghệ; icon outline Heroicons.
- Corners: 12px cho control/card, 16px cho panel, không dùng pill tràn lan.
- Lines/elevation: rule 1px xanh pha 14%; shadow mềm có offset; receipt dùng cạnh dashed/perforation tiết chế.
- Type: workhorse sans cho UI; serif display chỉ dùng cho tên Mercato và headline Home, không dùng cho form/data.
- Responsive: desktop header hai tầng; mobile header compact + bottom navigation; product grid 2/3/4 cột.

## Visible inventory

| Thành phần | Cam kết | Medium |
|---|---|---|
| Header | Logo, search/AI, wishlist/cart/account, trust/category rail | semantic Vue/HTML + Heroicons |
| Hero | Copy thật + CTA + ảnh banner/API; fallback vẫn có cấu trúc tuyển chọn | semantic HTML/CSS + API raster |
| Category strip | nhãn tuyến mua sắm, ảnh lỗi có fallback | Vue + API raster |
| Flash Sale | receipt band, countdown, giá sale/gốc đúng logic | Vue/CSS |
| Product card | ảnh dẫn, shop/tên/rating/giá/badge/action | shared Vue component |
| Checkout | receipt summary sticky và bước nhập rõ ràng | semantic Vue/HTML |
| Account | cùng shell, navigation rõ, form state đầy đủ | semantic Vue/HTML |
| Mobile nav | 5 tác vụ chính, vùng chạm ≥44px | Vue + Heroicons |
