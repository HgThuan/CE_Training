from uuid import UUID

from django.contrib.postgres.search import (
    SearchQuery,
    SearchRank,
    SearchVector,
    TrigramSimilarity,
)
from django.db import connections
from django.db.models import Exists, F, FloatField, OuterRef, Prefetch, Q, QuerySet, Value
from django.db.models.functions import Greatest

from apps.account.models import Shop, User
from apps.common.exceptions import BusinessError

from .models import (
    Attribute,
    AttributeValue,
    Product,
    ProductAttributeValue,
    ProductMedia,
    ProductVariant,
    VariantAttributeValue,
)

SEARCH_CONFIG = "simple"


def _filter_uuid_or_slug(queryset: QuerySet[Product], relation: str, value):
    try:
        object_id = UUID(str(value))
    except (TypeError, ValueError):
        return queryset.filter(**{f"{relation}__slug": str(value)})
    return queryset.filter(**{f"{relation}_id": object_id})


def _apply_public_filters(
    queryset: QuerySet[Product],
    params: dict,
) -> QuerySet[Product]:
    if category := params.get("category"):
        queryset = _filter_uuid_or_slug(queryset, "category", category)
    if brand := params.get("brand"):
        queryset = _filter_uuid_or_slug(queryset, "brand", brand)
    if shop := params.get("shop"):
        try:
            shop_id = int(shop)
        except (TypeError, ValueError):
            queryset = queryset.filter(shop__slug=str(shop))
        else:
            queryset = queryset.filter(shop_id=shop_id)

    price_min = params.get("price_min")
    if price_min is not None:
        queryset = queryset.filter(max_price__gte=price_min)
    price_max = params.get("price_max")
    if price_max is not None:
        queryset = queryset.filter(min_price__lte=price_max)
    rating_min = params.get("rating_min")
    if rating_min is not None:
        queryset = queryset.filter(rating_average__gte=rating_min)

    if params.get("in_stock") is not None:
        stocked_variants = ProductVariant.objects.filter(
            product_id=OuterRef("pk"),
            is_active=True,
            is_deleted=False,
            inventory_balance__available_stock__gt=0,
        )
        queryset = queryset.annotate(has_available_stock=Exists(stocked_variants)).filter(
            has_available_stock=params["in_stock"]
        )
    return queryset


class ProductSelector:
    SORT_EXPRESSIONS = {
        "created_at": (F("created_at").asc(),),
        "-created_at": (F("created_at").desc(),),
        "price": (F("min_price").asc(nulls_last=True),),
        "-price": (F("min_price").desc(nulls_last=True),),
        "sold_count": (F("sold_count").asc(),),
        "-sold_count": (F("sold_count").desc(),),
        "rating": (F("rating_average").asc(),),
        "-rating": (F("rating_average").desc(),),
        "avg_rating": (F("rating_average").asc(),),
        "-avg_rating": (F("rating_average").desc(),),
    }

    @staticmethod
    def _with_relations(
        queryset: QuerySet[Product],
        *,
        public_only: bool = False,
    ) -> QuerySet[Product]:
        variant_attribute_links = VariantAttributeValue.objects.select_related(
            "attribute",
            "attribute_value",
        ).order_by("attribute__sort_order", "attribute__name")
        variant_queryset = ProductVariant.objects.filter(is_deleted=False)
        if public_only:
            variant_queryset = variant_queryset.filter(is_active=True)
        variants = (
            variant_queryset.select_related("shop", "inventory_balance")
            .prefetch_related(
                Prefetch(
                    "variant_attribute_links",
                    queryset=variant_attribute_links,
                )
            )
            .order_by("created_at", "id")
        )
        product_attribute_links = ProductAttributeValue.objects.select_related(
            "attribute_value__attribute"
        ).order_by(
            "attribute_value__attribute__sort_order",
            "attribute_value__sort_order",
        )
        return queryset.select_related(
            "shop",
            "shop__owner",
            "category",
            "brand",
            "approved_by",
        ).prefetch_related(
            Prefetch(
                "media",
                queryset=ProductMedia.objects.order_by(
                    "sort_order",
                    "created_at",
                    "id",
                ),
            ),
            Prefetch("variants", queryset=variants),
            Prefetch(
                "product_attribute_links",
                queryset=product_attribute_links,
            ),
        )

    @staticmethod
    def _with_list_relations(queryset: QuerySet[Product]) -> QuerySet[Product]:
        list_images = ProductMedia.objects.filter(
            media_type=ProductMedia.MediaType.IMAGE,
        ).order_by(
            "-is_primary",
            "sort_order",
            "created_at",
            "id",
        )
        return queryset.select_related("shop", "category", "brand").prefetch_related(
            Prefetch("media", queryset=list_images, to_attr="_public_list_images")
        )

    @staticmethod
    def public_base() -> QuerySet[Product]:
        return Product.objects.filter(
            status=Product.Status.APPROVED,
            is_deleted=False,
            shop__status=Shop.Status.APPROVED,
            shop__is_deleted=False,
            shop__owner__is_active=True,
            shop__owner__is_deleted=False,
            category__is_active=True,
            category__is_deleted=False,
        )

    @staticmethod
    def public_list() -> QuerySet[Product]:
        return ProductSelector._with_list_relations(ProductSelector.public_base())

    @staticmethod
    def public_queryset() -> QuerySet[Product]:
        """Backward-compatible public list queryset."""

        return ProductSelector.public_list()

    @staticmethod
    def for_seller(seller_user) -> QuerySet[Product]:
        if (
            getattr(seller_user, "role", None) != User.Role.SELLER
            or not getattr(seller_user, "is_active", False)
            or getattr(seller_user, "is_deleted", True)
        ):
            return Product.objects.none()
        queryset = Product.objects.filter(
            shop__owner=seller_user,
            shop__is_deleted=False,
            is_deleted=False,
        )
        return ProductSelector._with_relations(queryset)

    @staticmethod
    def filter_for_seller(
        queryset: QuerySet[Product],
        params: dict,
    ) -> QuerySet[Product]:
        if status := params.get("status"):
            queryset = queryset.filter(status=status)
        if category_id := params.get("category_id"):
            queryset = queryset.filter(category_id=category_id)
        if search := params.get("search"):
            queryset = queryset.filter(name__icontains=search)
        sort = params.get("sort", "-created_at")
        return queryset.order_by(*ProductSelector.SORT_EXPRESSIONS[sort], "id")

    @staticmethod
    def filter_public(
        queryset: QuerySet[Product],
        params: dict,
    ) -> QuerySet[Product]:
        queryset = _apply_public_filters(queryset, params)
        if query := params.get("q"):
            queryset = queryset.filter(
                Q(name__icontains=query)
                | Q(short_description__icontains=query)
                | Q(description__icontains=query)
            )
        sort = params.get("sort", "-created_at")
        return queryset.order_by(*ProductSelector.SORT_EXPRESSIONS[sort], "id")

    @staticmethod
    def admin_pending() -> QuerySet[Product]:
        return ProductSelector._with_relations(
            Product.objects.filter(
                status=Product.Status.PENDING_REVIEW,
                is_deleted=False,
            )
        )

    @staticmethod
    def admin_all(filter_params: dict | None = None) -> QuerySet[Product]:
        params = filter_params or {}
        queryset = Product.objects.all()
        exact_filters = {
            "status": "status",
            "shop_id": "shop_id",
            "category_id": "category_id",
            "brand_id": "brand_id",
        }
        for param, lookup in exact_filters.items():
            value = params.get(param)
            if value not in (None, ""):
                queryset = queryset.filter(**{lookup: value})

        is_deleted = params.get("is_deleted")
        if is_deleted not in (None, ""):
            if isinstance(is_deleted, str):
                is_deleted = is_deleted.lower() in {"1", "true", "yes"}
            queryset = queryset.filter(is_deleted=bool(is_deleted))

        search = str(params.get("search", "")).strip()
        if search:
            queryset = queryset.filter(Q(name__icontains=search) | Q(slug__icontains=search))
        return ProductSelector._with_relations(queryset)

    @staticmethod
    def public_detail(*, slug: str, shop_slug: str | None = None) -> Product | None:
        matches = ProductSelector._with_relations(
            ProductSelector.public_base(), public_only=True
        ).filter(slug=slug)
        if shop_slug:
            return matches.filter(shop__slug=shop_slug).first()
        first_two = list(matches[:2])
        if len(first_two) > 1:
            raise BusinessError(
                "Slug sản phẩm tồn tại ở nhiều gian hàng",
                errors={"shop_slug": ["Vui lòng cung cấp shop_slug để xác định đúng sản phẩm"]},
            )
        return first_two[0] if first_two else None

    @staticmethod
    def media_for_product(
        *,
        product: Product,
        media_id,
    ) -> ProductMedia | None:
        return (
            ProductMedia.objects.select_related("product__shop")
            .filter(pk=media_id, product=product)
            .first()
        )

    @staticmethod
    def variant_for_product(
        *,
        product: Product,
        variant_id,
    ) -> ProductVariant | None:
        return (
            ProductVariant.objects.select_related(
                "product__shop",
                "shop",
                "inventory_balance",
            )
            .prefetch_related(
                "variant_attribute_links__attribute",
                "variant_attribute_links__attribute_value",
            )
            .filter(
                pk=variant_id,
                product=product,
                shop_id=product.shop_id,
                is_deleted=False,
            )
            .first()
        )

    @staticmethod
    def variants_for_product(
        *,
        product: Product,
        variant_ids=None,
    ) -> QuerySet[ProductVariant]:
        queryset = (
            ProductVariant.objects.select_related(
                "product__shop",
                "shop",
                "inventory_balance",
            )
            .prefetch_related(
                "variant_attribute_links__attribute",
                "variant_attribute_links__attribute_value",
            )
            .filter(
                product=product,
                shop_id=product.shop_id,
                is_deleted=False,
            )
            .order_by("created_at", "id")
        )
        if variant_ids is not None:
            queryset = queryset.filter(pk__in=variant_ids)
        return queryset

    @staticmethod
    def variant_by_barcode(*, seller_user, barcode: str) -> ProductVariant | None:
        if (
            getattr(seller_user, "role", None) != User.Role.SELLER
            or not getattr(seller_user, "is_active", False)
            or getattr(seller_user, "is_deleted", True)
        ):
            return None
        return (
            ProductVariant.objects.select_related(
                "product",
                "product__shop",
                "shop",
                "inventory_balance",
            )
            .prefetch_related(
                "variant_attribute_links__attribute",
                "variant_attribute_links__attribute_value",
            )
            .filter(
                shop__owner=seller_user,
                product__is_deleted=False,
                is_deleted=False,
                barcode=barcode,
            )
            .first()
        )

    @staticmethod
    def attributes_for_seller(seller_user) -> QuerySet[Attribute]:
        if (
            getattr(seller_user, "role", None) != User.Role.SELLER
            or not getattr(seller_user, "is_active", False)
            or getattr(seller_user, "is_deleted", True)
        ):
            return Attribute.objects.none()
        values = AttributeValue.objects.order_by("sort_order", "value", "id")
        return (
            Attribute.objects.filter(Q(shop__isnull=True) | Q(shop__owner=seller_user))
            .select_related("shop")
            .prefetch_related(Prefetch("values", queryset=values))
            .order_by("sort_order", "name", "id")
        )

    @staticmethod
    def detail_with_relations(
        product_id_or_slug,
        *,
        shop: Shop | None = None,
        queryset: QuerySet[Product] | None = None,
    ) -> Product | None:
        """
        Resolve a detail object with eager-loaded relations.

        Product slugs are unique only inside a shop. Callers should therefore
        provide ``shop`` for slug lookup; an unscoped slug is accepted only
        when it identifies exactly one row.
        """

        base_queryset = ProductSelector._with_relations(
            queryset if queryset is not None else Product.objects.all()
        )
        try:
            product_id = UUID(str(product_id_or_slug))
        except (TypeError, ValueError):
            product_id = None
        if product_id is not None:
            return base_queryset.filter(pk=product_id).first()

        matches = base_queryset.filter(slug=str(product_id_or_slug))
        if shop is not None:
            return matches.filter(shop=shop).first()
        first_two = list(matches[:2])
        if len(first_two) > 1:
            raise BusinessError(
                "Slug sản phẩm cần được scope theo gian hàng",
                errors={"shop": ["Hãy cung cấp gian hàng khi tra cứu bằng slug"]},
            )
        return first_two[0] if first_two else None


class SearchSelector:
    @staticmethod
    def _postgres_search(
        queryset: QuerySet[Product],
        query_text: str,
    ) -> QuerySet[Product]:
        search_document = (
            SearchVector("name", weight="A", config=SEARCH_CONFIG)
            + SearchVector("short_description", weight="B", config=SEARCH_CONFIG)
            + SearchVector("description", weight="C", config=SEARCH_CONFIG)
        )
        search_query = SearchQuery(
            query_text,
            config=SEARCH_CONFIG,
            search_type="websearch",
        )
        return (
            queryset.annotate(
                search_document=search_document,
                search_rank=SearchRank(search_document, search_query),
                trigram_similarity=TrigramSimilarity("name", query_text),
            )
            .filter(Q(search_document=search_query) | Q(name__trigram_similar=query_text))
            .annotate(
                relevance=Greatest("search_rank", "trigram_similarity"),
            )
        )

    @staticmethod
    def _fallback_search(
        queryset: QuerySet[Product],
        query_text: str,
    ) -> QuerySet[Product]:
        return queryset.filter(
            Q(name__icontains=query_text)
            | Q(short_description__icontains=query_text)
            | Q(description__icontains=query_text)
        ).annotate(relevance=Value(0.0, output_field=FloatField()))

    @staticmethod
    def search(params: dict) -> QuerySet[Product]:
        queryset = _apply_public_filters(ProductSelector.public_list(), params)
        query_text = str(params.get("q", "")).strip()
        if query_text:
            if connections[queryset.db].vendor == "postgresql":
                queryset = SearchSelector._postgres_search(queryset, query_text)
            else:
                queryset = SearchSelector._fallback_search(queryset, query_text)

        sort = params.get("sort")
        if sort:
            if sort == "relevance":
                return queryset.order_by(
                    F("relevance").desc(),
                    F("created_at").desc(),
                    "id",
                )
            return queryset.order_by(*ProductSelector.SORT_EXPRESSIONS[sort], "id")
        if query_text:
            return queryset.order_by(
                F("relevance").desc(),
                F("created_at").desc(),
                "id",
            )
        return queryset.order_by(F("created_at").desc(), "id")

    @staticmethod
    def suggestions(*, query: str, limit: int = 10) -> QuerySet[Product]:
        queryset = ProductSelector.public_base().select_related("shop")
        if connections[queryset.db].vendor == "postgresql":
            return (
                queryset.annotate(similarity=TrigramSimilarity("name", query))
                .filter(Q(name__istartswith=query) | Q(name__trigram_similar=query))
                .order_by("-similarity", "name", "id")[:limit]
            )
        return queryset.filter(name__icontains=query).order_by("name", "id")[:limit]
