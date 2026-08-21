import math
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from django.conf import settings
from django.db import DatabaseError, connections
from django.db.models import Q, QuerySet, Subquery

from apps.common.models import SiteSetting
from apps.product.models import Product, ProductAttributeValue
from apps.product.selectors import ProductSelector, SearchSelector
from apps.product.serializers import SearchFilterSerializer

from .db_capabilities import product_embedding_table_available
from .models import ProductEmbedding
from .search_intent import SearchIntentParser, StructuredSearchIntent
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
MAX_EXPLANATION_PRODUCTS = 100


@dataclass(frozen=True, slots=True)
class SearchOutcome:
    products: QuerySet[Product] | list[Product]
    explanation: str
    intent: dict[str, Any]
    ai_used: bool
    fallback_used: bool
    match_reasons: dict[str, str] = field(default_factory=dict)


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
        structured = SearchIntentParser.parse(
            query=normalized_query,
            raw_intent=raw_intent,
            validated_filters=params,
        )
        intent = structured.as_dict()
        products = cls._smart_products(params=params, intent=structured)
        raw_mapping = raw_intent if isinstance(raw_intent, dict) else {}
        ai_used = bool(raw_mapping.get("ai_used")) and intent_valid
        fallback_used = bool(raw_mapping.get("fallback_used")) or not ai_used or not intent_valid
        # Never expose a free-form model explanation. This text is assembled
        # solely from validated slots and catalog constraints.
        explanation = SearchIntentParser.controlled_explanation(structured)
        return SearchOutcome(
            products=products,
            explanation=explanation,
            intent=intent,
            ai_used=ai_used,
            fallback_used=fallback_used,
            match_reasons=cls._controlled_match_reasons(products, structured),
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
        raw_intent: dict[str, Any] = {}
        try:
            raw_intent = AIService().extract_search_intent(normalized_query, user=user)
        except Exception:
            raw_intent = {}
        _normalized, validated_params, _intent_valid = cls._normalize_intent(
            raw_intent,
            query=normalized_query,
            explicit_filters=effective_filters,
        )
        structured = SearchIntentParser.parse(
            query=normalized_query,
            raw_intent=raw_intent,
            validated_filters=validated_params,
        )
        base_intent = structured.as_dict()
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
                text=structured.expanded_query or normalized_query,
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
                query=normalized_query,
                intent=structured,
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
            explanation=SearchIntentParser.controlled_explanation(structured),
            intent=base_intent,
            ai_used=True,
            fallback_used=False,
            match_reasons=cls._controlled_match_reasons(products, structured),
        )

    @staticmethod
    def _supports_vector_search() -> bool:
        return (
            CosineDistance is not None
            and connections["default"].vendor == "postgresql"
            and product_embedding_table_available()
        )

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
        query: str = "",
        intent: StructuredSearchIntent | None = None,
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
            similarity = 1.0 - distance
            if similarity < float(
                getattr(settings, "AI_SEARCH_MIN_COSINE_SIMILARITY", 0.30)
            ):
                continue
            previous_distance = distance_by_product_id.get(product_id)
            if previous_distance is None or distance < previous_distance:
                distance_by_product_id[product_id] = distance

        if not distance_by_product_id and not query:
            return []

        keyword_rank: dict[Any, int] = {}
        if query:
            keyword_params = {
                key: value for key, value in filters.items() if key in ALLOWED_INTENT_FILTERS
            }
            keyword_params.update({"q": query, "sort": "relevance"})
            for rank, product_id in enumerate(
                SearchSelector.search(keyword_params)
                .order_by("-relevance", "id")
                .values_list("pk", flat=True)[:MAX_SEMANTIC_CANDIDATES],
                1,
            ):
                keyword_rank[product_id] = rank

        candidate_ids = set(distance_by_product_id) | set(keyword_rank)
        if not candidate_ids:
            return []
        products = ProductSelector.public_list().filter(pk__in=candidate_ids)
        sort = filters.get("sort")
        if sort and sort != "relevance":
            return list(
                products.order_by(
                    *ProductSelector.SORT_EXPRESSIONS[sort],
                    "id",
                )
            )
        products = list(products)

        if not query:
            # Backward-compatible internal call path; public semantic search
            # always supplies the query and therefore uses RRF below.
            return sorted(
                products,
                key=lambda product: (
                    -(
                        (1.0 - distance_by_product_id[product.pk]) * 0.9
                        + (float(product.rating_average or 0) / 5.0) * 0.1
                    ),
                    -int(product.sold_count or 0),
                    str(product.pk),
                ),
            )

        semantic_order = sorted(distance_by_product_id, key=distance_by_product_id.get)
        semantic_rank = {product_id: rank for rank, product_id in enumerate(semantic_order, 1)}

        rrf_k = max(1, int(getattr(settings, "AI_SEARCH_RRF_K", 60)))
        semantic_weight = max(0.0, float(getattr(settings, "AI_SEARCH_SEMANTIC_WEIGHT", 0.65)))
        keyword_weight = max(0.0, float(getattr(settings, "AI_SEARCH_KEYWORD_WEIGHT", 0.35)))

        def hybrid_sort_key(product: Product) -> tuple[float, int, str]:
            score = 0.0
            if product.pk in semantic_rank:
                score += semantic_weight / (rrf_k + semantic_rank[product.pk])
            if product.pk in keyword_rank:
                score += keyword_weight / (rrf_k + keyword_rank[product.pk])
            # Deterministic top-k reranking uses only verified catalog fields.
            if intent and cls._product_matches_category_hint(product, intent):
                score += 0.002
            score += min(float(product.rating_average or 0) / 5.0, 1.0) * 0.0001
            return (-score, -int(product.sold_count or 0), str(product.pk))

        return sorted(products, key=hybrid_sort_key)

    @classmethod
    def _smart_products(
        cls,
        *,
        params: dict[str, Any],
        intent: StructuredSearchIntent,
    ) -> QuerySet[Product] | list[Product]:
        products = SearchSelector.search(params)
        if not intent.category_hints or products.exists():
            return products
        # Vague queries such as "quà sinh nhật cho bạn gái" may not contain a
        # literal catalog term. Fall back to inferred category/name hints while
        # retaining every validated public/price/stock filter.
        filter_params = {
            key: value
            for key, value in params.items()
            if key in ALLOWED_INTENT_FILTERS or key == "sort"
        }
        filter_params.pop("sort", None)
        hinted = SearchSelector.search(filter_params)
        hint_filter = Q()
        for hint in intent.category_hints:
            hint_filter |= Q(category__name__icontains=hint)
            hint_filter |= Q(name__icontains=hint)
            hint_filter |= Q(short_description__icontains=hint)
        return hinted.filter(hint_filter).order_by(
            "-sold_count", "-rating_average", "-created_at", "id"
        )

    @staticmethod
    def _product_matches_category_hint(
        product: Product,
        intent: StructuredSearchIntent,
    ) -> bool:
        haystack = " ".join(
            (
                product.name or "",
                product.category.name if product.category_id else "",
                product.brand.name if product.brand_id else "",
            )
        ).casefold()
        return any(hint.casefold() in haystack for hint in intent.category_hints)

    @classmethod
    def _controlled_match_reasons(
        cls,
        products: QuerySet[Product] | list[Product],
        intent: StructuredSearchIntent,
    ) -> dict[str, str]:
        sample = list(products[:MAX_EXPLANATION_PRODUCTS])
        reasons: dict[str, str] = {}
        attribute_text_by_product: dict[Any, list[str]] = {}
        attribute_rows = ProductAttributeValue.objects.filter(
            product_id__in=[product.pk for product in sample]
        ).values_list(
            "product_id",
            "attribute_value__attribute__name",
            "attribute_value__value",
            "attribute_value__display_value",
        )
        for product_id, attribute_name, value, display_value in attribute_rows:
            attribute_text_by_product.setdefault(product_id, []).extend(
                (attribute_name, display_value or value)
            )
        price_min = intent.filters.get("price_min")
        price_max = intent.filters.get("price_max")
        for product in sample:
            verified: list[str] = []
            if cls._product_matches_category_hint(product, intent):
                verified.append(f"thuộc nhóm {product.category.name}")
            product_min = getattr(product, "min_price", None)
            product_max = getattr(product, "max_price", None)
            if product_min is not None and (
                (price_min is None or product_max is None or product_max >= price_min)
                and (price_max is None or product_min <= price_max)
            ) and (price_min is not None or price_max is not None):
                verified.append("nằm trong khoảng giá đã chọn")
            if intent.attributes:
                actual_text = " ".join(
                    filter(
                        None,
                        (
                            product.name,
                            product.short_description,
                            product.description,
                            *attribute_text_by_product.get(product.pk, []),
                        ),
                    )
                ).casefold()
                matched = [
                    value
                    for values in intent.attributes.values()
                    for value in values
                    if value.casefold() in actual_text
                ]
                if matched:
                    verified.append("khớp " + ", ".join(matched[:2]))
            if not verified:
                verified.append("khớp nội dung tìm kiếm trong dữ liệu sản phẩm")
            reasons[str(product.pk)] = "Gợi ý vì " + "; ".join(verified[:2]) + "."
        return reasons

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

    @classmethod
    def _keyword_fallback(
        cls,
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
        structured = SearchIntentParser.parse(
            query=query,
            raw_intent={},
            validated_filters=filters or {},
        )
        effective_intent = intent or structured.as_dict()
        products = SearchSelector.search(params)
        return SearchOutcome(
            products=products,
            explanation=explanation,
            intent=effective_intent,
            ai_used=False,
            fallback_used=True,
            match_reasons=cls._controlled_match_reasons(products, structured),
        )
