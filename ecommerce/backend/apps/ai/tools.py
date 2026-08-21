import logging
import unicodedata
import uuid
from datetime import timedelta
from decimal import Decimal, InvalidOperation
from typing import Any

from django.conf import settings
from django.db import DatabaseError, connections
from django.db.models import Avg, Count, Q
from django.utils import timezone

from apps.after_sales.models import ReturnRequest
from apps.catalog.models import Category
from apps.common.exceptions import BusinessError
from apps.common.models import SiteSetting
from apps.order.models import Order, ShopOrder
from apps.product.models import ProductAttributeValue, VariantAttributeValue
from apps.product.selectors import ProductSelector, SearchSelector
from apps.product.serializers import PublicProductListSerializer
from apps.promotion.models import UserVoucher, Voucher
from apps.review.models import Review

from .models import AIRequestLog, PolicyDocument, sanitize_ai_text
from .product_matching import assess_product_matches
from .recommendation_service import RecommendationService
from .services import AIService

try:
    from pgvector.django import CosineDistance
except ImportError:  # pragma: no cover - required in production, safe fallback for tooling
    CosineDistance = None

logger = logging.getLogger(__name__)

TOOL_SPECS = [
    {
        "name": "search_products",
        "description": "Tìm sản phẩm thật, công khai và còn hàng trên Mercato.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Nhu cầu hoặc từ khóa sản phẩm"},
                "category": {
                    "type": "string",
                    "description": "Tên, slug hoặc ID danh mục nếu khách đã nêu rõ",
                },
                "min_price": {"type": "number", "minimum": 0},
                "max_price": {"type": "number", "minimum": 0},
                "limit": {"type": "integer", "minimum": 1, "maximum": 8},
            },
            "required": ["query"],
        },
    },
    {
        "name": "get_product",
        "description": "Lấy thông tin public mới nhất của một sản phẩm theo ID.",
        "parameters": {
            "type": "object",
            "properties": {"product_id": {"type": "string"}},
            "required": ["product_id"],
        },
    },
    {
        "name": "compare_products",
        "description": "So sánh từ 2 đến 4 sản phẩm thật bằng dịch vụ so sánh của Mercato.",
        "parameters": {
            "type": "object",
            "properties": {
                "product_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "minItems": 2,
                    "maxItems": 4,
                }
            },
            "required": ["product_ids"],
        },
    },
    {
        "name": "get_policy",
        "description": (
            "Tra cứu nội dung chính sách đã được Mercato xác minh về giao hàng, "
            "đổi trả hoặc thanh toán."
        ),
        "parameters": {
            "type": "object",
            "properties": {"topic": {"type": "string"}},
            "required": ["topic"],
        },
    },
    {
        "name": "get_order_status",
        "description": (
            "Tra cứu trạng thái đơn và giao hàng từ OMS. Chỉ hoạt động với khách đã đăng nhập "
            "và chỉ trả về đơn thuộc chính khách đó."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "order_code": {"type": "string", "description": "Mã ORD/SORD nếu khách nêu"},
                "limit": {"type": "integer", "minimum": 1, "maximum": 5},
            },
        },
    },
    {
        "name": "get_return_support",
        "description": (
            "Kiểm tra trạng thái và điều kiện mở yêu cầu đổi/trả/hoàn tiền bằng dữ liệu thật. "
            "Không tự tạo yêu cầu thay khách."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "order_code": {"type": "string"},
                "limit": {"type": "integer", "minimum": 1, "maximum": 5},
            },
        },
    },
    {
        "name": "get_payment_support",
        "description": (
            "Tra cứu trạng thái thanh toán và lỗi giao dịch đã được hệ thống ghi nhận cho đơn "
            "của khách đã đăng nhập."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "order_code": {"type": "string"},
                "limit": {"type": "integer", "minimum": 1, "maximum": 5},
            },
        },
    },
    {
        "name": "get_active_promotions",
        "description": "Lấy mã giảm giá công khai đang còn hiệu lực trực tiếp từ hệ thống.",
        "parameters": {
            "type": "object",
            "properties": {"limit": {"type": "integer", "minimum": 1, "maximum": 8}},
        },
    },
    {
        "name": "get_personalized_recommendations",
        "description": (
            "Gợi ý sản phẩm bằng lịch sử xem, mua hàng và wishlist có sẵn; chỉ trả sản phẩm "
            "đang công khai từ catalog."
        ),
        "parameters": {
            "type": "object",
            "properties": {"limit": {"type": "integer", "minimum": 1, "maximum": 8}},
        },
    },
]


class ToolExecutionError(Exception):
    """A safe, expected tool failure that can be returned to the model."""


def execute_tool(name: str, arguments: dict[str, Any], *, user: Any = None) -> dict[str, Any]:
    try:
        if name == "search_products":
            return _search_products(**arguments)
        if name == "get_product":
            return _get_product(
                arguments.get("product_id"),
                user_need=str(arguments.get("_user_need", "")),
            )
        if name == "compare_products":
            return AIService().compare_products(arguments.get("product_ids", []), user=user)
        if name == "get_policy":
            return _get_policy(arguments.get("topic", ""), user=user)
        if name == "get_order_status":
            return _get_order_support(
                order_code=arguments.get("order_code", ""),
                limit=arguments.get("limit", 3),
                user=user,
                include_payment=False,
            )
        if name == "get_return_support":
            return _get_order_support(
                order_code=arguments.get("order_code", ""),
                limit=arguments.get("limit", 3),
                user=user,
                include_payment=False,
            )
        if name == "get_payment_support":
            return _get_order_support(
                order_code=arguments.get("order_code", ""),
                limit=arguments.get("limit", 3),
                user=user,
                include_payment=True,
            )
        if name == "get_active_promotions":
            return _get_active_promotions(limit=arguments.get("limit", 5), user=user)
        if name == "get_personalized_recommendations":
            return _get_personalized_recommendations(
                limit=arguments.get("limit", 4),
                browsing_history=arguments.get("_browsing_history", []),
                user=user,
            )
        raise ToolExecutionError("Công cụ không được hỗ trợ")
    except (BusinessError, ToolExecutionError, ValueError) as exc:
        return {
            "error": True,
            "message": sanitize_ai_text(str(exc), max_length=300),
        }
    except Exception:
        logger.exception("Shopping assistant tool failed", extra={"ai_tool": name})
        return {
            "error": True,
            "message": "Công cụ tạm thời không khả dụng. Hãy thử cách khác.",
        }


def _search_products(
    query: str,
    category: str | None = None,
    min_price: Any = None,
    max_price: Any = None,
    limit: Any = 5,
    _user_need: str = "",
) -> dict[str, Any]:
    normalized_query = sanitize_ai_text(query, max_length=300).strip()
    if not normalized_query:
        raise ToolExecutionError("Cần có từ khóa hoặc nhu cầu để tìm sản phẩm")
    try:
        normalized_limit = min(8, max(1, int(limit or 5)))
    except (TypeError, ValueError) as exc:
        raise ToolExecutionError("Số lượng kết quả không hợp lệ") from exc

    params: dict[str, Any] = {
        "q": normalized_query,
        "sort": "relevance",
        "in_stock": True,
    }
    if category:
        category_value = sanitize_ai_text(category, max_length=100).strip()
        try:
            params["category"] = uuid.UUID(category_value)
        except ValueError:
            matched_category = (
                Category.objects.filter(is_active=True, is_deleted=False)
                .filter(Q(slug__iexact=category_value) | Q(name__icontains=category_value))
                .order_by("name", "id")
                .first()
            )
            if matched_category:
                params["category"] = matched_category.pk

    price_min = _optional_nonnegative_decimal(min_price, "Giá tối thiểu")
    price_max = _optional_nonnegative_decimal(max_price, "Giá tối đa")
    if price_min is not None:
        params["price_min"] = price_min
    if price_max is not None:
        params["price_max"] = price_max
    if price_min is not None and price_max is not None and price_min > price_max:
        raise ToolExecutionError("Giá tối thiểu không thể lớn hơn giá tối đa")

    products = list(SearchSelector.search(params)[:normalized_limit])
    serialized_products = _serialize_products_with_verified_ratings(products)
    matches = assess_product_matches(
        user_need=_user_need or normalized_query,
        products=products,
        attribute_text_by_product=_attribute_text_by_product(products),
        price_range_by_product={
            str(product["id"]): (product.get("min_price"), product.get("max_price"))
            for product in serialized_products
        },
    )
    return {
        "products": serialized_products,
        "result_count": len(products),
        "matches": [match.to_dict() for match in matches],
    }


def _get_product(product_id: Any, *, user_need: str = "") -> dict[str, Any]:
    try:
        normalized_id = uuid.UUID(str(product_id))
    except (TypeError, ValueError, AttributeError) as exc:
        raise ToolExecutionError("ID sản phẩm không hợp lệ") from exc
    product = ProductSelector.public_list().filter(pk=normalized_id).first()
    if product is None:
        raise ToolExecutionError("Sản phẩm không tồn tại hoặc không còn hiển thị")
    serialized_product = _serialize_products_with_verified_ratings([product])[0]
    matches = assess_product_matches(
        user_need=user_need or product.name,
        products=[product],
        attribute_text_by_product=_attribute_text_by_product([product]),
        price_range_by_product={
            str(serialized_product["id"]): (
                serialized_product.get("min_price"),
                serialized_product.get("max_price"),
            )
        },
    )
    return {
        "product": serialized_product,
        "matches": [match.to_dict() for match in matches],
    }


def _attribute_text_by_product(products: list[Any]) -> dict[str, list[str]]:
    product_ids = [product.pk for product in products]
    values_by_product: dict[str, list[str]] = {str(product_id): [] for product_id in product_ids}
    if not product_ids:
        return values_by_product

    product_values = ProductAttributeValue.objects.filter(product_id__in=product_ids).values_list(
        "product_id",
        "attribute_value__attribute__name",
        "attribute_value__value",
        "attribute_value__display_value",
    )
    for product_id, attribute_name, value, display_value in product_values:
        values_by_product[str(product_id)].extend(
            part for part in (attribute_name, value, display_value) if part
        )

    variant_values = VariantAttributeValue.objects.filter(
        variant__product_id__in=product_ids,
        variant__is_active=True,
        variant__is_deleted=False,
    ).values_list(
        "variant__product_id",
        "attribute__name",
        "attribute_value__value",
        "attribute_value__display_value",
    )
    for product_id, attribute_name, value, display_value in variant_values:
        values_by_product[str(product_id)].extend(
            part for part in (attribute_name, value, display_value) if part
        )
    return values_by_product


def _serialize_products_with_verified_ratings(products: list[Any]) -> list[dict[str, Any]]:
    """Use visible review rows as the source of truth for chat product ratings."""
    serialized = [dict(item) for item in PublicProductListSerializer(products, many=True).data]
    if not serialized:
        return serialized

    product_ids = [item["id"] for item in serialized]
    verified_stats = {
        str(row["product_id"]): row
        for row in Review.objects.filter(
            product_id__in=product_ids,
            status=Review.Status.VISIBLE,
            is_deleted=False,
        )
        .values("product_id")
        .annotate(rating_average=Avg("rating"), rating_count=Count("id"))
    }
    for item in serialized:
        stats = verified_stats.get(str(item["id"]))
        item["rating_average"] = (
            f"{stats['rating_average']:.2f}" if stats and stats["rating_average"] else "0.00"
        )
        item["rating_count"] = int(stats["rating_count"]) if stats else 0
    return serialized


def _get_policy(topic: str, *, user: Any = None) -> dict[str, Any]:
    normalized_topic = sanitize_ai_text(topic, max_length=300).strip()
    if not normalized_topic:
        raise ToolExecutionError("Cần nêu chủ đề chính sách muốn tra cứu")

    queryset = PolicyDocument.objects.filter(is_active=True)
    category = _policy_category(normalized_topic)
    if category:
        queryset = queryset.filter(category=category)

    documents: list[PolicyDocument] = []
    if (
        CosineDistance is not None
        and connections[queryset.db].vendor == "postgresql"
        and queryset.filter(embedding__isnull=False).exists()
    ):
        try:
            embedding = AIService().get_embedding(
                feature=AIRequestLog.Feature.POLICY_EMBEDDING,
                text=normalized_topic,
                task_type="retrieval_query",
                user=user,
                fallback=[],
            )
            if (
                embedding.ai_used
                and not embedding.fallback_used
                and len(embedding.vector) == settings.AI_EMBEDDING_DIMENSIONS
            ):
                documents = list(
                    queryset.filter(embedding__isnull=False)
                    .annotate(distance=CosineDistance("embedding", embedding.vector))
                    .order_by("distance", "id")[:2]
                )
        except (DatabaseError, ValueError):
            logger.warning("Policy vector lookup failed; using verified keyword fallback")

    if not documents:
        terms = [term for term in _normalized_words(normalized_topic) if len(term) >= 3][:8]
        matching = Q()
        for term in terms:
            matching |= Q(title__icontains=term) | Q(content__icontains=term)
        documents = list((queryset.filter(matching) if matching else queryset)[:2])
        if not documents and category:
            documents = list(PolicyDocument.objects.filter(is_active=True, category=category)[:2])

    if not documents:
        return {
            "documents": [],
            "message": "Mercato chưa công bố chính sách đã xác minh cho chủ đề này.",
        }
    return {
        "documents": [
            {
                "id": str(document.pk),
                "category": document.category,
                "title": document.title,
                "content": document.content,
            }
            for document in documents
        ]
    }


def _authentication_required() -> dict[str, Any]:
    return {
        "error": True,
        "code": "authentication_required",
        "message": "Vui lòng đăng nhập để tra cứu dữ liệu tài khoản.",
    }


def _eligible_customer(user: Any) -> bool:
    return bool(
        user
        and getattr(user, "is_authenticated", False)
        and getattr(user, "role", None) == "customer"
        and getattr(user, "is_active", False)
        and not getattr(user, "is_deleted", True)
    )


def _normalized_limit(value: Any, *, default: int, maximum: int) -> int:
    try:
        return min(maximum, max(1, int(value or default)))
    except (TypeError, ValueError) as exc:
        raise ToolExecutionError("Số lượng kết quả không hợp lệ") from exc


def _get_order_support(
    *,
    order_code: Any = "",
    limit: Any = 3,
    user: Any = None,
    include_payment: bool = False,
) -> dict[str, Any]:
    if not _eligible_customer(user):
        return _authentication_required()

    normalized_code = sanitize_ai_text(order_code, max_length=60).strip().upper()
    normalized_limit = _normalized_limit(limit, default=3, maximum=5)
    queryset = (
        Order.objects.filter(customer__user=user)
        .select_related("customer__user")
        .prefetch_related(
            "payments",
            "shop_orders__shop",
            "shop_orders__items",
            "shop_orders__status_history",
            "shop_orders__return_requests__items",
            "shop_orders__return_requests__refunds",
        )
        .order_by("-placed_at", "-id")
    )
    if normalized_code:
        queryset = queryset.filter(
            Q(order_code__iexact=normalized_code)
            | Q(shop_orders__shop_order_code__iexact=normalized_code)
        ).distinct()
    orders = list(queryset[:normalized_limit])
    if not orders:
        message = (
            f"Không tìm thấy đơn {normalized_code} trong tài khoản này."
            if normalized_code
            else "Tài khoản này chưa có đơn hàng."
        )
        return {"orders": [], "message": message}

    window_days = int(SiteSetting.get_value("returns.window_days", 7))
    return {
        "orders": [
            _serialize_owned_order(
                order,
                window_days=window_days,
                include_payment=include_payment,
            )
            for order in orders
        ],
        "source": "oms",
        "retrieved_at": timezone.now().isoformat(),
    }


def _serialize_owned_order(
    order: Order,
    *,
    window_days: int,
    include_payment: bool,
) -> dict[str, Any]:
    shop_orders = []
    now = timezone.now()
    for shop_order in order.shop_orders.all():
        return_requests = list(shop_order.return_requests.all())
        has_active_return = any(
            request.status != ReturnRequest.Status.CLOSED for request in return_requests
        )
        completed_at = shop_order.completed_at or shop_order.updated_at
        return_deadline = completed_at + timedelta(days=window_days)
        return_eligible = bool(
            shop_order.fulfillment_status == ShopOrder.FulfillmentStatus.COMPLETED
            and now <= return_deadline
            and not has_active_return
        )
        latest_history = max(
            shop_order.status_history.all(),
            key=lambda item: item.created_at,
            default=None,
        )
        shop_orders.append(
            {
                "id": str(shop_order.pk),
                "shop_order_code": shop_order.shop_order_code,
                "shop_name": shop_order.shop.name,
                "fulfillment_status": shop_order.fulfillment_status,
                "fulfillment_status_label": shop_order.get_fulfillment_status_display(),
                "shipping_method": shop_order.shipping_method_name or "Chưa cập nhật",
                "estimated_delivery_at": None,
                "last_status_at": (
                    latest_history.created_at.isoformat()
                    if latest_history
                    else shop_order.updated_at.isoformat()
                ),
                "return_eligible": return_eligible,
                "return_deadline": return_deadline.isoformat() if return_eligible else None,
                "items": [
                    {
                        "id": str(item.pk),
                        "name": item.product_name,
                        "variant": item.variant_name,
                        "quantity": item.quantity,
                    }
                    for item in list(shop_order.items.all())[:4]
                ],
                "return_requests": [
                    {
                        "id": str(request.pk),
                        "status": request.status,
                        "status_label": request.get_status_display(),
                        "requested_at": request.requested_at.isoformat(),
                    }
                    for request in return_requests[:3]
                ],
            }
        )

    payload: dict[str, Any] = {
        "id": str(order.pk),
        "order_code": order.order_code,
        "placed_at": order.placed_at.isoformat(),
        "grand_total": str(order.grand_total),
        "currency": order.currency,
        "payment_status": order.payment_status,
        "payment_status_label": order.get_payment_status_display(),
        "payment_method": order.payment_method,
        "payment_method_label": order.get_payment_method_display(),
        "shop_orders": shop_orders,
    }
    if include_payment:
        payment = max(order.payments.all(), key=lambda item: item.created_at, default=None)
        payload["payment"] = (
            {
                "status": payment.status,
                "status_label": payment.get_status_display(),
                "method": payment.method,
                "failed_at": payment.failed_at.isoformat() if payment.failed_at else None,
                "failure_code": sanitize_ai_text(payment.failure_code, max_length=100),
                "failure_message": sanitize_ai_text(payment.failure_message, max_length=300),
            }
            if payment
            else None
        )
    return payload


def _get_active_promotions(*, limit: Any = 5, user: Any = None) -> dict[str, Any]:
    normalized_limit = _normalized_limit(limit, default=5, maximum=8)
    now = timezone.now()
    promotions = list(
        Voucher.objects.filter(
            is_active=True,
            valid_from__lte=now,
            valid_until__gte=now,
        )
        .filter(Q(remaining_quantity__isnull=True) | Q(remaining_quantity__gt=0))
        .select_related("shop")
        .order_by("valid_until", "code")[:normalized_limit]
    )
    saved_ids: set[uuid.UUID] = set()
    if _eligible_customer(user):
        saved_ids = set(
            UserVoucher.objects.filter(
                user=user.customer_profile,
                voucher_campaign__in=promotions,
                status__in=(UserVoucher.Status.SAVED, UserVoucher.Status.PENDING_USE),
            ).values_list("voucher_campaign_id", flat=True)
        )
    return {
        "promotions": [
            {
                "id": str(voucher.pk),
                "code": voucher.code,
                "name": voucher.name,
                "description": voucher.description,
                "scope": voucher.scope,
                "shop_name": voucher.shop.name if voucher.shop else "Mercato",
                "discount_type": voucher.discount_type,
                "discount_value": str(voucher.discount_value),
                "max_discount_amount": (
                    str(voucher.max_discount_amount)
                    if voucher.max_discount_amount is not None
                    else None
                ),
                "min_order_amount": str(voucher.min_order_amount),
                "valid_until": voucher.valid_until.isoformat(),
                "remaining_quantity": voucher.remaining_quantity,
                "saved": voucher.pk in saved_ids,
            }
            for voucher in promotions
        ],
        "source": "promotion_service",
        "retrieved_at": now.isoformat(),
    }


def _get_personalized_recommendations(
    *,
    limit: Any = 4,
    browsing_history: Any = (),
    user: Any = None,
) -> dict[str, Any]:
    normalized_limit = _normalized_limit(limit, default=4, maximum=8)
    browsing_ids: list[uuid.UUID] = []
    for item in browsing_history if isinstance(browsing_history, (list, tuple)) else ():
        try:
            browsing_ids.append(uuid.UUID(str(item)))
        except (TypeError, ValueError, AttributeError):
            continue
        if len(browsing_ids) >= 20:
            break

    purchase_ids: list[uuid.UUID] = []
    if _eligible_customer(user):
        purchase_ids = list(
            uuid.UUID(str(product_id))
            for product_id in Order.objects.filter(customer__user=user)
            .order_by("-placed_at")
            .values_list("shop_orders__items__product_id", flat=True)
            .exclude(shop_orders__items__product_id__isnull=True)[:20]
        )
    signals = list(dict.fromkeys([*browsing_ids, *purchase_ids]))[:20]
    outcome = RecommendationService.recommendations(
        browsing_ids=signals,
        user=user if _eligible_customer(user) else None,
    )
    products = list(outcome.products[:normalized_limit])
    return {
        "products": _serialize_products_with_verified_ratings(products),
        "result_count": len(products),
        "personalized": outcome.personalized,
        "strategy": outcome.strategy,
        "signal_counts": {
            "browsing": len(browsing_ids),
            "purchases": len(purchase_ids),
        },
    }


def extract_product_ids(result: Any) -> set[str]:
    product_ids: set[str] = set()
    if isinstance(result, dict):
        for key, value in result.items():
            if key == "id" and _is_uuid(value):
                product_ids.add(str(value))
            elif key in {"product_id", "product_ids"}:
                values = value if isinstance(value, list) else [value]
                product_ids.update(str(item) for item in values if _is_uuid(item))
            else:
                product_ids.update(extract_product_ids(value))
    elif isinstance(result, list):
        for item in result:
            product_ids.update(extract_product_ids(item))
    return product_ids


def build_attachments(name: str, result: dict[str, Any]) -> list[dict[str, Any]]:
    if result.get("code") == "authentication_required":
        return [
            {
                "type": "quick_actions",
                "actions": [
                    {
                        "label": "Đăng nhập để tra cứu",
                        "kind": "link",
                        "value": "/auth/login",
                    },
                    {
                        "label": "Xem chính sách hỗ trợ",
                        "kind": "reply",
                        "value": "Chính sách đổi trả và thanh toán của Mercato",
                    },
                ],
            }
        ]
    if result.get("error"):
        return []
    if name == "search_products":
        matches = {
            str(match.get("product_id")): match
            for match in result.get("matches", [])
            if isinstance(match, dict)
        }
        return [
            {
                "type": "product_card",
                "product_id": product["id"],
                "product": product,
                "match": matches.get(
                    str(product["id"]),
                    {
                        "kind": "alternative",
                        "matched_terms": [],
                        "missing_terms": [],
                    },
                ),
            }
            for product in result.get("products", [])
            if isinstance(product, dict) and product.get("id")
        ]
    if name == "get_product" and isinstance(result.get("product"), dict):
        product = result["product"]
        match = next(
            (
                item
                for item in result.get("matches", [])
                if isinstance(item, dict) and str(item.get("product_id")) == str(product["id"])
            ),
            {
                "kind": "alternative",
                "matched_terms": [],
                "missing_terms": [],
            },
        )
        return [
            {
                "type": "product_card",
                "product_id": product["id"],
                "product": product,
                "match": match,
            }
        ]
    if name == "compare_products":
        product_ids = [
            str(product["id"])
            for product in result.get("products", [])
            if isinstance(product, dict) and product.get("id")
        ]
        return [
            {
                "type": "compare_table",
                "product_ids": product_ids,
                "comparison": result,
            }
        ]
    if name in {"get_order_status", "get_return_support", "get_payment_support"}:
        attachments: list[dict[str, Any]] = [
            {
                "type": "order_card",
                "order": order,
            }
            for order in result.get("orders", [])
            if isinstance(order, dict) and order.get("id")
        ]
        if attachments:
            first_order = attachments[0]["order"]
            attachments.append(
                {
                    "type": "quick_actions",
                    "actions": [
                        {
                            "label": "Mở chi tiết đơn",
                            "kind": "link",
                            "value": f"/account/orders/{first_order['id']}",
                        },
                        {
                            "label": "Kiểm tra đổi/trả",
                            "kind": "reply",
                            "value": f"Kiểm tra đổi trả đơn {first_order['order_code']}",
                        },
                        {
                            "label": "Gặp nhân viên hỗ trợ",
                            "kind": "reply",
                            "value": "Tôi muốn gặp nhân viên hỗ trợ",
                        },
                    ],
                }
            )
        else:
            attachments.append(
                {
                    "type": "quick_actions",
                    "actions": [
                        {
                            "label": "Mở lịch sử đơn hàng",
                            "kind": "link",
                            "value": "/account/orders",
                        },
                        {
                            "label": "Gặp nhân viên hỗ trợ",
                            "kind": "reply",
                            "value": "Tôi muốn gặp nhân viên hỗ trợ",
                        },
                    ],
                }
            )
        return attachments
    if name == "get_active_promotions":
        attachments = [
            {"type": "promotion_card", "promotion": promotion}
            for promotion in result.get("promotions", [])
            if isinstance(promotion, dict) and promotion.get("id")
        ]
        if attachments:
            attachments.append(
                {
                    "type": "quick_actions",
                    "actions": [
                        {
                            "label": "Mở kho voucher",
                            "kind": "link",
                            "value": "/voucher-center",
                        },
                        {
                            "label": "Xem Flash Sale",
                            "kind": "link",
                            "value": "/flash-sales",
                        },
                    ],
                }
            )
        return attachments
    if name == "get_personalized_recommendations":
        return [
            {
                "type": "product_card",
                "product_id": product["id"],
                "product": product,
                "match": {
                    "kind": "personalized",
                    "matched_terms": ["personalized"],
                    "missing_terms": [],
                },
            }
            for product in result.get("products", [])
            if isinstance(product, dict) and product.get("id")
        ]
    return []


def _optional_nonnegative_decimal(value: Any, label: str) -> Decimal | None:
    if value in (None, ""):
        return None
    try:
        normalized = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ToolExecutionError(f"{label} không hợp lệ") from exc
    if not normalized.is_finite() or normalized < 0:
        raise ToolExecutionError(f"{label} không hợp lệ")
    return normalized


def _policy_category(topic: str) -> str | None:
    normalized = " ".join(_normalized_words(topic))
    mapping = {
        PolicyDocument.Category.SHIPPING: ("giao hang", "van chuyen", "phi ship", "ship"),
        PolicyDocument.Category.RETURN: ("doi tra", "tra hang", "hoan tien", "khieu nai"),
        PolicyDocument.Category.PAYMENT: ("thanh toan", "cod", "vnpay"),
        PolicyDocument.Category.WARRANTY: ("bao hanh",),
    }
    for category, phrases in mapping.items():
        if any(phrase in normalized for phrase in phrases):
            return category
    return None


def _normalized_words(value: str) -> list[str]:
    decomposed = unicodedata.normalize("NFD", value.casefold())
    ascii_value = "".join(
        character for character in decomposed if not unicodedata.combining(character)
    ).replace("đ", "d")
    normalized = "".join(character if character.isalnum() else " " for character in ascii_value)
    return normalized.split()


def _is_uuid(value: Any) -> bool:
    try:
        uuid.UUID(str(value))
    except (TypeError, ValueError, AttributeError):
        return False
    return True
