import hashlib
from datetime import timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from django.contrib import admin
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import RequestFactory
from django.utils import timezone

from apps.account.models import User
from apps.account.tests.factories import UserFactory
from apps.ai.admin import AIContentCacheAdmin
from apps.ai.models import (
    EMBEDDING_DIMENSIONS,
    LOG_PROMPT_MAX_LENGTH,
    AIContentCache,
    AIRequestLog,
    ProductEmbedding,
)
from apps.common.admin import SiteSettingAdmin
from apps.common.models import SiteSetting
from apps.product.tests.factories import ProductFactory, ProductVariantFactory


@pytest.fixture(autouse=True)
def clear_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.mark.django_db
def test_site_setting_boolean_cache_is_invalidated_on_update_and_delete():
    setting = SiteSetting.set_value("feature.ai_search.enabled", True)

    assert SiteSetting.get_bool("feature.ai_search.enabled") is True

    setting.value = False
    setting.value_type = SiteSetting.ValueType.BOOLEAN
    setting.save()
    assert SiteSetting.get_bool("feature.ai_search.enabled", default=True) is False

    setting.delete()
    assert SiteSetting.get_bool("feature.ai_search.enabled", default=True) is True


@pytest.mark.django_db
def test_site_setting_validates_json_value_type_and_admin_records_actor():
    setting = SiteSetting(
        key="feature.ai_search.enabled",
        value=True,
        value_type=SiteSetting.ValueType.STRING,
    )
    with pytest.raises(ValidationError):
        setting.full_clean()

    actor = UserFactory(role=User.Role.ADMIN, is_staff=True)
    request = RequestFactory().post("/admin/common/sitesetting/add/")
    request.user = actor
    setting.value_type = SiteSetting.ValueType.BOOLEAN
    model_admin = SiteSettingAdmin(SiteSetting, admin.site)
    model_admin.save_model(request, setting, form=None, change=False)

    setting.refresh_from_db()
    assert setting.updated_by == actor


@pytest.mark.django_db
def test_product_embedding_enforces_dimension_and_product_variant_consistency():
    product = ProductFactory()
    other_variant = ProductVariantFactory()
    embedding = ProductEmbedding(
        product=product,
        variant=other_variant,
        language_code="vi",
        model_name="gemini-embedding-2",
        content_hash=hashlib.sha256(b"product").hexdigest(),
        embedding=[0.0] * (EMBEDDING_DIMENSIONS - 1),
    )

    with pytest.raises(ValidationError) as exc_info:
        embedding.full_clean()

    assert "embedding" in exc_info.value.message_dict
    assert "variant" in exc_info.value.message_dict


@pytest.mark.django_db
def test_product_embedding_product_level_uniqueness_is_portable_to_sqlite():
    product = ProductFactory()
    values = {
        "product": product,
        "variant": None,
        "language_code": "vi",
        "model_name": "gemini-embedding-2",
        "content_hash": hashlib.sha256(b"same source").hexdigest(),
        "embedding": [0.0] * EMBEDDING_DIMENSIONS,
    }
    ProductEmbedding.objects.create(**values)

    with pytest.raises(IntegrityError), transaction.atomic():
        ProductEmbedding.objects.create(**values)


@pytest.mark.django_db
def test_ai_request_log_masks_and_truncates_sensitive_text_and_metadata():
    log = AIRequestLog.objects.create(
        feature=AIRequestLog.Feature.SMART_SEARCH,
        provider="gemini",
        model_name="gemini-3.6-flash",
        prompt=("api_key=never-store-this customer@example.com " + "x" * LOG_PROMPT_MAX_LENGTH),
        response="authorization: Bearer private-token-value",
        error_message="password=hunter2",
        metadata={
            "access_token": "private",
            "nested": {"contact": "buyer@example.com"},
        },
        status=AIRequestLog.Status.FALLBACK,
    )

    log.refresh_from_db()
    assert "never-store-this" not in log.prompt
    assert "customer@example.com" not in log.prompt
    assert len(log.prompt) <= LOG_PROMPT_MAX_LENGTH
    assert "private-token-value" not in log.response
    assert "hunter2" not in log.error_message
    assert log.metadata["access_token"] == "[REDACTED]"
    assert log.metadata["nested"]["contact"] == "[REDACTED_EMAIL]"


@pytest.mark.django_db
def test_ai_request_log_full_clean_accepts_valid_log():
    log = AIRequestLog(
        feature=AIRequestLog.Feature.SMART_SEARCH,
        provider="gemini",
        model_name="gemini-3.6-flash",
        status=AIRequestLog.Status.SUCCESS,
    )

    log.full_clean()


@pytest.mark.django_db
def test_ai_request_log_cost_constraint_rejects_negative_values():
    with pytest.raises(IntegrityError), transaction.atomic():
        AIRequestLog.objects.create(
            feature=AIRequestLog.Feature.OTHER,
            provider="gemini",
            model_name="gemini-3.6-flash",
            estimated_cost=Decimal("-0.000001"),
            status=AIRequestLog.Status.FAILED,
        )


@pytest.mark.django_db
def test_ai_content_cache_unique_expiry_and_result_sanitization():
    entity_id = uuid4()
    values = {
        "feature": "summary",
        "entity_type": "product",
        "entity_id": entity_id,
        "language_code": "vi",
        "content_hash": hashlib.sha256(b"summary source").hexdigest(),
        "model_name": "gemini-3.6-flash",
        "expires_at": timezone.now() - timedelta(seconds=1),
    }
    cached = AIContentCache.objects.create(
        **values,
        result={"api_key": "private", "contact": "buyer@example.com"},
    )
    cached.refresh_from_db()

    assert cached.is_expired is True
    assert cached.result == {
        "api_key": "[REDACTED]",
        "contact": "[REDACTED_EMAIL]",
    }

    with pytest.raises(IntegrityError), transaction.atomic():
        AIContentCache.objects.create(**values, result={})


@pytest.mark.django_db
def test_ai_content_cache_full_clean_and_admin_form_accept_valid_data():
    entity_id = uuid4()
    content_hash = hashlib.sha256(b"admin cache").hexdigest()
    cached = AIContentCache(
        feature="summary",
        entity_type="product",
        entity_id=entity_id,
        language_code="vi",
        content_hash=content_hash,
        result={"summary": "Safe result"},
        model_name="gemini-3.6-flash",
    )

    cached.full_clean()

    actor = UserFactory(
        role=User.Role.ADMIN,
        is_staff=True,
        is_superuser=True,
    )
    request = RequestFactory().post("/admin/ai/aicontentcache/add/")
    request.user = actor
    model_admin = AIContentCacheAdmin(AIContentCache, admin.site)
    form_class = model_admin.get_form(request)
    form = form_class(
        data={
            "feature": "summary",
            "entity_type": "product",
            "entity_id": str(uuid4()),
            "language_code": "vi",
            "content_hash": hashlib.sha256(b"admin form cache").hexdigest(),
            "result": '{"summary": "Safe admin result"}',
            "model_name": "gemini-3.6-flash",
            "is_stale": False,
            "expires_at": "",
        }
    )

    assert form.is_valid(), form.errors
