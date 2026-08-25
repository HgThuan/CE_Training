from unittest.mock import patch
from uuid import uuid4

import pytest
from django.conf import settings
from django.core.cache import cache
from django.test import override_settings
from django.urls import reverse
from rest_framework.test import APIClient

from apps.account.models import Shop, User
from apps.account.tests.factories import ShopFactory, UserFactory
from apps.ai.embedding_service import EmbeddingService
from apps.ai.recommendation_service import (
    RecommendationOutcome,
    RecommendationService,
)
from apps.catalog.tests.factories import BrandFactory, CategoryFactory
from apps.engagement.models import Wishlist, WishlistItem
from apps.inventory.models import InventoryBalance
from apps.product.models import Product
from apps.product.tests.factories import ProductFactory, ProductVariantFactory


@pytest.fixture(autouse=True)
def isolate_recommendation_cache():
    cache.clear()
    yield
    cache.clear()


def add_stock(product, quantity=5):
    variant = ProductVariantFactory(product=product, shop=product.shop)
    return InventoryBalance.objects.create(
        variant=variant,
        available_stock=quantity,
    )


def public_product(**kwargs):
    product = ProductFactory(status=Product.Status.APPROVED, **kwargs)
    add_stock(product)
    return product


@pytest.mark.django_db
def test_similar_fallback_uses_deterministic_tiers_and_never_returns_anchor():
    category = CategoryFactory()
    other_category = CategoryFactory()
    brand = BrandFactory()
    other_brand = BrandFactory()
    anchor = public_product(category=category, brand=brand)
    same_category_brand = public_product(
        category=category,
        brand=brand,
        sold_count=1,
    )
    same_category = public_product(
        category=category,
        brand=other_brand,
        sold_count=50,
    )
    same_brand = public_product(
        category=other_category,
        brand=brand,
        sold_count=100,
    )
    global_product = public_product(
        category=other_category,
        brand=other_brand,
        sold_count=200,
    )

    with patch.object(RecommendationService, "is_vector_enabled", return_value=False):
        outcome = RecommendationService.similar_products(context_product=anchor)

    assert [product.pk for product in outcome.products] == [
        same_category_brand.pk,
        same_category.pk,
    ]
    assert same_brand.pk not in {product.pk for product in outcome.products}
    assert global_product.pk not in {product.pk for product in outcome.products}
    assert anchor.pk not in {product.pk for product in outcome.products}
    assert outcome.ai_used is False
    assert outcome.fallback_used is True
    assert outcome.personalized is False


@override_settings(AI_FEATURES_ENABLED=True)
def test_recommendations_disable_vectors_when_embedding_table_is_missing():
    with patch(
        "apps.ai.recommendation_service.product_embedding_table_available",
        return_value=False,
    ):
        assert RecommendationService.is_vector_enabled() is False


@pytest.mark.django_db
def test_customer_wishlist_is_owner_scoped_and_excluded_from_results():
    category_a = CategoryFactory()
    category_b = CategoryFactory()
    customer_a = UserFactory(role=User.Role.CUSTOMER)
    customer_b = UserFactory(role=User.Role.CUSTOMER)
    wished_a = public_product(category=category_a)
    wished_b = public_product(category=category_b)
    candidate_a = public_product(category=category_a, sold_count=20)
    candidate_b = public_product(category=category_b, sold_count=10)
    wishlist_a = Wishlist.objects.create(user=customer_a)
    wishlist_b = Wishlist.objects.create(user=customer_b)
    WishlistItem.objects.create(wishlist=wishlist_a, product=wished_a)
    WishlistItem.objects.create(wishlist=wishlist_b, product=wished_b)

    signals_a = RecommendationService._build_signals(
        context_product=None,
        browsing_ids=(),
        user=customer_a,
    )
    signals_b = RecommendationService._build_signals(
        context_product=None,
        browsing_ids=(),
        user=customer_b,
    )
    with patch.object(RecommendationService, "is_vector_enabled", return_value=False):
        outcome_a = RecommendationService.recommendations(user=customer_a)
        outcome_b = RecommendationService.recommendations(user=customer_b)

    assert signals_a.wishlist_ids == (wished_a.pk,)
    assert signals_b.wishlist_ids == (wished_b.pk,)
    assert outcome_a.products[0].pk == candidate_a.pk
    assert outcome_b.products[0].pk == candidate_b.pk
    assert wished_a.pk not in {product.pk for product in outcome_a.products}
    assert wished_b.pk not in {product.pk for product in outcome_b.products}


@pytest.mark.django_db
def test_non_customer_roles_are_anonymous_and_do_not_read_wishlists():
    seller = UserFactory(role=User.Role.SELLER)
    admin = UserFactory(role=User.Role.ADMIN)

    seller_signals = RecommendationService._build_signals(
        context_product=None,
        browsing_ids=(),
        user=seller,
    )
    admin_signals = RecommendationService._build_signals(
        context_product=None,
        browsing_ids=(),
        user=admin,
    )

    assert seller_signals.user_identity == "anonymous"
    assert admin_signals.user_identity == "anonymous"
    assert seller_signals.wishlist_ids == ()
    assert admin_signals.wishlist_ids == ()


@pytest.mark.django_db
@override_settings(AI_EMBEDDING_DIMENSIONS=3)
def test_centroid_ignores_non_public_browsing_products_and_normalizes_vector():
    public = public_product()
    draft = ProductFactory(status=Product.Status.DRAFT)
    signals = RecommendationService._build_signals(
        context_product=None,
        browsing_ids=(draft.pk, public.pk),
        user=None,
    )

    with patch.object(
        RecommendationService,
        "_embeddings_for_products",
        return_value=[[3.0, 4.0, 0.0]],
    ) as embeddings:
        centroid = RecommendationService._centroid_for_signals(signals)

    embeddings.assert_called_once_with((public.pk,))
    assert centroid == pytest.approx([0.6, 0.8, 0.0])
    assert RecommendationService._normalize_vector([0.0, 0.0, 0.0]) is None
    assert RecommendationService._normalize_vector([1.0, float("inf"), 0.0]) is None
    assert RecommendationService._normalize_vector([True, 0.0, 0.0]) is None


@pytest.mark.django_db
def test_cached_results_are_rehydrated_through_public_in_stock_selector():
    anchor = public_product()
    candidate = public_product(category=anchor.category)

    with patch.object(RecommendationService, "is_vector_enabled", return_value=False):
        first = RecommendationService.similar_products(context_product=anchor)
        InventoryBalance.objects.filter(variant__product=candidate).update(available_stock=0)
        second = RecommendationService.similar_products(context_product=anchor)

    assert candidate.pk in {product.pk for product in first.products}
    assert second.cached is True
    assert candidate.pk not in {product.pk for product in second.products}


@pytest.mark.django_db
def test_similar_cache_does_not_reuse_vector_result_after_feature_is_disabled():
    anchor = public_product()
    candidate = public_product(category=anchor.category)

    with (
        patch.object(
            RecommendationService,
            "is_vector_enabled",
            side_effect=[True, False],
        ),
        patch.object(
            RecommendationService,
            "_embedding_for_product",
            return_value=[1.0] * 1536,
        ),
        patch.object(
            RecommendationService,
            "_postgres_vector_product_ids",
            return_value=[candidate.pk],
        ) as vector_query,
    ):
        vector_outcome = RecommendationService.similar_products(
            context_product=anchor,
        )
        fallback_outcome = RecommendationService.similar_products(
            context_product=anchor,
        )

    assert vector_outcome.ai_used is True
    assert vector_outcome.strategy == "vector_similar"
    assert fallback_outcome.cached is False
    assert fallback_outcome.ai_used is False
    assert fallback_outcome.strategy == "fallback_similar"
    vector_query.assert_called_once()


@pytest.mark.django_db
@override_settings(
    AI_RECOMMENDATION_CACHE_TTL_SECONDS=901,
    AI_SIMILAR_CACHE_TTL_SECONDS=1801,
)
def test_recommendation_cache_uses_separate_configured_ttls():
    anchor = public_product()
    with (
        patch.object(RecommendationService, "is_vector_enabled", return_value=False),
        patch("apps.ai.recommendation_service.safe_cache_set") as cache_set,
    ):
        RecommendationService.recommendations(context_product=anchor)
        recommendation_timeout = cache_set.call_args.kwargs["timeout"]
        cache_set.reset_mock()
        RecommendationService.similar_products(context_product=anchor)
        similar_timeout = cache_set.call_args.kwargs["timeout"]

    assert recommendation_timeout == 901
    assert similar_timeout == 1801


@pytest.mark.django_db
@override_settings(AI_FEATURES_ENABLED=True)
def test_embedding_indexing_is_enabled_when_either_ai_feature_is_enabled():
    with (
        patch("apps.ai.embedding_service.AIService.is_configured", return_value=True),
        patch(
            "apps.ai.embedding_service.SiteSetting.get_bool",
            side_effect=[False, True],
        ),
    ):
        assert EmbeddingService.is_enabled() is True


@pytest.mark.django_db
def test_three_recommendation_endpoints_return_standard_shape_and_forward_context():
    customer = UserFactory(role=User.Role.CUSTOMER)
    anchor = public_product()
    result = public_product()
    outcome = RecommendationOutcome(
        products=[result],
        ai_used=False,
        fallback_used=True,
        personalized=True,
        strategy="fallback_preferences",
    )
    client = APIClient()
    client.force_authenticate(customer)

    with (
        patch.object(
            RecommendationService,
            "recommendations",
            return_value=outcome,
        ) as recommendations,
        patch.object(
            RecommendationService,
            "similar_products",
            return_value=outcome,
        ) as similar,
    ):
        product_response = client.get(
            reverse("product-recommendations", args=[anchor.pk]),
            {"browsing_history": str(result.pk), "page_size": 12},
        )
        similar_response = client.get(
            reverse("product-similar", args=[anchor.pk]),
            {"page_size": 12},
        )
        home_response = client.get(
            reverse("ai:recommendations"),
            {"browsing_history": str(result.pk), "page_size": 12},
        )

    for response in (product_response, similar_response, home_response):
        assert response.status_code == 200
        assert response.data["success"] is True
        assert response.data["data"]["strategy"] == "fallback_preferences"
        assert response.data["data"]["results"][0]["id"] == str(result.pk)
        assert response.data["meta"]["page_size"] == 12
    assert recommendations.call_args_list[0].kwargs == {
        "context_product": anchor,
        "browsing_ids": [result.pk],
        "user": customer,
    }
    assert recommendations.call_args_list[1].kwargs == {
        "browsing_ids": [result.pk],
        "user": customer,
    }
    similar.assert_called_once()
    assert similar.call_args.kwargs["context_product"] == anchor


@pytest.mark.django_db
def test_recommendation_event_accepts_interactions_but_rejects_client_purchase():
    customer = UserFactory(role=User.Role.CUSTOMER)
    product = public_product()
    client = APIClient()
    client.force_authenticate(customer)
    recommendation_id = "2a7446df-b249-47af-8518-29f501ff10e6"

    accepted = client.post(
        reverse("ai:recommendation-event"),
        {
            "recommendation_id": recommendation_id,
            "product_id": str(product.pk),
            "event_type": "click",
            "source": "home",
            "position": 0,
        },
        format="json",
    )
    rejected = client.post(
        reverse("ai:recommendation-event"),
        {
            "recommendation_id": recommendation_id,
            "product_id": str(product.pk),
            "event_type": "purchase",
            "source": "home",
        },
        format="json",
    )

    assert accepted.status_code == 200
    assert rejected.status_code == 400


@pytest.mark.django_db
def test_recommendations_and_tracking_events_have_independent_throttle_buckets():
    rates = {
        **settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"],
        "ai_recommendation_authenticated": "1/minute",
        "ai_recommendation_event_authenticated": "2/minute",
    }
    rest_framework = {
        **settings.REST_FRAMEWORK,
        "DEFAULT_THROTTLE_RATES": rates,
    }
    customer = UserFactory(role=User.Role.CUSTOMER)
    product = public_product()
    client = APIClient()
    client.force_authenticate(customer)
    event_payload = {
        "recommendation_id": str(uuid4()),
        "product_id": str(product.pk),
        "event_type": "impression",
        "source": "home",
        "position": 0,
    }

    with override_settings(REST_FRAMEWORK=rest_framework):
        assert client.get(reverse("ai:recommendations")).status_code == 200
        assert client.get(reverse("ai:recommendations")).status_code == 429

        assert (
            client.post(
                reverse("ai:recommendation-event"), event_payload, format="json"
            ).status_code
            == 200
        )
        assert (
            client.post(
                reverse("ai:recommendation-event"), event_payload, format="json"
            ).status_code
            == 200
        )
        assert (
            client.post(
                reverse("ai:recommendation-event"), event_payload, format="json"
            ).status_code
            == 429
        )


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("url_name", "url_args", "invalid_params"),
    [
        ("product-recommendations", True, {"user_id": str(uuid4())}),
        ("product-similar", True, {"browsing_history": str(uuid4())}),
        ("ai:recommendations", False, {"unknown": "value"}),
    ],
)
def test_recommendation_endpoints_reject_unknown_or_private_query_params(
    url_name,
    url_args,
    invalid_params,
):
    anchor = public_product()
    url = reverse(url_name, args=[anchor.pk] if url_args else None)

    response = APIClient().get(url, invalid_params)

    assert response.status_code == 400
    assert "query_params" in response.data["errors"]


@pytest.mark.django_db
def test_recommendation_history_validation_rejects_malformed_empty_and_over_limit_values():
    anchor = public_product()
    url = reverse("product-recommendations", args=[anchor.pk])
    client = APIClient()

    malformed = client.get(url, {"browsing_history": "not-a-uuid"})
    empty_item = client.get(
        url,
        {"browsing_history": f"{uuid4()},,{uuid4()}"},
    )
    over_limit = client.get(
        url,
        {"browsing_history": ",".join(str(uuid4()) for _ in range(21))},
    )

    assert malformed.status_code == 400
    assert empty_item.status_code == 400
    assert over_limit.status_code == 400


@pytest.mark.django_db
@pytest.mark.parametrize(
    "product_kwargs",
    [
        {"status": Product.Status.DRAFT},
        {"status": Product.Status.APPROVED, "is_deleted": True},
        {
            "status": Product.Status.APPROVED,
            "shop": None,
        },
    ],
)
def test_product_recommendation_source_must_be_public(product_kwargs):
    if product_kwargs.get("shop", object()) is None:
        product_kwargs["shop"] = ShopFactory(status=Shop.Status.LOCKED)
    anchor = ProductFactory(**product_kwargs)

    response = APIClient().get(
        reverse("product-recommendations", args=[anchor.pk]),
    )

    assert response.status_code == 404


@pytest.mark.django_db
def test_recommendation_request_path_never_calls_external_ai_provider():
    anchor = public_product()

    with (
        patch.object(RecommendationService, "is_vector_enabled", return_value=False),
        patch("apps.ai.services.AIService.get_embedding") as get_embedding,
        patch("apps.ai.services.AIService.generate_text") as generate_text,
    ):
        response = APIClient().get(reverse("product-similar", args=[anchor.pk]))

    assert response.status_code == 200
    get_embedding.assert_not_called()
    generate_text.assert_not_called()


@pytest.mark.django_db
def test_postgresql_recommendation_vector_integration_or_skip():
    from django.db import connection

    if connection.vendor != "postgresql":
        pytest.skip("pgvector recommendation integration requires PostgreSQL")
    pytest.skip(
        "Requires the external PostgreSQL server with pgvector, the HNSW index, "
        "and representative product embeddings."
    )
