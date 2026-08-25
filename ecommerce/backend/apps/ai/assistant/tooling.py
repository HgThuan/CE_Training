from __future__ import annotations

import logging
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from django.db import DatabaseError, connections, transaction
from django.db.models import Q
from django.utils import timezone

from apps.account.models import User
from apps.ai.models import ChatHandoff, ChatMessage, ChatSession, PolicyDocument, sanitize_ai_text
from apps.ai.services import AIService
from apps.catalog.models import Brand, Category
from apps.common.exceptions import BusinessError
from apps.order.models import Order
from apps.order.selectors import get_orders_for_customer
from apps.product.models import ProductAttributeValue
from apps.product.selectors import SearchSelector
from apps.product.serializers import PublicProductListSerializer
from apps.promotion.models import FlashSale, Voucher

from .recommendation import GroundedRecommendationEngine
from .schemas import ToolResult
from .state import ConversationState

try:
    from pgvector.django import CosineDistance
except ImportError:  # pragma: no cover
    CosineDistance = None

logger = logging.getLogger(__name__)


class AssistantToolError(Exception):
    def __init__(self, message: str, *, code: str = "tool_error") -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True, slots=True)
class ToolContext:
    user: Any
    session: ChatSession
    state: ConversationState


@dataclass(frozen=True, slots=True)
class ToolDefinition:
    handler: Callable[[dict[str, Any], ToolContext], dict[str, Any]]
    allowed_arguments: frozenset[str]
    customer_only: bool = False


class AssistantToolRegistry:
    def __init__(self, *, ai_service: AIService | None = None) -> None:
        self._ai_service = ai_service or AIService()
        self._recommendation = GroundedRecommendationEngine()
        self._definitions = {
            "search_products": ToolDefinition(
                self._search_products,
                frozenset(
                    {
                        "query",
                        "query_terms",
                        "product_type",
                        "category",
                        "brand",
                        "price_min",
                        "price_max",
                        "in_stock",
                        "limit",
                    }
                ),
            ),
            "compare_products": ToolDefinition(
                self._compare_products,
                frozenset({"product_ids"}),
            ),
            "get_policy": ToolDefinition(self._get_policy, frozenset({"topic"})),
            "get_order_status": ToolDefinition(
                self._get_order_status,
                frozenset({"order_code"}),
                customer_only=True,
            ),
            "get_return_support": ToolDefinition(
                self._get_return_support,
                frozenset({"order_code"}),
                customer_only=True,
            ),
            "get_payment_support": ToolDefinition(
                self._get_payment_support,
                frozenset({"order_code"}),
                customer_only=True,
            ),
            "get_promotions": ToolDefinition(
                self._get_promotions,
                frozenset({"limit"}),
            ),
            "get_flash_sales": ToolDefinition(
                self._get_flash_sales,
                frozenset({"limit"}),
            ),
            "human_handoff": ToolDefinition(
                self._human_handoff,
                frozenset({"reason"}),
                customer_only=True,
            ),
        }

    def execute(
        self,
        *,
        name: str,
        arguments: dict[str, Any],
        context: ToolContext,
    ) -> ToolResult:
        started = time.monotonic()
        definition = self._definitions.get(name)
        if definition is None:
            return ToolResult(
                name=name,
                ok=False,
                error_code="tool_not_allowed",
                message="Công cụ không được phép sử dụng.",
            )
        if definition.customer_only and not _eligible_customer(context.user):
            return ToolResult(
                name=name,
                ok=False,
                error_code="authentication_required",
                message="Vui lòng đăng nhập bằng tài khoản khách hàng để tra cứu dữ liệu này.",
            )
        safe_arguments = {
            key: value for key, value in arguments.items() if key in definition.allowed_arguments
        }
        try:
            data = definition.handler(safe_arguments, context)
        except AssistantToolError as exc:
            return ToolResult(
                name=name,
                ok=False,
                error_code=exc.code,
                message=sanitize_ai_text(str(exc), max_length=300),
                duration_ms=_elapsed(started),
            )
        except (BusinessError, ValueError) as exc:
            return ToolResult(
                name=name,
                ok=False,
                error_code="invalid_tool_request",
                message=sanitize_ai_text(str(exc), max_length=300),
                duration_ms=_elapsed(started),
            )
        except Exception:
            logger.exception("Assistant tool failed", extra={"ai_tool": name})
            return ToolResult(
                name=name,
                ok=False,
                error_code="tool_unavailable",
                message="Dữ liệu Mercato tạm thời không khả dụng.",
                duration_ms=_elapsed(started),
            )
        return ToolResult(name=name, ok=True, data=data, duration_ms=_elapsed(started))

    def _search_products(
        self,
        arguments: dict[str, Any],
        context: ToolContext,
    ) -> dict[str, Any]:
        query = sanitize_ai_text(arguments.get("query", ""), max_length=250).strip()
        product_type = sanitize_ai_text(
            arguments.get("product_type", ""), max_length=120
        ).strip()
        if not query and not arguments.get("category") and not product_type:
            raise AssistantToolError("Cần có nhu cầu hoặc nhóm sản phẩm để tìm kiếm.")
        limit = _limit(arguments.get("limit"), default=4, maximum=8)
        params: dict[str, Any] = {
            "sort": "relevance",
            "in_stock": bool(arguments.get("in_stock", True)),
        }
        category = _catalog_slug(Category, arguments.get("category"))
        brand = _catalog_slug(Brand, arguments.get("brand"))
        if category:
            params["category"] = category
        if brand:
            params["brand"] = brand
        for source, target in (("price_min", "price_min"), ("price_max", "price_max")):
            value = arguments.get(source)
            if value is not None:
                params[target] = _nonnegative_number(value, source)

        raw_query_terms = arguments.get("query_terms")
        query_terms = (
            [
                sanitize_ai_text(item, max_length=80).strip()
                for item in raw_query_terms[:6]
                if isinstance(item, str) and sanitize_ai_text(item, max_length=80).strip()
            ]
            if isinstance(raw_query_terms, list)
            else []
        )
        search_queries = list(dict.fromkeys([query, *query_terms]))
        category_value = sanitize_ai_text(arguments.get("category", ""), max_length=100).strip()
        if category and _normalized_text(query) == _normalized_text(category_value):
            search_queries = ["", *query_terms]
        if not search_queries:
            search_queries = [""]

        products: list[Any] = []
        product_type_needs_name_scope = bool(
            product_type
            and not (
                category
                and _normalized_text(product_type) == _normalized_text(category_value)
            )
        )
        if product_type_needs_name_scope:
            # Once a concrete product noun exists, context is ranking-only.
            # It must never generate candidates outside this bounded scope.
            candidate_limit = min(200, max(limit * 25, limit))
            scoped_params = dict(params)
            if connections["default"].vendor == "postgresql":
                scoped_params["q"] = product_type
            else:
                # SQLite's case-insensitive lookup is ASCII-only for Vietnamese
                # text, so the isolated test fallback applies the same Unicode
                # normalization in Python over a bounded public candidate set.
                scoped_params.pop("sort", None)
            products = [
                product
                for product in SearchSelector.search(scoped_params).filter(
                    name__icontains=product_type
                )[:candidate_limit]
                if _contains_normalized_phrase(product.name, product_type)
            ]
        else:
            seen_product_ids: set[str] = set()
            for search_query in search_queries:
                candidate_params = dict(params)
                if search_query:
                    candidate_params["q"] = search_query
                else:
                    candidate_params.pop("sort", None)
                for product in SearchSelector.search(candidate_params)[:limit]:
                    product_id = str(product.pk)
                    if product_id in seen_product_ids:
                        continue
                    seen_product_ids.add(product_id)
                    products.append(product)
                    if len(products) >= limit:
                        break
                if len(products) >= limit:
                    break
        serialized = [dict(item) for item in PublicProductListSerializer(products, many=True).data]
        details = _product_details(products)
        for item in serialized:
            item.update(details.get(str(item["id"]), {}))
            item["stock_status"] = "in_stock"
        ranked = self._recommendation.rank(
            products=serialized,
            state=context.state,
            context_terms=query_terms,
        )[:limit]
        return {
            "products": [item["product"] for item in ranked],
            "recommendations": [
                {
                    "product_id": str(item["product"]["id"]),
                    "score": item["recommendation_score"],
                    "reasons": item["reasons"],
                    "compatibility_warnings": item["compatibility_warnings"],
                    "kind": item["kind"],
                }
                for item in ranked
            ],
            "result_count": len(ranked),
            "source": "catalog",
            "query": query,
            "expanded_terms": query_terms,
        }

    def _compare_products(
        self,
        arguments: dict[str, Any],
        context: ToolContext,
    ) -> dict[str, Any]:
        raw_ids = arguments.get("product_ids")
        if not isinstance(raw_ids, list):
            raise AssistantToolError("Cần chọn từ 2 đến 4 sản phẩm để so sánh.")
        return self._ai_service.compare_products(raw_ids[:4], user=context.user)

    def _get_policy(
        self,
        arguments: dict[str, Any],
        context: ToolContext,
    ) -> dict[str, Any]:
        topic = sanitize_ai_text(arguments.get("topic", ""), max_length=300).strip()
        if not topic:
            raise AssistantToolError("Cần nêu chủ đề chính sách muốn tra cứu.")
        queryset = PolicyDocument.objects.filter(is_active=True)
        category = _policy_category(topic)
        if category:
            queryset = queryset.filter(category=category)
        documents: list[PolicyDocument] = []
        if (
            CosineDistance is not None
            and connections[queryset.db].vendor == "postgresql"
            and queryset.filter(embedding__isnull=False).exists()
        ):
            try:
                embedding = self._ai_service.get_embedding(
                    feature="policy_embedding",
                    text=topic,
                    task_type="retrieval_query",
                    user=context.user,
                    fallback=[],
                )
                if embedding.ai_used and embedding.vector:
                    documents = list(
                        queryset.filter(embedding__isnull=False)
                        .annotate(distance=CosineDistance("embedding", embedding.vector))
                        .order_by("distance", "id")[:2]
                    )
            except (DatabaseError, ValueError):
                logger.warning("Policy vector search failed; using relational fallback")
        if not documents:
            terms = [term for term in _normalize_words(topic) if len(term) >= 3][:8]
            condition = Q()
            for term in terms:
                condition |= Q(title__icontains=term) | Q(content__icontains=term)
            documents = list((queryset.filter(condition) if condition else queryset)[:2])
        return {
            "documents": [
                {
                    "id": str(document.pk),
                    "category": document.category,
                    "title": document.title,
                    "content": document.content,
                }
                for document in documents
            ],
            "source": "verified_policy",
        }

    @staticmethod
    def _get_order_status(
        arguments: dict[str, Any],
        context: ToolContext,
    ) -> dict[str, Any]:
        orders = _owned_orders(arguments=arguments, user=context.user)
        return {"orders": [_serialize_order(order) for order in orders], "source": "oms"}

    @staticmethod
    def _get_return_support(
        arguments: dict[str, Any],
        context: ToolContext,
    ) -> dict[str, Any]:
        orders = _owned_orders(arguments=arguments, user=context.user)
        payload = [_serialize_order(order) for order in orders]
        return {"orders": payload, "source": "returns"}

    @staticmethod
    def _get_payment_support(
        arguments: dict[str, Any],
        context: ToolContext,
    ) -> dict[str, Any]:
        orders = _owned_orders(arguments=arguments, user=context.user)
        return {"orders": [_serialize_order(order) for order in orders], "source": "payments"}

    @staticmethod
    def _get_promotions(
        arguments: dict[str, Any],
        context: ToolContext,
    ) -> dict[str, Any]:
        now = timezone.now()
        limit = _limit(arguments.get("limit"), default=4, maximum=8)
        vouchers = list(
            Voucher.objects.filter(
                is_active=True,
                valid_from__lte=now,
                valid_until__gte=now,
            )
            .filter(Q(remaining_quantity__isnull=True) | Q(remaining_quantity__gt=0))
            .select_related("shop")
            .order_by("valid_until", "id")[:limit]
        )
        return {
            "promotions": [
                {
                    "id": str(voucher.pk),
                    "code": voucher.code,
                    "name": voucher.name,
                    "description": voucher.description,
                    "shop_name": voucher.shop.name if voucher.shop_id else "Mercato",
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
                }
                for voucher in vouchers
            ],
            "source": "promotion",
        }

    @staticmethod
    def _get_flash_sales(
        arguments: dict[str, Any],
        context: ToolContext,
    ) -> dict[str, Any]:
        now = timezone.now()
        limit = _limit(arguments.get("limit"), default=4, maximum=8)
        active = list(
            FlashSale.objects.filter(
                is_active=True,
                start_time__lte=now,
                end_time__gt=now,
            ).order_by("end_time", "id")[:limit]
        )
        upcoming = list(
            FlashSale.objects.filter(
                is_active=True,
                start_time__gt=now,
            ).order_by("start_time", "id")[:2]
        )
        return {
            "as_of": now.isoformat(),
            "active": [
                {
                    "id": str(sale.pk),
                    "name": sale.name,
                    "start_time": sale.start_time.isoformat(),
                    "end_time": sale.end_time.isoformat(),
                    "remaining_seconds": max(0, int((sale.end_time - now).total_seconds())),
                }
                for sale in active
            ],
            "upcoming": [
                {
                    "id": str(sale.pk),
                    "name": sale.name,
                    "start_time": sale.start_time.isoformat(),
                    "end_time": sale.end_time.isoformat(),
                    "starts_in_seconds": max(0, int((sale.start_time - now).total_seconds())),
                }
                for sale in upcoming
            ],
            "source": "flash_sale",
        }

    @staticmethod
    def _human_handoff(
        arguments: dict[str, Any],
        context: ToolContext,
    ) -> dict[str, Any]:
        reason = sanitize_ai_text(arguments.get("reason", ""), max_length=300)
        with transaction.atomic():
            session = ChatSession.objects.select_for_update().get(pk=context.session.pk)
            handoff = session.handoffs.filter(
                status__in=(ChatHandoff.Status.OPEN, ChatHandoff.Status.ASSIGNED)
            ).first()
            if handoff is None:
                messages = list(
                    session.messages.filter(
                        role__in=(ChatMessage.Role.USER, ChatMessage.Role.ASSISTANT)
                    ).order_by("-created_at", "-id")[:20]
                )
                messages.reverse()
                handoff = ChatHandoff.objects.create(
                    session=session,
                    requested_by=context.user,
                    reason=reason,
                    conversation_summary=sanitize_ai_text(
                        session.history_summary or reason,
                        max_length=2_000,
                    ),
                    context_snapshot=[
                        {
                            "role": message.role,
                            "content": sanitize_ai_text(message.content, max_length=1_000),
                            "created_at": message.created_at.isoformat(),
                        }
                        for message in messages
                    ],
                    channel=str((session.context or {}).get("channel", "web"))[:30],
                )
            session.status = ChatSession.Status.ESCALATED
            session.save(update_fields=("status", "updated_at"))
        return {
            "handoff": {
                "id": str(handoff.pk),
                "status": handoff.status,
                "status_label": handoff.get_status_display(),
                "channel": handoff.channel,
            }
        }


def _elapsed(started: float) -> int:
    return max(0, round((time.monotonic() - started) * 1_000))


def _eligible_customer(user: Any) -> bool:
    return bool(
        user
        and getattr(user, "is_authenticated", False)
        and getattr(user, "role", None) == User.Role.CUSTOMER
        and getattr(user, "is_active", False)
        and not getattr(user, "is_deleted", True)
    )


def _limit(value: Any, *, default: int, maximum: int) -> int:
    try:
        return min(maximum, max(1, int(value or default)))
    except (TypeError, ValueError) as exc:
        raise AssistantToolError("Số lượng kết quả không hợp lệ.") from exc


def _nonnegative_number(value: Any, label: str) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise AssistantToolError(f"{label} không hợp lệ.") from exc
    if result < 0 or result == float("inf") or result != result:
        raise AssistantToolError(f"{label} không hợp lệ.")
    return result


def _catalog_slug(model, raw_value: Any) -> str:
    value = sanitize_ai_text(raw_value, max_length=100).strip()
    if not value:
        return ""
    try:
        object_id = uuid.UUID(value)
    except ValueError:
        item = (
            model.objects.filter(is_active=True, is_deleted=False)
            .filter(Q(slug__iexact=value) | Q(name__iexact=value))
            .values("slug")
            .first()
        )
    else:
        item = (
            model.objects.filter(pk=object_id, is_active=True, is_deleted=False)
            .values("slug")
            .first()
        )
    return str(item["slug"]) if item else ""


def _product_details(products: list[Any]) -> dict[str, dict[str, Any]]:
    product_ids = [product.pk for product in products]
    details = {
        str(product.pk): {
            "category_name": product.category.name,
            "brand_name": product.brand.name if product.brand_id else "",
            "short_description": product.short_description or "",
            "attributes": {},
        }
        for product in products
    }
    links = ProductAttributeValue.objects.filter(product_id__in=product_ids).values_list(
        "product_id",
        "attribute_value__attribute__code",
        "attribute_value__attribute__name",
        "attribute_value__display_value",
        "attribute_value__value",
    )
    for product_id, code, name, display_value, value in links:
        # Human-readable names retain generic equipment semantics (for example,
        # "Yêu cầu máy xay") while the catalog code remains an implementation detail.
        key = name or code
        details[str(product_id)]["attributes"][key] = display_value or value
    return details


def _owned_orders(*, arguments: dict[str, Any], user: Any) -> list[Order]:
    code = sanitize_ai_text(arguments.get("order_code", ""), max_length=60).strip().upper()
    queryset = get_orders_for_customer(user).prefetch_related("shop_orders__items")
    if code:
        queryset = queryset.filter(
            Q(order_code__iexact=code) | Q(shop_orders__shop_order_code__iexact=code)
        ).distinct()
    return list(queryset.order_by("-placed_at", "-id")[:3])


def _serialize_order(order: Order) -> dict[str, Any]:
    return {
        "id": str(order.pk),
        "order_code": order.order_code,
        "placed_at": order.placed_at.isoformat(),
        "grand_total": str(order.grand_total),
        "currency": order.currency,
        "payment_status": order.payment_status,
        "payment_status_label": order.get_payment_status_display(),
        "payment_method": order.payment_method,
        "payment_method_label": order.get_payment_method_display(),
        "shop_orders": [
            {
                "id": str(shop_order.pk),
                "shop_order_code": shop_order.shop_order_code,
                "shop_name": shop_order.shop.name,
                "fulfillment_status": shop_order.fulfillment_status,
                "fulfillment_status_label": shop_order.get_fulfillment_status_display(),
                "shipping_method": shop_order.shipping_method_name or "Chưa cập nhật",
                "last_status_at": shop_order.updated_at.isoformat(),
                "items": [
                    {
                        "id": str(item.pk),
                        "name": item.product_name,
                        "variant": item.variant_name,
                        "quantity": item.quantity,
                    }
                    for item in shop_order.items.all()
                ],
            }
            for shop_order in order.shop_orders.all()
        ],
    }


def _policy_category(topic: str) -> str | None:
    normalized = " ".join(_normalize_words(topic))
    mapping = {
        PolicyDocument.Category.SHIPPING: ("giao hang", "van chuyen", "phi ship"),
        PolicyDocument.Category.RETURN: ("doi tra", "tra hang", "hoan tien"),
        PolicyDocument.Category.PAYMENT: ("thanh toan", "cod", "vnpay"),
        PolicyDocument.Category.WARRANTY: ("bao hanh",),
    }
    return next(
        (
            category
            for category, phrases in mapping.items()
            if any(phrase in normalized for phrase in phrases)
        ),
        None,
    )


def _normalize_words(value: str) -> list[str]:
    import unicodedata

    decomposed = unicodedata.normalize("NFD", value.casefold())
    ascii_value = "".join(
        character for character in decomposed if not unicodedata.combining(character)
    ).replace("đ", "d")
    return "".join(character if character.isalnum() else " " for character in ascii_value).split()


def _normalized_text(value: str) -> str:
    return " ".join(_normalize_words(value))


def _contains_normalized_phrase(value: str, phrase: str) -> bool:
    normalized_value = f" {_normalized_text(value)} "
    normalized_phrase = _normalized_text(phrase)
    return bool(normalized_phrase and f" {normalized_phrase} " in normalized_value)
