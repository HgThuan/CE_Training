import math
from collections import Counter
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID, uuid4

from django.conf import settings
from django.db import DatabaseError, connections
from django.db.models import Q, Subquery

from apps.account.models import User
from apps.catalog.models import Category
from apps.common.cache_utils import (
    build_cache_key,
    canonical_sha256,
    safe_cache_get,
    safe_cache_set,
)
from apps.common.models import SiteSetting
from apps.engagement.models import WishlistItem
from apps.product.models import Product
from apps.product.selectors import ProductSelector, SearchSelector

from .db_capabilities import product_embedding_table_available
from .models import ProductEmbedding, RecommendationProfile

try:
    from pgvector.django import CosineDistance
except ImportError:  # pragma: no cover - required in production, safe at startup
    CosineDistance = None


AI_RECOMMENDATION_FEATURE_KEY = "feature.ai_recommendation.enabled"
RECOMMENDATION_ALGORITHM_VERSION = "realtime-batch-v2"
RECOMMENDATION_CACHE_TTL_SECONDS = 15 * 60
SIMILAR_CACHE_TTL_SECONDS = 30 * 60
MAX_BROWSING_HISTORY = 20
MAX_VECTOR_CANDIDATES = 500
MAX_RECOMMENDATION_RESULTS = 100
_CACHE_MISS = object()


@dataclass(frozen=True, slots=True)
class RecommendationOutcome:
    products: list[Product]
    ai_used: bool
    fallback_used: bool
    personalized: bool
    strategy: str
    recommendation_id: str = field(default_factory=lambda: str(uuid4()))
    cached: bool = False


@dataclass(frozen=True, slots=True)
class _Signals:
    context_product: Product | None
    browsing_ids: tuple[UUID, ...]
    cart_ids: tuple[UUID, ...]
    wishlist_ids: tuple[UUID, ...]
    user_identity: str
    landing_context: str
    traffic_source: str

    @property
    def excluded_ids(self) -> set[UUID]:
        excluded = set(self.browsing_ids)
        excluded.update(self.cart_ids)
        excluded.update(self.wishlist_ids)
        if self.context_product is not None:
            excluded.add(self.context_product.pk)
        return excluded

    @property
    def ordered_product_ids(self) -> tuple[UUID, ...]:
        ordered: list[UUID] = []
        if self.context_product is not None:
            ordered.append(self.context_product.pk)
        ordered.extend(self.cart_ids)
        ordered.extend(self.browsing_ids)
        ordered.extend(self.wishlist_ids)
        return tuple(dict.fromkeys(ordered))


class RecommendationService:
    """Rank stored product embeddings and deterministic SQL fallbacks.

    This service deliberately never invokes ``AIService`` or an external
    provider on the request path. Vector recommendations use only embeddings
    that were indexed asynchronously.
    """

    @staticmethod
    def is_vector_enabled() -> bool:
        if not settings.AI_FEATURES_ENABLED:
            return False
        if CosineDistance is None or connections["default"].vendor != "postgresql":
            return False
        if not product_embedding_table_available():
            return False
        try:
            return SiteSetting.get_bool(
                AI_RECOMMENDATION_FEATURE_KEY,
                default=settings.AI_FEATURES_ENABLED,
            )
        except DatabaseError:
            return False

    @classmethod
    def recommendations(
        cls,
        *,
        context_product: Product | None = None,
        browsing_ids: list[UUID] | tuple[UUID, ...] = (),
        cart_ids: list[UUID] | tuple[UUID, ...] = (),
        landing_context: str = "home",
        traffic_source: str = "direct",
        user: Any = None,
    ) -> RecommendationOutcome:
        signals = cls._build_signals(
            context_product=context_product,
            browsing_ids=browsing_ids,
            cart_ids=cart_ids,
            landing_context=landing_context,
            traffic_source=traffic_source,
            user=user,
        )
        vector_enabled = cls.is_vector_enabled()
        cache_key = cls._cache_key(
            kind="recommendations",
            signals=signals,
            vector_enabled=vector_enabled,
        )
        cached = cls._cached_outcome(cache_key, vector_enabled=vector_enabled)
        if cached is not None:
            return cached

        category_preferences, brand_preferences = cls._preferences(signals)
        batch_profile = cls._batch_profile(user)
        category_preferences = cls._merge_ranked(
            category_preferences,
            cls._weighted_profile_ids(batch_profile, "category_weights"),
        )
        brand_preferences = cls._merge_ranked(
            brand_preferences,
            cls._weighted_profile_ids(batch_profile, "brand_weights"),
        )
        if not signals.ordered_product_ids and not category_preferences:
            category_preferences = cls._cold_start_categories(
                user=user,
                landing_context=signals.landing_context,
                traffic_source=signals.traffic_source,
            )
        vector_ids: list[UUID] = []
        if vector_enabled:
            centroid = cls._centroid_for_signals(signals)
            if centroid is not None:
                vector_ids = cls._postgres_vector_product_ids(
                    vector=centroid,
                    excluded_ids=signals.excluded_ids,
                    category_preferences=category_preferences,
                    brand_preferences=brand_preferences,
                )

        ordered_ids = list(vector_ids)
        batch_ids = cls._batch_product_ids(batch_profile, excluded_ids=signals.excluded_ids)
        ordered_ids.extend(product_id for product_id in batch_ids if product_id not in ordered_ids)
        fallback_ids = cls._fallback_recommendation_ids(
            excluded_ids=signals.excluded_ids | set(ordered_ids),
            category_preferences=category_preferences,
            brand_preferences=brand_preferences,
            limit=MAX_RECOMMENDATION_RESULTS - len(ordered_ids),
        )
        ordered_ids.extend(fallback_ids)
        ordered_ids = ordered_ids[:MAX_RECOMMENDATION_RESULTS]

        ai_used = bool(vector_ids)
        fallback_used = not ai_used or bool(fallback_ids)
        personalized = bool(signals.ordered_product_ids or batch_profile)
        if vector_ids and batch_ids:
            strategy = "hybrid_realtime_batch"
        elif ai_used and fallback_ids:
            strategy = "realtime_vector_with_fallback"
        elif ai_used:
            strategy = "realtime_vector"
        elif batch_ids:
            strategy = "batch_collaborative"
        elif category_preferences or brand_preferences:
            strategy = (
                "cold_start_context"
                if not signals.ordered_product_ids
                else "fallback_preferences"
            )
        else:
            strategy = "fallback_best_sellers"
        outcome = RecommendationOutcome(
            products=cls._rehydrate(ordered_ids),
            ai_used=ai_used,
            fallback_used=fallback_used,
            personalized=personalized,
            strategy=strategy,
        )
        cls._cache_outcome(
            cache_key,
            outcome,
            vector_enabled=vector_enabled,
            timeout=getattr(
                settings,
                "AI_RECOMMENDATION_CACHE_TTL_SECONDS",
                RECOMMENDATION_CACHE_TTL_SECONDS,
            ),
        )
        return outcome

    @classmethod
    def similar_products(
        cls,
        *,
        context_product: Product,
        browsing_ids: list[UUID] | tuple[UUID, ...] = (),
        user: Any = None,
    ) -> RecommendationOutcome:
        # Similar-product ranking is global and depends only on the public
        # anchor. Browsing and wishlist data must not personalize it.
        signals = _Signals(
            context_product=context_product,
            browsing_ids=(),
            cart_ids=(),
            wishlist_ids=(),
            user_identity="anonymous",
            landing_context="product_detail",
            traffic_source="direct",
        )
        vector_enabled = cls.is_vector_enabled()
        cache_key = cls._cache_key(
            kind="similar",
            signals=signals,
            vector_enabled=vector_enabled,
        )
        cached = cls._cached_outcome(cache_key, vector_enabled=vector_enabled)
        if cached is not None:
            return cached

        vector_ids: list[UUID] = []
        if vector_enabled:
            vector = cls._embedding_for_product(context_product.pk)
            if vector is not None:
                vector_ids = cls._postgres_vector_product_ids(
                    vector=vector,
                    excluded_ids=signals.excluded_ids,
                    category_preferences=(context_product.category_id,),
                    brand_preferences=(
                        (context_product.brand_id,) if context_product.brand_id else ()
                    ),
                    min_similarity=float(
                        getattr(settings, "AI_SIMILAR_MIN_COSINE_SIMILARITY", 0.45)
                    ),
                )

        ordered_ids = list(vector_ids)
        fallback_ids = cls._fallback_similar_ids(
            context_product=context_product,
            excluded_ids=signals.excluded_ids | set(ordered_ids),
            limit=MAX_RECOMMENDATION_RESULTS - len(ordered_ids),
        )
        ordered_ids.extend(fallback_ids)
        ordered_ids = ordered_ids[:MAX_RECOMMENDATION_RESULTS]

        ai_used = bool(vector_ids)
        fallback_used = not ai_used or bool(fallback_ids)
        if ai_used and fallback_ids:
            strategy = "vector_similar_with_fallback"
        elif ai_used:
            strategy = "vector_similar"
        else:
            strategy = "fallback_similar"
        outcome = RecommendationOutcome(
            products=cls._rehydrate(ordered_ids),
            ai_used=ai_used,
            fallback_used=fallback_used,
            personalized=False,
            strategy=strategy,
        )
        cls._cache_outcome(
            cache_key,
            outcome,
            vector_enabled=vector_enabled,
            timeout=getattr(
                settings,
                "AI_SIMILAR_CACHE_TTL_SECONDS",
                SIMILAR_CACHE_TTL_SECONDS,
            ),
        )
        return outcome

    @classmethod
    def _build_signals(
        cls,
        *,
        context_product: Product | None,
        browsing_ids: list[UUID] | tuple[UUID, ...],
        cart_ids: list[UUID] | tuple[UUID, ...] = (),
        landing_context: str = "home",
        traffic_source: str = "direct",
        user: Any,
    ) -> _Signals:
        normalized_browsing = tuple(
            dict.fromkeys(UUID(str(product_id)) for product_id in browsing_ids)
        )[:MAX_BROWSING_HISTORY]
        normalized_cart = tuple(
            dict.fromkeys(UUID(str(product_id)) for product_id in cart_ids)
        )[:MAX_BROWSING_HISTORY]
        wishlist_ids = cls._wishlist_ids(user)
        return _Signals(
            context_product=context_product,
            browsing_ids=normalized_browsing,
            cart_ids=normalized_cart,
            wishlist_ids=wishlist_ids,
            user_identity=cls._user_identity(user),
            landing_context=str(landing_context or "home")[:40],
            traffic_source=str(traffic_source or "direct")[:80],
        )

    @staticmethod
    def _eligible_customer(user: Any) -> bool:
        return bool(
            user
            and getattr(user, "is_authenticated", False)
            and getattr(user, "role", None) == User.Role.CUSTOMER
            and getattr(user, "is_active", False)
            and not getattr(user, "is_deleted", True)
        )

    @classmethod
    def _wishlist_ids(cls, user: Any) -> tuple[UUID, ...]:
        if not cls._eligible_customer(user):
            return ()
        product_ids = WishlistItem.objects.filter(
            wishlist__user_id=user.pk,
        ).values_list("product_id", flat=True)
        # Wishlist order is not a ranking input. Sorting makes both the
        # centroid and its cache fingerprint independent of row timestamps.
        return tuple(sorted(set(product_ids), key=str))

    @staticmethod
    def _user_identity(user: Any) -> str:
        return (
            f"customer:{user.pk}" if RecommendationService._eligible_customer(user) else "anonymous"
        )

    @classmethod
    def _preferences(
        cls,
        signals: _Signals,
    ) -> tuple[tuple[UUID, ...], tuple[UUID, ...]]:
        signal_ids = signals.ordered_product_ids
        products_by_id = {
            product.pk: product
            for product in ProductSelector.public_base()
            .filter(pk__in=signal_ids)
            .only("id", "category_id", "brand_id")
        }
        category_counts: Counter[UUID] = Counter()
        brand_counts: Counter[UUID] = Counter()
        for product_id in signal_ids:
            product = products_by_id.get(product_id)
            if product is None:
                continue
            category_counts[product.category_id] += 1
            if product.brand_id is not None:
                brand_counts[product.brand_id] += 1

        def ranked(counter: Counter[UUID]) -> tuple[UUID, ...]:
            return tuple(
                value
                for value, _count in sorted(
                    counter.items(),
                    key=lambda item: (-item[1], str(item[0])),
                )
            )

        return ranked(category_counts), ranked(brand_counts)

    @classmethod
    def _batch_profile(cls, user: Any) -> RecommendationProfile | None:
        if not cls._eligible_customer(user):
            return None
        return RecommendationProfile.objects.filter(user_id=user.pk).first()

    @staticmethod
    def _weighted_profile_ids(
        profile: RecommendationProfile | None,
        field_name: str,
    ) -> tuple[UUID, ...]:
        if profile is None:
            return ()
        raw = getattr(profile, field_name, {})
        if not isinstance(raw, dict):
            return ()
        parsed: list[tuple[UUID, float]] = []
        for raw_id, raw_weight in raw.items():
            try:
                parsed.append((UUID(str(raw_id)), float(raw_weight)))
            except (TypeError, ValueError, OverflowError):
                continue
        return tuple(item[0] for item in sorted(parsed, key=lambda item: (-item[1], str(item[0]))))

    @staticmethod
    def _merge_ranked(*groups: tuple[UUID, ...]) -> tuple[UUID, ...]:
        return tuple(dict.fromkeys(item for group in groups for item in group))

    @staticmethod
    def _batch_product_ids(
        profile: RecommendationProfile | None,
        *,
        excluded_ids: set[UUID],
    ) -> list[UUID]:
        if profile is None or not isinstance(profile.related_product_ids, list):
            return []
        result: list[UUID] = []
        for raw_id in profile.related_product_ids[:MAX_RECOMMENDATION_RESULTS]:
            try:
                product_id = UUID(str(raw_id))
            except (TypeError, ValueError):
                continue
            if product_id not in excluded_ids and product_id not in result:
                result.append(product_id)
        return result

    @classmethod
    def _cold_start_categories(
        cls,
        *,
        user: Any,
        landing_context: str,
        traffic_source: str,
    ) -> tuple[UUID, ...]:
        from django.utils import timezone

        terms: list[str] = []
        context = f"{landing_context} {traffic_source}".casefold()
        context_rules = {
            "beauty": ("mỹ phẩm", "làm đẹp"),
            "fashion": ("thời trang", "phụ kiện"),
            "electronics": ("điện tử", "điện thoại", "máy tính"),
            "gift": ("quà tặng", "phụ kiện"),
        }
        for marker, categories in context_rules.items():
            if marker in context:
                terms.extend(categories)
        month = timezone.localdate().month
        if month in {11, 12, 1}:
            terms.extend(("quà tặng", "thời trang"))
        elif month in {5, 6, 7, 8}:
            terms.extend(("du lịch", "thời trang"))
        if cls._eligible_customer(user):
            if user.gender == User.Gender.FEMALE:
                terms.extend(("mỹ phẩm", "thời trang nữ"))
            elif user.gender == User.Gender.MALE:
                terms.extend(("thời trang nam", "điện tử"))
        query = Q()
        for term in dict.fromkeys(terms):
            query |= Q(name__icontains=term)
        if not query:
            return ()
        return tuple(
            Category.objects.filter(query, is_active=True, is_deleted=False)
            .order_by("sort_order", "name", "id")
            .values_list("pk", flat=True)[:20]
        )

    @classmethod
    def _centroid_for_signals(cls, signals: _Signals) -> list[float] | None:
        weighted_ids: list[UUID] = []
        if signals.context_product is not None:
            weighted_ids.extend([signals.context_product.pk] * 4)
        for product_id in signals.cart_ids:
            weighted_ids.extend([product_id] * 3)
        for index, product_id in enumerate(signals.browsing_ids):
            weighted_ids.extend([product_id] * (2 if index < 5 else 1))
        weighted_ids.extend(signals.wishlist_ids)
        ordered_signal_ids = tuple(dict.fromkeys(weighted_ids))
        weight_by_id = Counter(weighted_ids)
        public_ids = set(
            ProductSelector.public_base()
            .filter(pk__in=ordered_signal_ids)
            .values_list("pk", flat=True)
        )
        public_ordered_ids = tuple(
            product_id for product_id in ordered_signal_ids if product_id in public_ids
        )
        vectors = cls._embeddings_for_products(public_ordered_ids)
        if not vectors:
            return None
        dimensions = settings.AI_EMBEDDING_DIMENSIONS
        weighted_vectors = [
            (vector, weight_by_id[product_id])
            for product_id, vector in zip(public_ordered_ids, vectors, strict=False)
        ]
        total_weight = sum(weight for _vector, weight in weighted_vectors)
        centroid = [
            sum(vector[index] * weight for vector, weight in weighted_vectors) / total_weight
            for index in range(dimensions)
        ]
        return cls._normalize_vector(centroid)

    @classmethod
    def _embedding_for_product(cls, product_id: UUID) -> list[float] | None:
        vectors = cls._embeddings_for_products((product_id,))
        return vectors[0] if vectors else None

    @classmethod
    def _embeddings_for_products(
        cls,
        product_ids: tuple[UUID, ...],
    ) -> list[list[float]]:
        if not product_ids:
            return []
        rows = (
            ProductEmbedding.objects.filter(
                product_id__in=product_ids,
                variant__isnull=True,
                language_code="vi",
                model_name=settings.AI_EMBEDDING_MODEL,
            )
            .order_by("product_id", "-indexed_at", "-id")
            .values_list("product_id", "embedding")
        )
        vector_by_product: dict[UUID, list[float]] = {}
        for product_id, raw_vector in rows:
            if product_id in vector_by_product:
                continue
            vector = cls._normalize_vector(raw_vector)
            if vector is not None:
                vector_by_product[product_id] = vector
        return [
            vector_by_product[product_id]
            for product_id in product_ids
            if product_id in vector_by_product
        ]

    @staticmethod
    def _normalize_vector(raw_vector: Any) -> list[float] | None:
        try:
            vector = list(raw_vector)
        except (TypeError, ValueError):
            return None
        if len(vector) != settings.AI_EMBEDDING_DIMENSIONS:
            return None
        normalized_values: list[float] = []
        for value in vector:
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                return None
            normalized_value = float(value)
            if not math.isfinite(normalized_value):
                return None
            normalized_values.append(normalized_value)
        norm = math.sqrt(sum(value * value for value in normalized_values))
        if not math.isfinite(norm) or norm <= 0:
            return None
        return [value / norm for value in normalized_values]

    @classmethod
    def _postgres_vector_product_ids(
        cls,
        *,
        vector: list[float],
        excluded_ids: set[UUID],
        category_preferences: tuple[UUID, ...],
        brand_preferences: tuple[UUID, ...],
        min_similarity: float | None = None,
    ) -> list[UUID]:
        public_product_ids = SearchSelector.search({"in_stock": True}).order_by().values("pk")
        distance = CosineDistance("embedding", vector)
        candidates = ProductEmbedding.objects.filter(
            product_id__in=Subquery(public_product_ids),
            variant__isnull=True,
            language_code="vi",
            model_name=settings.AI_EMBEDDING_MODEL,
        ).exclude(product_id__in=excluded_ids)
        # Keep cosine distance as the direct ORDER BY expression so PostgreSQL
        # can use the pgvector HNSW index before the deterministic rerank.
        candidate_rows = (
            candidates.annotate(vector_distance=distance)
            .order_by(distance)[:MAX_VECTOR_CANDIDATES]
            .values_list("product_id", "vector_distance")
        )
        distance_by_id: dict[UUID, float] = {}
        for product_id, raw_distance in candidate_rows:
            try:
                candidate_distance = float(raw_distance)
            except (TypeError, ValueError):
                continue
            if not math.isfinite(candidate_distance):
                continue
            threshold = (
                float(min_similarity)
                if min_similarity is not None
                else float(getattr(settings, "AI_RECOMMENDATION_MIN_COSINE_SIMILARITY", 0.30))
            )
            if 1.0 - candidate_distance < threshold:
                continue
            previous = distance_by_id.get(product_id)
            if previous is None or candidate_distance < previous:
                distance_by_id[product_id] = candidate_distance
        if not distance_by_id:
            return []

        product_rows = (
            ProductSelector.public_base()
            .filter(pk__in=distance_by_id)
            .values_list(
                "pk",
                "category_id",
                "brand_id",
                "sold_count",
                "rating_average",
            )
        )
        category_rank = {
            category_id: index for index, category_id in enumerate(category_preferences)
        }
        brand_rank = {brand_id: index for index, brand_id in enumerate(brand_preferences)}

        def sort_key(row) -> tuple[Any, ...]:
            product_id, category_id, brand_id, sold_count, rating_average = row
            return (
                round(distance_by_id[product_id], 12),
                category_rank.get(category_id, len(category_rank) + 1),
                brand_rank.get(brand_id, len(brand_rank) + 1),
                -int(sold_count or 0),
                -float(rating_average or 0),
                str(product_id),
            )

        return [row[0] for row in sorted(product_rows, key=sort_key)[:MAX_RECOMMENDATION_RESULTS]]

    @classmethod
    def _fallback_recommendation_ids(
        cls,
        *,
        excluded_ids: set[UUID],
        category_preferences: tuple[UUID, ...],
        brand_preferences: tuple[UUID, ...],
        limit: int,
    ) -> list[UUID]:
        if limit <= 0:
            return []
        base = SearchSelector.search({"in_stock": True}).exclude(pk__in=excluded_ids)
        selected: list[UUID] = []
        if category_preferences or brand_preferences:
            preference_filter = Q()
            if category_preferences:
                preference_filter |= Q(category_id__in=category_preferences)
            if brand_preferences:
                preference_filter |= Q(brand_id__in=brand_preferences)
            preferred_rows = (
                base.filter(preference_filter)
                .order_by(
                    "-sold_count",
                    "-rating_average",
                    "-rating_count",
                    "-created_at",
                    "id",
                )
                .values_list(
                    "pk",
                    "category_id",
                    "brand_id",
                    "sold_count",
                    "rating_average",
                )[:MAX_VECTOR_CANDIDATES]
            )
            category_rank = {
                category_id: index for index, category_id in enumerate(category_preferences)
            }
            brand_rank = {brand_id: index for index, brand_id in enumerate(brand_preferences)}

            def preference_key(row) -> tuple[Any, ...]:
                product_id, category_id, brand_id, sold_count, rating_average = row
                return (
                    category_rank.get(category_id, len(category_rank) + 1),
                    brand_rank.get(brand_id, len(brand_rank) + 1),
                    -int(sold_count or 0),
                    -float(rating_average or 0),
                    str(product_id),
                )

            selected.extend(row[0] for row in sorted(preferred_rows, key=preference_key)[:limit])

        remaining = limit - len(selected)
        if remaining > 0:
            selected_set = excluded_ids | set(selected)
            global_ids = (
                base.exclude(pk__in=selected_set)
                .order_by(
                    "-sold_count",
                    "-rating_average",
                    "-rating_count",
                    "-created_at",
                    "id",
                )
                .values_list("pk", flat=True)[:remaining]
            )
            selected.extend(global_ids)
        return selected

    @classmethod
    def _fallback_similar_ids(
        cls,
        *,
        context_product: Product,
        excluded_ids: set[UUID],
        limit: int,
    ) -> list[UUID]:
        if limit <= 0:
            return []
        base = SearchSelector.search({"in_stock": True})
        selected: list[UUID] = []

        filters: list[dict[str, Any]] = []
        if context_product.brand_id is not None:
            filters.append(
                {
                    "category_id": context_product.category_id,
                    "brand_id": context_product.brand_id,
                }
            )
        filters.append({"category_id": context_product.category_id})
        # Never fill with globally popular but unrelated items. If vectors are
        # unavailable, category is the minimum content-similarity contract.

        for bucket_filter in filters:
            remaining = limit - len(selected)
            if remaining <= 0:
                break
            bucket = base.exclude(pk__in=excluded_ids | set(selected)).filter(**bucket_filter)
            bucket_ids = bucket.order_by(
                "-sold_count",
                "-rating_average",
                "-rating_count",
                "-created_at",
                "id",
            ).values_list("pk", flat=True)[:remaining]
            selected.extend(bucket_ids)
        return selected

    @classmethod
    def _cache_key(
        cls,
        *,
        kind: str,
        signals: _Signals,
        vector_enabled: bool,
    ) -> str:
        if kind == "similar":
            return build_cache_key(
                "ai-similar",
                {
                    "algorithm": RECOMMENDATION_ALGORITHM_VERSION,
                    "context": str(signals.context_product.pk),
                    "model": settings.AI_EMBEDDING_MODEL,
                },
            )
        wishlist_fingerprint = canonical_sha256(
            {
                "model": settings.AI_EMBEDDING_MODEL,
                "ids": sorted(str(product_id) for product_id in signals.wishlist_ids),
            }
        )
        return build_cache_key(
            f"ai-{kind}",
            {
                "algorithm": RECOMMENDATION_ALGORITHM_VERSION,
                "context": (
                    str(signals.context_product.pk) if signals.context_product is not None else ""
                ),
                "browsing": [str(product_id) for product_id in signals.browsing_ids],
                "cart": [str(product_id) for product_id in signals.cart_ids],
                "landing_context": signals.landing_context,
                "traffic_source": signals.traffic_source,
                "user": signals.user_identity,
                "wishlist_fingerprint": wishlist_fingerprint,
                "model": settings.AI_EMBEDDING_MODEL,
                "vector_enabled": vector_enabled,
            },
        )

    @classmethod
    def _cached_outcome(
        cls,
        cache_key: str,
        *,
        vector_enabled: bool,
    ) -> RecommendationOutcome | None:
        payload = safe_cache_get(cache_key, _CACHE_MISS)
        if payload is _CACHE_MISS or not isinstance(payload, dict):
            return None
        if set(payload) != {
            "product_ids",
            "ai_used",
            "fallback_used",
            "personalized",
            "strategy",
            "vector_enabled",
        }:
            return None
        product_ids = payload.get("product_ids")
        if (
            not isinstance(product_ids, list)
            or not all(isinstance(product_id, str) for product_id in product_ids)
            or not isinstance(payload.get("ai_used"), bool)
            or not isinstance(payload.get("fallback_used"), bool)
            or not isinstance(payload.get("personalized"), bool)
            or not isinstance(payload.get("strategy"), str)
            or not isinstance(payload.get("vector_enabled"), bool)
        ):
            return None
        if payload["vector_enabled"] is not vector_enabled:
            return None
        try:
            normalized_ids = [UUID(product_id) for product_id in product_ids]
        except (TypeError, ValueError):
            return None
        return RecommendationOutcome(
            products=cls._rehydrate(normalized_ids),
            ai_used=payload["ai_used"],
            fallback_used=payload["fallback_used"],
            personalized=payload["personalized"],
            strategy=payload["strategy"][:100],
            cached=True,
        )

    @staticmethod
    def _cache_outcome(
        cache_key: str,
        outcome: RecommendationOutcome,
        *,
        vector_enabled: bool,
        timeout: int,
    ) -> None:
        safe_cache_set(
            cache_key,
            {
                "product_ids": [str(product.pk) for product in outcome.products],
                "ai_used": outcome.ai_used,
                "fallback_used": outcome.fallback_used,
                "personalized": outcome.personalized,
                "strategy": outcome.strategy,
                "vector_enabled": vector_enabled,
            },
            timeout=max(0, int(timeout)),
        )

    @staticmethod
    def _rehydrate(product_ids: list[UUID]) -> list[Product]:
        if not product_ids:
            return []
        unique_ids = list(dict.fromkeys(product_ids))
        products_by_id = {
            product.pk: product
            for product in SearchSelector.search({"in_stock": True}).filter(pk__in=unique_ids)
        }
        return [
            products_by_id[product_id] for product_id in unique_ids if product_id in products_by_id
        ]
