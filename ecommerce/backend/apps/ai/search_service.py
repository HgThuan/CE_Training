import math
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from django.conf import settings
from django.db import DatabaseError, connections
from django.db.models import QuerySet, Subquery

from apps.common.models import SiteSetting
from apps.product.models import Product
from apps.product.selectors import ProductSelector, SearchSelector
from apps.product.serializers import SearchFilterSerializer

from .models import ProductEmbedding
from .services import AIService

try:
    from pgvector.django import CosineDistance
except ImportError:  # pragma: no cover - production dependency, retained for safe startup
    CosineDistance = None


AI_SEARCH_FEATURE_KEY = "feature.ai_search.enabled"
ALLOWED_INTENT_FILTERS = {
    "category",
    "brand",
    "price_min",
    "price_max",
    "rating_min",
    "in_stock",
    "shop",
}
MAX_INTENT_KEYWORDS = 8
MAX_SEMANTIC_CANDIDATES = 500


@dataclass(frozen=True, slots=True)
class SearchOutcome:
    products: QuerySet[Product] | list[Product]
    explanation: str
    intent: dict[str, Any]
    ai_used: bool
    fallback_used: bool


class AISearchService:
    @staticmethod
    def is_enabled() -> bool:
        if not settings.AI_FEATURES_ENABLED:
            return False
        try:
            return SiteSetting.get_bool(
                AI_SEARCH_FEATURE_KEY,
                default=settings.AI_FEATURES_ENABLED,
            )
        except DatabaseError:
            # Deployments can briefly reach this code before the setting migration.
            return bool(settings.AI_FEATURES_ENABLED)

    @classmethod
    def smart_search(
        cls,
        *,
        query: str,
        user=None,
        filters: dict[str, Any] | None = None,
    ) -> SearchOutcome:
        normalized_query = query.strip()
        explicit_filters = cls._explicit_filters(filters)
        if not cls.is_enabled():
            return cls._keyword_fallback(
                query=normalized_query,
                explanation="AI Search đang tắt; kết quả dùng tìm kiếm từ khóa.",
                filters=explicit_filters,
            )

        try:
            raw_intent = AIService().extract_search_intent(
                normalized_query,
                user=user,
            )
        except Exception:
            return cls._keyword_fallback(
                query=normalized_query,
                explanation="Không thể phân tích nhu cầu; kết quả dùng tìm kiếm từ khóa.",
                filters=explicit_filters,
            )

        intent, params, intent_valid = cls._normalize_intent(
            raw_intent,
            query=normalized_query,
            explicit_filters=explicit_filters,
        )
        products = SearchSelector.search(params)
        raw_mapping = raw_intent if isinstance(raw_intent, dict) else {}
        ai_used = bool(raw_mapping.get("ai_used")) and intent_valid
        fallback_used = bool(raw_mapping.get("fallback_used")) or not ai_used or not intent_valid
        explanation = cls._safe_explanation(raw_mapping.get("explanation"))
        if not explanation:
            explanation = (
                "AI đã phân tích từ khóa và bộ lọc phù hợp."
                if ai_used
                else "Kết quả dùng tìm kiếm từ khóa."
            )
        return SearchOutcome(
            products=products,
            explanation=explanation,
            intent=intent,
            ai_used=ai_used,
            fallback_used=fallback_used,
        )

    @classmethod
    def semantic_search(
        cls,
        *,
        query: str,
        user=None,
        filters: dict[str, Any] | None = None,
    ) -> SearchOutcome:
        normalized_query = query.strip()
        explicit_filters = cls._explicit_filters(filters)
        effective_filters = {**explicit_filters, "in_stock": True}
        base_intent = {
            "keywords": [normalized_query],
            "filters": cls._json_safe_filters(
                {
                    key: value
                    for key, value in effective_filters.items()
                    if key in ALLOWED_INTENT_FILTERS
                }
            ),
        }
        if not cls.is_enabled():
            return cls._keyword_fallback(
                query=normalized_query,
                explanation="AI Search đang tắt; kết quả dùng tìm kiếm từ khóa.",
                in_stock=True,
                intent=base_intent,
                filters=effective_filters,
            )
        if not cls._supports_vector_search():
            return cls._keyword_fallback(
                query=normalized_query,
                explanation=(
                    "Semantic Search chưa khả dụng trên cơ sở dữ liệu này; "
                    "kết quả dùng tìm kiếm từ khóa."
                ),
                in_stock=True,
                intent=base_intent,
                filters=effective_filters,
            )

        try:
            embedding_result = AIService().get_embedding(
                feature="semantic_search",
                text=normalized_query,
                task_type="retrieval_query",
                user=user,
                fallback=[],
            )
            vector = list(embedding_result.vector or [])
            if (
                embedding_result.fallback_used
                or not embedding_result.ai_used
                or len(vector) != settings.AI_EMBEDDING_DIMENSIONS
                or not all(
                    isinstance(value, (int, float))
                    and not isinstance(value, bool)
                    and math.isfinite(float(value))
                    for value in vector
                )
            ):
                raise ValueError("A usable query embedding was not produced")
            products = cls._postgres_semantic_products(
                vector=vector,
                model_name=embedding_result.model_name,
                filters=effective_filters,
            )
            if not products:
                raise ValueError("No indexed public products are available")
        except Exception:
            return cls._keyword_fallback(
                query=normalized_query,
                explanation=(
                    "Semantic Search tạm thời không khả dụng; kết quả dùng tìm kiếm từ khóa."
                ),
                in_stock=True,
                intent=base_intent,
                filters=effective_filters,
            )

        return SearchOutcome(
            products=products,
            explanation="AI xếp hạng sản phẩm theo mức độ tương đồng về ý nghĩa.",
            intent=base_intent,
            ai_used=True,
            fallback_used=False,
        )

    @staticmethod
    def _supports_vector_search() -> bool:
        return CosineDistance is not None and connections["default"].vendor == "postgresql"

    @staticmethod
    def _postgres_semantic_candidates(
        *,
        vector: list[float],
        model_name: str,
        filters: dict[str, Any],
    ) -> QuerySet[ProductEmbedding]:
        public_filter_params = {
            key: value for key, value in filters.items() if key in ALLOWED_INTENT_FILTERS
        }
        public_product_ids = SearchSelector.search(public_filter_params).order_by().values("pk")
        distance = CosineDistance("embedding", vector)
        return (
            ProductEmbedding.objects.filter(
                product_id__in=Subquery(public_product_ids),
                variant__isnull=True,
                language_code="vi",
                model_name=model_name,
            )
            .annotate(vector_distance=distance)
            # Keep the indexed distance operator as the direct ORDER BY
            # expression. Wrapping it in the hybrid score prevents PostgreSQL
            # from selecting the pgvector HNSW index.
            .order_by(distance)[:MAX_SEMANTIC_CANDIDATES]
        )

    @classmethod
    def _postgres_semantic_products(
        cls,
        *,
        vector: list[float],
        model_name: str,
        filters: dict[str, Any],
    ) -> list[Product]:
        candidate_rows = cls._postgres_semantic_candidates(
            vector=vector,
            model_name=model_name,
            filters=filters,
        ).values_list("product_id", "vector_distance")
        distance_by_product_id: dict[Any, float] = {}
        for product_id, raw_distance in candidate_rows:
            distance = float(raw_distance)
            if not math.isfinite(distance):
                continue
            previous_distance = distance_by_product_id.get(product_id)
            if previous_distance is None or distance < previous_distance:
                distance_by_product_id[product_id] = distance

        if not distance_by_product_id:
            return []

        products = ProductSelector.public_list().filter(pk__in=distance_by_product_id)
        sort = filters.get("sort")
        if sort and sort != "relevance":
            return list(
                products.order_by(
                    *ProductSelector.SORT_EXPRESSIONS[sort],
                    "id",
                )
            )
        products = list(products)

        def hybrid_sort_key(product: Product) -> tuple[float, int, str]:
            distance = distance_by_product_id[product.pk]
            rating = float(product.rating_average or 0)
            hybrid_score = (1.0 - distance) * 0.9 + (rating / 5.0) * 0.1
            return (-hybrid_score, -int(product.sold_count or 0), str(product.pk))

        return sorted(products, key=hybrid_sort_key)

    @classmethod
    def _normalize_intent(
        cls,
        raw_intent: Any,
        *,
        query: str,
        explicit_filters: dict[str, Any],
    ) -> tuple[dict[str, Any], dict[str, Any], bool]:
        if not isinstance(raw_intent, dict):
            fallback_params = {"q": query, **explicit_filters}
            fallback_params.setdefault("sort", "relevance")
            return (
                {
                    "keywords": [query],
                    "filters": cls._json_safe_filters(
                        {
                            key: value
                            for key, value in explicit_filters.items()
                            if key in ALLOWED_INTENT_FILTERS
                        }
                    ),
                },
                fallback_params,
                False,
            )

        raw_keywords = raw_intent.get("keywords")
        if isinstance(raw_keywords, str):
            raw_keywords = [raw_keywords]
        keywords: list[str] = []
        if isinstance(raw_keywords, list):
            for value in raw_keywords[:MAX_INTENT_KEYWORDS]:
                if not isinstance(value, str):
                    continue
                normalized = " ".join(value.split())[:100]
                if normalized and normalized.casefold() not in {
                    keyword.casefold() for keyword in keywords
                }:
                    keywords.append(normalized)

        raw_filters = raw_intent.get("filters")
        filters = (
            {key: value for key, value in raw_filters.items() if key in ALLOWED_INTENT_FILTERS}
            if isinstance(raw_filters, dict)
            else {}
        )
        candidate_params: dict[str, Any] = {
            **filters,
            "q": " ".join(keywords),
            **explicit_filters,
        }
        if candidate_params.get("q"):
            candidate_params.setdefault("sort", "relevance")
        validator = SearchFilterSerializer(data=candidate_params)
        if not validator.is_valid():
            return (
                {
                    "keywords": keywords,
                    "filters": cls._json_safe_filters(
                        {
                            key: value
                            for key, value in explicit_filters.items()
                            if key in ALLOWED_INTENT_FILTERS
                        }
                    ),
                },
                {
                    "q": query,
                    **explicit_filters,
                    "sort": explicit_filters.get("sort", "relevance"),
                },
                False,
            )

        validated = dict(validator.validated_data)
        validated_filters = {
            key: value for key, value in validated.items() if key in ALLOWED_INTENT_FILTERS
        }
        return (
            {
                "keywords": keywords,
                "filters": cls._json_safe_filters(validated_filters),
            },
            validated,
            True,
        )

    @staticmethod
    def _json_safe_filters(filters: dict[str, Any]) -> dict[str, Any]:
        return {
            key: str(value) if isinstance(value, Decimal) else value
            for key, value in filters.items()
        }

    @staticmethod
    def _safe_explanation(value: Any) -> str:
        if not isinstance(value, str):
            return ""
        return " ".join(value.split())[:500]

    @staticmethod
    def _explicit_filters(filters: dict[str, Any] | None) -> dict[str, Any]:
        if not filters:
            return {}
        return {
            key: value
            for key, value in filters.items()
            if key in ALLOWED_INTENT_FILTERS or key == "sort"
        }

    @staticmethod
    def _keyword_fallback(
        *,
        query: str,
        explanation: str,
        in_stock: bool = False,
        intent: dict[str, Any] | None = None,
        filters: dict[str, Any] | None = None,
    ) -> SearchOutcome:
        params: dict[str, Any] = {"q": query, **(filters or {})}
        params.setdefault("sort", "relevance")
        if in_stock:
            params["in_stock"] = True
        effective_intent = intent or {
            "keywords": [query],
            "filters": AISearchService._json_safe_filters(
                {
                    key: value
                    for key, value in (filters or {}).items()
                    if key in ALLOWED_INTENT_FILTERS
                }
            ),
        }
        return SearchOutcome(
            products=SearchSelector.search(params),
            explanation=explanation,
            intent=effective_intent,
            ai_used=False,
            fallback_used=True,
        )
