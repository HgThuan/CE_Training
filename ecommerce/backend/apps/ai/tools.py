import logging
import unicodedata
import uuid
from decimal import Decimal, InvalidOperation
from typing import Any

from django.conf import settings
from django.db import DatabaseError, connections
from django.db.models import Avg, Count, Q

from apps.catalog.models import Category
from apps.common.exceptions import BusinessError
from apps.product.models import ProductAttributeValue, VariantAttributeValue
from apps.product.selectors import ProductSelector, SearchSelector
from apps.product.serializers import PublicProductListSerializer
from apps.review.models import Review

from .models import AIRequestLog, PolicyDocument, sanitize_ai_text
from .product_matching import assess_product_matches
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
