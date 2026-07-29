import hashlib
import math
from dataclasses import asdict, dataclass
from typing import Any

from django.conf import settings
from django.db import DatabaseError, transaction
from django.utils import timezone
from django.utils.html import strip_tags

from apps.common.models import SiteSetting
from apps.product.models import Product
from apps.product.selectors import ProductSelector

from .models import AIRequestLog, ProductEmbedding
from .services import AIService

MAX_EMBEDDING_SOURCE_CHARS = 16_000
AI_SEARCH_FEATURE_KEY = "feature.ai_search.enabled"
AI_RECOMMENDATION_FEATURE_KEY = "feature.ai_recommendation.enabled"


@dataclass(frozen=True, slots=True)
class EmbeddingIndexResult:
    product_id: str
    status: str
    content_hash: str = ""
    model_name: str = ""
    ai_used: bool = False
    fallback_used: bool = False

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


class EmbeddingService:
    @staticmethod
    def is_enabled() -> bool:
        if not settings.AI_FEATURES_ENABLED or not AIService.is_configured():
            return False
        try:
            search_enabled = SiteSetting.get_bool(
                AI_SEARCH_FEATURE_KEY,
                default=settings.AI_FEATURES_ENABLED,
            )
            recommendation_enabled = SiteSetting.get_bool(
                AI_RECOMMENDATION_FEATURE_KEY,
                default=settings.AI_FEATURES_ENABLED,
            )
            return search_enabled or recommendation_enabled
        except DatabaseError:
            return False

    @classmethod
    def build_source_text(cls, product: Product) -> str:
        attributes: list[tuple[str, str]] = []
        for link in product.product_attribute_links.all():
            value = link.attribute_value
            attribute = value.attribute
            display_value = value.display_value or value.value
            attributes.append((attribute.name, display_value))
        attributes.sort(key=lambda item: (item[0].casefold(), item[1].casefold()))

        sections = [
            ("Tên sản phẩm", product.name),
            ("Mô tả ngắn", product.short_description or ""),
            ("Mô tả", product.description or ""),
            ("Danh mục", product.category.name),
            ("Thương hiệu", product.brand.name if product.brand_id else ""),
        ]
        if attributes:
            sections.append(
                (
                    "Thuộc tính",
                    "; ".join(f"{name}: {value}" for name, value in attributes),
                )
            )
        normalized_sections = []
        for label, value in sections:
            normalized_value = " ".join(strip_tags(str(value)).split())
            if normalized_value:
                normalized_sections.append(f"{label}: {normalized_value}")
        return "\n".join(normalized_sections)[:MAX_EMBEDDING_SOURCE_CHARS]

    @staticmethod
    def content_hash(source_text: str) -> str:
        return hashlib.sha256(source_text.encode("utf-8")).hexdigest()

    @classmethod
    def index_product(cls, product_id) -> EmbeddingIndexResult:
        if not cls.is_enabled():
            return EmbeddingIndexResult(
                product_id=str(product_id),
                status="disabled",
            )
        product = (
            ProductSelector.public_base()
            .select_related("shop", "category", "brand")
            .prefetch_related(
                "product_attribute_links__attribute_value__attribute",
            )
            .filter(pk=product_id)
            .first()
        )
        if product is None:
            ProductEmbedding.objects.filter(product_id=product_id).delete()
            return EmbeddingIndexResult(
                product_id=str(product_id),
                status="removed",
            )

        source_text = cls.build_source_text(product)
        source_hash = cls.content_hash(source_text)
        model_name = settings.AI_EMBEDDING_MODEL
        lookup = {
            "product": product,
            "variant": None,
            "language_code": "vi",
            "model_name": model_name,
        }
        if ProductEmbedding.objects.filter(
            **lookup,
            content_hash=source_hash,
        ).exists():
            return EmbeddingIndexResult(
                product_id=str(product.pk),
                status="unchanged",
                content_hash=source_hash,
                model_name=model_name,
            )

        embedding_result = AIService().get_embedding(
            feature=AIRequestLog.Feature.EMBEDDING,
            text=source_text,
            task_type="retrieval_document",
            title=product.name,
            fallback=[],
            model_name=model_name,
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
            return EmbeddingIndexResult(
                product_id=str(product.pk),
                status="unavailable",
                content_hash=source_hash,
                model_name=embedding_result.model_name or model_name,
                ai_used=bool(embedding_result.ai_used),
                fallback_used=True,
            )

        effective_model = embedding_result.model_name or model_name
        effective_lookup = {
            **lookup,
            "model_name": effective_model,
            "content_hash": source_hash,
        }
        with transaction.atomic():
            embedding, _ = ProductEmbedding.objects.update_or_create(
                **effective_lookup,
                defaults={
                    "embedding": vector,
                    "source_text": source_text,
                    "indexed_at": timezone.now(),
                },
            )
            ProductEmbedding.objects.filter(
                product=product,
                variant__isnull=True,
                language_code="vi",
                model_name=effective_model,
            ).exclude(pk=embedding.pk).delete()

        return EmbeddingIndexResult(
            product_id=str(product.pk),
            status="indexed",
            content_hash=source_hash,
            model_name=effective_model,
            ai_used=True,
            fallback_used=False,
        )

    generate = index_product
