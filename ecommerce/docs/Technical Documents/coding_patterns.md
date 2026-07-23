# Coding Patterns

Tài liệu này đưa ra **code mẫu cụ thể** cho các pattern đã nêu ở `ARCHITECTURE.md` và `CODING_STANDARDS.md`. Mục tiêu: khi một thành viên (hoặc AI) bắt đầu code một module mới, có ngay khuôn mẫu để copy và điều chỉnh, tránh mỗi người viết Service Layer/Repository theo một kiểu khác nhau.

---

## 1. Backend — Service Layer Pattern

**Nguyên tắc:** View chỉ điều phối (nhận request, gọi service, trả response). Toàn bộ business logic nằm ở `services.py`.

```python
# apps/order/services.py
from django.db import transaction
from apps.inventory.services import StockService
from apps.promotion.services import CouponService
from .models import Order, OrderItem
from .exceptions import OutOfStockError

class OrderService:
    """Toàn bộ logic tạo/thay đổi Order đi qua đây — View không được tự ý update model."""

    @staticmethod
    @transaction.atomic
    def create_orders_from_cart(*, customer, cart, address, payment_method, coupon_codes: dict) -> list[Order]:
        orders = []
        for shop_id, items in cart.group_by_shop().items():
            # 1. Kiểm tra lại tồn kho ngay trước khi trừ (BR-CART-03/04)
            StockService.assert_available(items)

            # 2. Trừ tồn kho có khóa dòng (BR-INV-01, ARCHITECTURE.md mục 7)
            StockService.decrement_for_order(items)

            # 3. Áp voucher (nếu có) cho shop này
            discount = CouponService.apply(
                platform_code=coupon_codes.get("platform"),
                shop_code=coupon_codes.get(f"shop_{shop_id}"),
                shop_id=shop_id,
                items=items,
            )

            # 4. Tạo Order + OrderItem (snapshot giá/tên tại thời điểm mua)
            order = Order.objects.create(
                customer=customer,
                shop_id=shop_id,
                address_snapshot=address.to_snapshot(),
                payment_method=payment_method,
                subtotal=items.subtotal(),
                platform_discount=discount.platform_amount,
                shop_discount=discount.shop_amount,
                total_amount=items.subtotal() - discount.total_amount,
                status=Order.Status.PENDING_CONFIRMATION,
            )
            OrderItem.objects.bulk_create(items.to_order_items(order))
            orders.append(order)

        return orders
```

```python
# apps/order/views.py
class CheckoutConfirmView(APIView):
    def post(self, request):
        serializer = CheckoutConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            orders = OrderService.create_orders_from_cart(
                customer=request.user,
                cart=Cart.objects.get(user=request.user),
                **serializer.validated_data,
            )
        except OutOfStockError as e:
            return error_response(message="Một số sản phẩm trong giỏ đã hết hàng", errors=e.details)

        return success_response(data=OrderSummarySerializer(orders, many=True).data)
```

Nhận xét: View **không** chứa vòng lặp theo shop, không gọi ORM trực tiếp để trừ tồn kho — tất cả nằm trong `OrderService`.

---

## 2. Backend — Repository / Selector Pattern

Tách truy vấn phức tạp ra khỏi service, đặc biệt các query chỉ đọc (selector) và query có logic tái sử dụng nhiều nơi (repository).

```python
# apps/product/selectors.py
class ProductSelector:
    """Chỉ đọc dữ liệu — không có side effect. Dùng cho các API list/detail."""

    @staticmethod
    def public_queryset():
        return Product.objects.filter(
            status=Product.Status.APPROVED,
            is_hidden=False,
            is_deleted=False,
        ).select_related("shop", "brand", "category").prefetch_related("media", "variants")

    @staticmethod
    def for_seller(seller_user):
        # BR-SHOP-04: luôn scope theo shop của seller đang đăng nhập
        return Product.objects.filter(shop__seller_id=seller_user.id, is_deleted=False)
```

```python
# apps/inventory/repositories.py
class StockRepository:
    """Đóng gói thao tác ghi dữ liệu tồn kho — nơi DUY NHẤT được UPDATE cột stock."""

    @staticmethod
    def decrement(variant_id: int, quantity: int, *, reference_type: str, reference_id: int, performed_by):
        with transaction.atomic():
            variant = ProductVariant.objects.select_for_update().get(id=variant_id)
            if variant.stock < quantity:
                raise OutOfStockError(variant_id=variant_id, available=variant.stock)
            variant.stock = F("stock") - quantity
            variant.save(update_fields=["stock"])
            variant.refresh_from_db(fields=["stock"])

            StockMovement.objects.create(
                variant=variant,
                movement_type=StockMovement.Type.SALE,
                quantity=-quantity,
                balance_after=variant.stock,
                reference_type=reference_type,
                reference_id=reference_id,
                performed_by=performed_by,
            )
```

Đây chính là cách hiện thực rule **BR-INV-01/03** và `ARCHITECTURE.md` mục 7 bằng code thật.

---

## 3. Backend — Multi-tenant Scoping Pattern

Không bao giờ tin `shop_id` từ client. Luôn lấy từ `request.user`.

```python
# apps/product/permissions.py
class IsShopOwner(BasePermission):
    """Object-level permission — chặn Seller A sửa dữ liệu Seller B (BR-SHOP-04)."""

    def has_object_permission(self, request, view, obj):
        return obj.shop.seller_id == request.user.id
```

```python
# apps/product/views.py — SAI (không làm thế này)
def list(self, request):
    shop_id = request.query_params.get("shop_id")   # ❌ tin client
    return Product.objects.filter(shop_id=shop_id)

# apps/product/views.py — ĐÚNG
class SellerProductViewSet(ModelViewSet):
    permission_classes = [IsAuthenticated, IsSeller]

    def get_queryset(self):
        return ProductSelector.for_seller(self.request.user)   # ✔ luôn theo user đăng nhập
```

---

## 4. Backend — State Machine Pattern (Order Status)

Không cho phép chuyển trạng thái tùy tiện — dùng bảng chuyển hợp lệ tập trung một chỗ (khớp `workflows.md` mục 1, BR-ORD-03).

```python
# apps/order/state_machine.py
class OrderStateMachine:
    TRANSITIONS = {
        Order.Status.PENDING_CONFIRMATION: {Order.Status.CONFIRMED, Order.Status.CANCELLED},
        Order.Status.CONFIRMED: {Order.Status.PACKING},
        Order.Status.PACKING: {Order.Status.SHIPPING},
        Order.Status.SHIPPING: {Order.Status.COMPLETED},
        Order.Status.COMPLETED: set(),
        Order.Status.CANCELLED: set(),
    }

    @classmethod
    @transaction.atomic
    def transition(cls, order: Order, to_status: str, *, actor, note: str = ""):
        allowed = cls.TRANSITIONS.get(order.status, set())
        if to_status not in allowed:
            raise InvalidTransitionError(f"Không thể chuyển từ {order.status} sang {to_status}")

        from_status = order.status
        order.status = to_status
        order.save(update_fields=["status", "updated_at"])

        OrderStatusHistory.objects.create(
            order=order, from_status=from_status, to_status=to_status,
            changed_by=actor, note=note,
        )

        if to_status == Order.Status.CANCELLED:
            StockService.restore_for_order(order)
            CouponService.restore_usage(order)

        NotificationService.notify_order_status_changed(order)
```

Mọi nơi muốn đổi trạng thái đơn **phải** gọi `OrderStateMachine.transition(...)` — không có view/service nào khác được `order.status = ...` trực tiếp.

---

## 5. Backend — AI Provider Pattern

Khớp `ARCHITECTURE.md` mục 6. Interface chung + implementation cho từng provider.

```python
# apps/ai_service/providers/base.py
class AIProvider(ABC):
    @abstractmethod
    def complete(self, *, system: str, messages: list[dict], tools: list[dict] | None = None) -> AIResponse:
        ...

# apps/ai_service/providers/claude_provider.py
class ClaudeProvider(AIProvider):
    def complete(self, *, system, messages, tools=None):
        response = self._client.messages.create(
            model=settings.AI_MODEL, system=system, messages=messages, tools=tools, max_tokens=1024,
        )
        return AIResponse.from_claude(response)

# apps/ai_service/service.py
class AIService:
    """Điểm gọi DUY NHẤT ra AI provider — View/Service khác không được import provider trực tiếp."""

    def __init__(self, provider: AIProvider | None = None):
        self._provider = provider or get_default_provider()

    def generate_product_description(self, *, product_name: str, keywords: list[str]) -> dict:
        cache_key = f"ai:desc:{hash((product_name, tuple(keywords)))}"
        if cached := cache.get(cache_key):
            return cached

        try:
            response = self._call_with_retry(
                system=PRODUCT_DESCRIPTION_PROMPT,
                messages=[{"role": "user", "content": f"Tên: {product_name}. Từ khóa: {keywords}"}],
            )
        except AIProviderError:
            logger.exception("AI provider failed for generate_product_description")
            return {"title": product_name, "description": "", "meta_description": "", "ai_generated": False}

        result = json.loads(response.text)
        result["ai_generated"] = True
        cache.set(cache_key, result, timeout=3600)
        return result

    def _call_with_retry(self, **kwargs) -> AIResponse:
        start = time.monotonic()
        try:
            response = retry(stop=stop_after_attempt(3), wait=wait_exponential())(self._provider.complete)(**kwargs)
        except Exception as e:
            AIRequestLog.objects.create(status="error", error_message=str(e), **kwargs_for_log(kwargs))
            raise AIProviderError from e

        AIRequestLog.objects.create(
            status="success", latency_ms=int((time.monotonic() - start) * 1000),
            input_tokens=response.input_tokens, output_tokens=response.output_tokens,
            **kwargs_for_log(kwargs),
        )
        return response
```

Điểm mấu chốt: lỗi provider **không** raise ra tới View — `generate_product_description` luôn trả về một dict hợp lệ (fallback `ai_generated: False`), khớp BR-AI-05.

---

## 6. Backend — Response & Error Handling Pattern

```python
# apps/common/responses.py
def success_response(data=None, message="Thành công", meta=None, status=200):
    payload = {"success": True, "message": message, "data": data}
    if meta:
        payload["meta"] = meta
    return Response(payload, status=status)

def error_response(message="Có lỗi xảy ra", errors=None, status=400):
    return Response({"success": False, "message": message, "errors": errors or {}}, status=status)
```

```python
# apps/common/exception_handler.py — DRF custom exception handler
def custom_exception_handler(exc, context):
    if isinstance(exc, BusinessError):
        return error_response(message=str(exc), errors=exc.errors, status=exc.http_status)

    response = drf_exception_handler(exc, context)
    if response is not None:
        return error_response(message=_default_message_for(exc), errors=response.data, status=response.status_code)

    logger.exception("Unhandled exception", extra={"request_id": context["request"].request_id})
    return error_response(message="Đã có lỗi hệ thống xảy ra", status=500)
```

---

## 7. Frontend — API Layer Pattern

```typescript
// src/shared/lib/http.ts
export const http = axios.create({ baseURL: import.meta.env.VITE_API_BASE_URL })

http.interceptors.response.use(
  (res) => res,
  async (error) => {
    if (error.response?.status === 401 && !error.config._retry) {
      error.config._retry = true
      await useAuthStore().refreshAccessToken()
      error.config.headers.Authorization = `Bearer ${useAuthStore().accessToken}`
      return http(error.config)
    }
    return Promise.reject(error)
  },
)
```

```typescript
// src/features/product/api.ts — điểm DUY NHẤT của feature product gọi HTTP
import { http } from '@/shared/lib/http'
import type { Product, ProductListParams } from './types'

export const productApi = {
  list: (params: ProductListParams) =>
    http.get<ApiResponse<Product[]>>('/products', { params }),
  detail: (slug: string) =>
    http.get<ApiResponse<Product>>(`/products/${slug}`),
}
```

```typescript
// src/features/product/store.ts
export const useProductStore = defineStore('product', () => {
  const products = ref<Product[]>([])
  const meta = ref<PaginationMeta | null>(null)
  const isLoading = ref(false)

  async function fetchProducts(params: ProductListParams) {
    isLoading.value = true
    try {
      const { data } = await productApi.list(params)
      products.value = data.data
      meta.value = data.meta ?? null
    } finally {
      isLoading.value = false
    }
  }

  return { products, meta, isLoading, fetchProducts }
})
```

```vue
<!-- src/features/product/components/ProductListPage.vue -->
<script setup lang="ts">
// Component chỉ gọi store — KHÔNG import axios/productApi trực tiếp
import { useProductStore } from '../store'
const store = useProductStore()
onMounted(() => store.fetchProducts({ page: 1 }))
</script>
```

---

## 8. Frontend — Composable Pattern (WebSocket / Chat)

```typescript
// src/features/chat/composables/useConversationSocket.ts
export function useConversationSocket(conversationId: number) {
  const messages = ref<Message[]>([])
  const authStore = useAuthStore()
  let socket: WebSocket | null = null

  function connect() {
    socket = new WebSocket(
      `${WS_BASE_URL}/chat/${conversationId}?token=${authStore.accessToken}`,
    )
    socket.onmessage = (event) => messages.value.push(JSON.parse(event.data))
    socket.onclose = () => scheduleReconnect()
  }

  function send(content: string) {
    socket?.send(JSON.stringify({ type: 'text', content }))
  }

  onMounted(connect)
  onUnmounted(() => socket?.close())

  return { messages, send }
}
```

Logic realtime nằm trọn trong composable — component chỉ gọi `useConversationSocket(id)` và render `messages`.

---

## 9. Naming & File Pattern Cheatsheet

| Tình huống | Pattern áp dụng | File |
|---|---|---|
| Business logic ghi dữ liệu | Service | `services.py` |
| Query đọc phức tạp, tái sử dụng | Selector | `selectors.py` |
| Query ghi có logic riêng (VD: stock) | Repository | `repositories.py` |
| Kiểm tra quyền theo object | Permission class | `permissions.py` |
| Luồng nhiều bước có trạng thái | State Machine | `state_machine.py` |
| Gọi dịch vụ ngoài (AI, Payment) | Provider + Service wrapper | `providers/`, `service.py` |
| Tác vụ chạy nền | Celery task, gọi Service bên trong | `tasks.py` |
| FE gọi API | `api.ts` theo feature | `features/<name>/api.ts` |
| FE state dùng chung | Pinia store | `features/<name>/store.ts` |
| FE logic tái sử dụng có side-effect (socket, timer) | Composable | `features/<name>/composables/` |

## 10. Tài liệu liên quan

- `ARCHITECTURE.md` — bối cảnh kiến trúc mà các pattern này hiện thực.
- `CODING_STANDARDS.md` — quy chuẩn naming/response format áp dụng trong code mẫu ở trên.
- `business_rules.md` — các rule (BR-...) được hiện thực trực tiếp trong các pattern (đặc biệt mục 2–4).
- `database_design.md` — bảng dữ liệu tương ứng với các model dùng trong ví dụ.
