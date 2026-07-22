# Testing Strategy

Tài liệu định nghĩa chiến lược kiểm thử cho toàn dự án, cụ thể hóa `NFR-14` và mục Testing trong `CODING_STANDARDS.md` / `PROJECT_CONSTITUTION.md`.

---

## 1. Test Pyramid

```
                ▲
               /  \        E2E (ít nhất)
              / E2E \       — luồng checkout, đăng nhập, luồng seller duyệt sản phẩm
             /────────\
            /Integration\  Integration / API Test (vừa phải)
           /   / API Test \ — test từng endpoint qua DRF test client
          /────────────────\
         /   Unit Test       \  Unit Test (nhiều nhất)
        /______________________\ — Service, Selector, State Machine, Composable, Store
```

Nguyên tắc: viết nhiều unit test rẻ & nhanh cho logic nghiệp vụ (Service Layer), một lượng vừa phải integration test cho API quan trọng, và một số ít E2E test cho các luồng người dùng xuyên suốt quan trọng nhất.

---

## 2. Công cụ

| Tầng | Backend | Frontend |
|---|---|---|
| Unit test | `pytest` + `pytest-django` | `vitest` |
| Test data | `factory_boy` | fixture/mock data thủ công |
| API/Integration test | `pytest-django` + DRF `APIClient` | — |
| Component test | — | `@vue/test-utils` |
| E2E test (tùy chọn/điểm cộng) | `Playwright` hoặc `Cypress` | cùng công cụ |
| Coverage | `coverage.py` (`pytest-cov`) | `vitest --coverage` |
| Lint (chạy trước test trong CI) | `ruff` | `eslint` |

---

## 3. Mục tiêu độ phủ (Coverage Targets)

Theo NFR-14 và `CODING_STANDARDS.md` mục 14 — đây là **ràng buộc bắt buộc**, không phải gợi ý:

| Phạm vi | Độ phủ tối thiểu |
|---|---|
| Module core: Cart, Checkout/Order, Coupon/Promotion, Inventory | **≥ 60%** |
| Các module còn lại (Review, Chat, Notification, Report...) | Khuyến nghị ≥ 40%, không bắt buộc |
| AIService (logic retry/fallback/cache, không tính lời gọi provider thật) | Khuyến nghị ≥ 50% |

CI **fail** nếu coverage của module core giảm dưới ngưỡng khi có PR mới (đặt ngưỡng trong cấu hình `pytest-cov`/`vitest`).

---

## 4. Test theo từng tầng (Backend)

### 4.1 Unit Test — Service Layer

Mục tiêu: test logic nghiệp vụ độc lập với HTTP layer, dùng DB test (Django `TestCase`/`pytest.mark.django_db`).

```python
# apps/order/tests/test_order_service.py
import pytest
from apps.order.services import OrderService
from apps.order.exceptions import OutOfStockError
from tests.factories import ProductVariantFactory, CartFactory, AddressFactory

@pytest.mark.django_db
class TestOrderService:
    def test_create_orders_splits_by_shop(self):
        cart = CartFactory.with_items_from_two_shops()
        orders = OrderService.create_orders_from_cart(
            customer=cart.user, cart=cart, address=AddressFactory(),
            payment_method="cod", coupon_codes={},
        )
        assert len(orders) == 2  # BR-CART-02: 1 order / shop

    def test_create_orders_raises_when_out_of_stock(self):
        variant = ProductVariantFactory(stock=0)
        cart = CartFactory.with_item(variant=variant, quantity=1)
        with pytest.raises(OutOfStockError):
            OrderService.create_orders_from_cart(
                customer=cart.user, cart=cart, address=AddressFactory(),
                payment_method="cod", coupon_codes={},
            )
```

### 4.2 Unit Test — State Machine

```python
# apps/order/tests/test_order_state_machine.py
def test_cannot_skip_status(order_factory):
    order = order_factory(status=Order.Status.PENDING_CONFIRMATION)
    with pytest.raises(InvalidTransitionError):
        OrderStateMachine.transition(order, Order.Status.SHIPPING, actor=order.customer)  # nhảy cóc — phải fail

def test_cancel_restores_stock(order_factory, variant_factory):
    variant = variant_factory(stock=5)
    order = order_factory(status=Order.Status.PENDING_CONFIRMATION, items=[(variant, 2)])
    variant.refresh_from_db()
    assert variant.stock == 3  # đã trừ khi tạo đơn

    OrderStateMachine.transition(order, Order.Status.CANCELLED, actor=order.customer)
    variant.refresh_from_db()
    assert variant.stock == 5  # hoàn tồn kho — BR-ORD-04
```

### 4.3 Concurrency Test — Chống Oversell (BẮT BUỘC theo NFR-14)

Đây là test case **bắt buộc phải có** trong bộ test — mô phỏng nhiều request đồng thời trừ cùng một tồn kho.

```python
# apps/inventory/tests/test_concurrency.py
import threading
import pytest
from apps.inventory.repositories import StockRepository
from apps.inventory.exceptions import OutOfStockError
from tests.factories import ProductVariantFactory

@pytest.mark.django_db(transaction=True)  # cần transaction=True để test thật sự chạy đa luồng với DB
def test_concurrent_decrement_never_oversells():
    variant = ProductVariantFactory(stock=10)
    results = []

    def worker():
        try:
            StockRepository.decrement(
                variant.id, quantity=1, reference_type="Order", reference_id=1, performed_by=None,
            )
            results.append("ok")
        except OutOfStockError:
            results.append("out_of_stock")

    threads = [threading.Thread(target=worker) for _ in range(20)]  # 20 request cùng lúc, chỉ 10 tồn kho
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    variant.refresh_from_db()
    assert variant.stock == 0                       # không bao giờ âm (BR-INV-01)
    assert results.count("ok") == 10                  # đúng 10 request thành công
    assert results.count("out_of_stock") == 10          # 10 request còn lại bị từ chối, không "vượt rào"
```

### 4.4 API / Integration Test

```python
# apps/order/tests/test_checkout_api.py
@pytest.mark.django_db
class TestCheckoutAPI:
    def test_checkout_requires_authentication(self, api_client):
        response = api_client.post("/api/v1/checkout/confirm", {})
        assert response.status_code == 401

    def test_checkout_success_creates_orders_per_shop(self, authenticated_client, cart_with_two_shops):
        response = authenticated_client.post("/api/v1/checkout/confirm", {
            "address_id": cart_with_two_shops.address.id,
            "payment_method": "cod",
        })
        assert response.status_code == 200
        assert response.json()["success"] is True
        assert len(response.json()["data"]["orders"]) == 2
```

### 4.5 Permission / Isolation Test (BẮT BUỘC — xem `security.md` mục 2, 5)

```python
# apps/product/tests/test_seller_isolation.py
@pytest.mark.django_db
def test_seller_cannot_edit_other_shop_product(seller_a_client, product_of_seller_b):
    response = seller_a_client.patch(
        f"/api/v1/seller/products/{product_of_seller_b.id}", {"name": "Hacked"},
    )
    assert response.status_code in (403, 404)   # không được lộ là tồn tại hay không (404 an toàn hơn 403)

@pytest.mark.django_db
def test_customer_cannot_view_other_customer_order(customer_a_client, order_of_customer_b):
    response = customer_a_client.get(f"/api/v1/orders/{order_of_customer_b.id}")
    assert response.status_code in (403, 404)
```

---

## 5. Test theo từng tầng (Frontend)

### 5.1 Store Test

```typescript
// src/features/cart/store.spec.ts
import { setActivePinia, createPinia } from 'pinia'
import { useCartStore } from './store'
import { vi, describe, it, expect, beforeEach } from 'vitest'

describe('useCartStore', () => {
  beforeEach(() => setActivePinia(createPinia()))

  it('merges guest cart items on login without duplicating rows', async () => {
    const store = useCartStore()
    store.setGuestItems([{ variantId: 1, quantity: 2 }])
    await store.mergeIntoServerCart()
    expect(store.items.filter((i) => i.variantId === 1)).toHaveLength(1)
    expect(store.items.find((i) => i.variantId === 1)?.quantity).toBe(2)
  })
})
```

### 5.2 Component Test

```typescript
// src/features/product/components/ProductCard.spec.ts
import { mount } from '@vue/test-utils'
import ProductCard from './ProductCard.vue'

it('shows sale price when product is on flash sale', () => {
  const wrapper = mount(ProductCard, { props: { product: { price: 100000, salePrice: 79000 } } })
  expect(wrapper.text()).toContain('79.000')
  expect(wrapper.find('.original-price').classes()).toContain('line-through')
})
```

---

## 6. E2E Test (tùy chọn/điểm cộng — NFR-13/14)

Ưu tiên viết E2E cho các luồng có nhiều bước và nhiều rủi ro hồi quy (regression):

1. Đăng ký → xác thực email → đăng nhập
2. Tìm sản phẩm → thêm giỏ → checkout COD → xem đơn ở trạng thái "Chờ xác nhận"
3. Seller đăng nhập → xác nhận đơn → chuyển các trạng thái → Customer thấy timeline cập nhật
4. Seller tạo sản phẩm → Admin duyệt → sản phẩm xuất hiện ở trang tìm kiếm

Không bắt buộc phủ toàn bộ tính năng bằng E2E — chỉ các luồng lõi ở trên là đủ cho phạm vi đồ án.

---

## 7. Test Data & Factories

- Backend: dùng `factory_boy` để sinh dữ liệu test nhất quán, tránh lặp lại code tạo fixture ở nhiều file test.

```python
# tests/factories.py
class ProductVariantFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ProductVariant

    product = factory.SubFactory(ProductFactory)
    sku = factory.Sequence(lambda n: f"SKU-{n:05d}")
    price = 100000
    stock = 10
```

- Seed data cho demo (khác với test data): dùng Django management command riêng (`python manage.py seed_demo_data`), không tái sử dụng factory test cho việc này vì mục đích khác nhau (demo cần dữ liệu thực tế/đẹp, test cần dữ liệu tối giản có kiểm soát).

---

## 8. Tích hợp CI

Khớp `PROJECT_CONSTITUTION.md` mục 18.

```yaml
# .github/workflows/ci.yml (rút gọn)
jobs:
  backend:
    steps:
      - run: ruff check .
      - run: pytest --cov=apps --cov-report=term-missing --cov-fail-under=60 apps/order apps/cart apps/promotion apps/inventory
      - run: pytest apps  # toàn bộ test còn lại, không ép ngưỡng coverage cứng

  frontend:
    steps:
      - run: eslint .
      - run: vitest run --coverage
      - run: vite build
```

**Không merge vào `develop`/`main` khi bất kỳ job nào fail** (đã nêu ở `CODING_STANDARDS.md` mục 13).

---

## 9. Những gì KHÔNG cần test kỹ (để tập trung thời gian đúng chỗ)

Tránh lãng phí thời gian test những phần rủi ro thấp — ưu tiên thời gian cho mục 4.3–4.5 ở trên:
- CRUD đơn giản không có business logic (VD: CRUD thương hiệu) — 1 vài test smoke là đủ.
- Serializer chỉ map field 1-1 không có validate phức tạp.
- Style/CSS, animation.

## 10. Tài liệu liên quan

- `CODING_STANDARDS.md` mục 14 — quy chuẩn testing tổng quát.
- `security.md` mục 2, 5 — yêu cầu test phân quyền/isolation chi tiết hơn.
- `business_rules.md` — mỗi rule `BR-...` nên có ít nhất 1 test case tương ứng khi hiện thực.
- `ARCHITECTURE.md` mục 7 — lý do vì sao concurrency test (mục 4.3) là bắt buộc.
