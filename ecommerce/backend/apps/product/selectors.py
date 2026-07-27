from uuid import UUID

from django.db.models import F, Prefetch, Q, QuerySet

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
            variant_queryset.select_related("shop")
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
    def public_queryset() -> QuerySet[Product]:
        queryset = Product.objects.filter(
            status=Product.Status.APPROVED,
            is_deleted=False,
            shop__status=Shop.Status.APPROVED,
            shop__is_deleted=False,
            shop__owner__is_active=True,
            shop__owner__is_deleted=False,
            category__is_active=True,
            category__is_deleted=False,
        )
        return ProductSelector._with_relations(queryset, public_only=True)

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
        if category_id := params.get("category_id"):
            queryset = queryset.filter(category_id=category_id)
        if brand_id := params.get("brand_id"):
            queryset = queryset.filter(brand_id=brand_id)
        min_price = params.get("min_price")
        if min_price is not None:
            queryset = queryset.filter(max_price__gte=min_price)
        max_price = params.get("max_price")
        if max_price is not None:
            queryset = queryset.filter(min_price__lte=max_price)
        if search := params.get("search"):
            queryset = queryset.filter(name__icontains=search)
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
        matches = ProductSelector.public_queryset().filter(slug=slug)
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
            ProductVariant.objects.select_related("product__shop", "shop")
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
            ProductVariant.objects.select_related("product__shop", "shop")
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
