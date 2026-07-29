from decimal import Decimal
from unittest.mock import Mock, patch

import pytest
from django.test import override_settings

from apps.ai import search_service
from apps.ai.models import EMBEDDING_DIMENSIONS
from apps.ai.search_service import (
    AISearchService,
)
from apps.ai.services import AIService, EmbeddingResult
from apps.catalog.tests.factories import CategoryFactory
from apps.product.models import Product
from apps.product.tests.factories import ProductFactory


@pytest.mark.django_db
@override_settings(AI_FEATURES_ENABLED=True)
def test_smart_search_explicit_filters_override_ai_intent():
    ai_category = CategoryFactory(slug="ai-category")
    selected_category = CategoryFactory(slug="selected-category")
    ProductFactory(
        status=Product.Status.APPROVED,
        name="Phone from AI category",
        category=ai_category,
    )
    selected = ProductFactory(
        status=Product.Status.APPROVED,
        name="Phone selected by customer",
        category=selected_category,
    )
    intent = {
        "keywords": ["Phone"],
        "filters": {"category": ai_category.slug},
        "explanation": "Đã hiểu nhu cầu.",
        "ai_used": True,
        "fallback_used": False,
    }

    with (
        patch.object(AISearchService, "is_enabled", return_value=True),
        patch(
            "apps.ai.search_service.AIService.extract_search_intent",
            return_value=intent,
        ),
    ):
        outcome = AISearchService.smart_search(
            query="phone phù hợp",
            filters={"category": selected_category.slug, "sort": "-created_at"},
        )

    assert [product.pk for product in outcome.products] == [selected.pk]
    assert outcome.intent["filters"]["category"] == selected_category.slug
    assert outcome.ai_used is True
    assert outcome.fallback_used is False


@pytest.mark.django_db
@override_settings(AI_FEATURES_ENABLED=True)
def test_smart_search_provider_error_keeps_explicit_filters():
    selected_category = CategoryFactory(slug="selected-category")
    selected = ProductFactory(
        status=Product.Status.APPROVED,
        name="Durable phone",
        category=selected_category,
    )
    ProductFactory(
        status=Product.Status.APPROVED,
        name="Durable phone elsewhere",
    )

    with (
        patch.object(AISearchService, "is_enabled", return_value=True),
        patch(
            "apps.ai.search_service.AIService.extract_search_intent",
            side_effect=RuntimeError("provider unavailable"),
        ),
    ):
        outcome = AISearchService.smart_search(
            query="Durable phone",
            filters={"category": selected_category.slug},
        )

    assert [product.pk for product in outcome.products] == [selected.pk]
    assert outcome.ai_used is False
    assert outcome.fallback_used is True


@pytest.mark.django_db
def test_global_kill_switch_cannot_be_overridden_by_database_flag():
    with (
        patch(
            "apps.ai.search_service.SiteSetting.get_bool",
            return_value=True,
        ) as get_bool,
        patch(
            "apps.ai.search_service.AIService.extract_search_intent",
        ) as extract_intent,
    ):
        outcome = AISearchService.smart_search(query="phone")

    assert outcome.ai_used is False
    assert outcome.fallback_used is True
    get_bool.assert_not_called()
    extract_intent.assert_not_called()


@pytest.mark.django_db
@override_settings(AI_FEATURES_ENABLED=True)
def test_semantic_search_rejects_non_finite_query_vector_before_database_query():
    invalid = EmbeddingResult(
        vector=[float("inf"), *([0.01] * (EMBEDDING_DIMENSIONS - 1))],
        ai_used=True,
        fallback_used=False,
        cached=False,
        model_name="test-model",
    )

    with (
        patch.object(AISearchService, "is_enabled", return_value=True),
        patch.object(AISearchService, "_supports_vector_search", return_value=True),
        patch.object(AIService, "get_embedding", return_value=invalid),
        patch.object(AISearchService, "_postgres_semantic_products") as vector_query,
    ):
        outcome = AISearchService.semantic_search(query="phone")

    assert outcome.ai_used is False
    assert outcome.fallback_used is True
    vector_query.assert_not_called()


@pytest.mark.django_db
def test_semantic_candidate_query_orders_directly_by_cosine_distance_with_limit():
    with patch.object(
        search_service.SearchSelector,
        "search",
        wraps=search_service.SearchSelector.search,
    ) as public_search:
        candidates = AISearchService._postgres_semantic_candidates(
            vector=[0.01] * EMBEDDING_DIMENSIONS,
            model_name="test-model",
            filters={
                "category": "phones",
                "in_stock": True,
                "sort": "-rating",
            },
        )

    public_search.assert_called_once_with(
        {
            "category": "phones",
            "in_stock": True,
        }
    )
    assert candidates.query.low_mark == 0
    assert candidates.query.high_mark == search_service.MAX_SEMANTIC_CANDIDATES
    assert len(candidates.query.order_by) == 1
    assert isinstance(
        candidates.query.order_by[0],
        search_service.CosineDistance,
    )
    assert "vector_distance" in candidates.query.annotations
    assert "hybrid_score" not in candidates.query.annotations


@pytest.mark.django_db
def test_semantic_products_hybrid_reranks_only_bounded_candidates_and_keeps_sort():
    high_rating = ProductFactory(
        status=Product.Status.APPROVED,
        rating_average=Decimal("5.00"),
        sold_count=1,
    )
    nearest = ProductFactory(
        status=Product.Status.APPROVED,
        rating_average=Decimal("0.00"),
        sold_count=100,
    )
    excluded = ProductFactory(
        status=Product.Status.APPROVED,
        rating_average=Decimal("5.00"),
        sold_count=1_000,
    )
    candidate_queryset = Mock()
    candidate_queryset.values_list.return_value = [
        (nearest.pk, 0.10),
        (high_rating.pk, 0.20),
    ]

    with patch.object(
        AISearchService,
        "_postgres_semantic_candidates",
        return_value=candidate_queryset,
    ):
        relevance_products = AISearchService._postgres_semantic_products(
            vector=[0.01] * EMBEDDING_DIMENSIONS,
            model_name="test-model",
            filters={"sort": "relevance"},
        )
        explicitly_sorted_products = AISearchService._postgres_semantic_products(
            vector=[0.01] * EMBEDDING_DIMENSIONS,
            model_name="test-model",
            filters={"sort": "-sold_count"},
        )

    # 0.82 hybrid score beats 0.81; the non-candidate never enters reranking.
    assert [product.pk for product in relevance_products] == [
        high_rating.pk,
        nearest.pk,
    ]
    assert [product.pk for product in explicitly_sorted_products] == [
        nearest.pk,
        high_rating.pk,
    ]
    assert excluded.pk not in {product.pk for product in relevance_products}
    assert candidate_queryset.values_list.call_args_list == [
        (("product_id", "vector_distance"),),
        (("product_id", "vector_distance"),),
    ]


@pytest.mark.django_db
def test_postgresql_semantic_vector_integration_or_skip():
    from django.db import connection

    if connection.vendor != "postgresql":
        pytest.skip("pgvector integration requires PostgreSQL")
    pytest.skip(
        "Requires the external PostgreSQL server with the vector extension "
        "and representative embeddings."
    )
