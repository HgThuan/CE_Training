from django.core.paginator import EmptyPage, Paginator
from django.db.models import BooleanField, Count, Exists, OuterRef, Q, Value
from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from apps.account.models import Shop, User
from apps.common.exceptions import BusinessError
from apps.common.responses import success_response
from apps.product.models import Product
from apps.product.selectors import ProductSelector
from apps.product.serializers import PublicProductListSerializer

from .models import ShopFollower

SHOP_SORTS = {
    "newest": "-created_at",
    "price_asc": "price",
    "price_desc": "-price",
    "rating": "-rating",
}


class PublicShopQuerySerializer(serializers.Serializer):
    page = serializers.IntegerField(min_value=1, default=1)
    page_size = serializers.IntegerField(min_value=1, max_value=100, default=20)
    sort = serializers.ChoiceField(choices=tuple(SHOP_SORTS), default="newest")


class PublicShopSerializer(serializers.ModelSerializer):
    total_products = serializers.IntegerField(read_only=True)
    follower_count = serializers.IntegerField(read_only=True)
    is_following = serializers.BooleanField(read_only=True)

    class Meta:
        model = Shop
        fields = (
            "id",
            "name",
            "slug",
            "description",
            "logo_url",
            "cover_url",
            "average_rating",
            "total_products",
            "follower_count",
            "is_following",
            "created_at",
        )
        read_only_fields = fields


class PublicShopDataSerializer(serializers.Serializer):
    shop = PublicShopSerializer()
    products = PublicProductListSerializer(many=True)
    available_filters = serializers.ListField(child=serializers.CharField())
    available_sorts = serializers.ListField(child=serializers.CharField())


class PublicShopMetaSerializer(serializers.Serializer):
    page = serializers.IntegerField()
    page_size = serializers.IntegerField()
    total_items = serializers.IntegerField()
    total_pages = serializers.IntegerField()


class PublicShopResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    message = serializers.CharField()
    data = PublicShopDataSerializer()
    meta = PublicShopMetaSerializer()


def get_public_shop(*, slug: str, user) -> Shop | None:
    active_followers = Q(
        followers__user__role=User.Role.CUSTOMER,
        followers__user__is_active=True,
        followers__user__is_deleted=False,
    )
    queryset = Shop.objects.filter(
        slug=slug,
        status=Shop.Status.APPROVED,
        is_deleted=False,
        owner__is_active=True,
        owner__is_deleted=False,
    ).annotate(
        total_products=Count(
            "products",
            filter=Q(
                products__status=Product.Status.APPROVED,
                products__is_deleted=False,
                products__category__is_active=True,
                products__category__is_deleted=False,
            ),
            distinct=True,
        ),
        follower_count=Count(
            "followers",
            filter=active_followers,
            distinct=True,
        ),
    )
    if (
        getattr(user, "is_authenticated", False)
        and getattr(user, "role", None) == User.Role.CUSTOMER
        and getattr(user, "is_active", False)
        and not getattr(user, "is_deleted", True)
    ):
        queryset = queryset.annotate(
            is_following=Exists(
                ShopFollower.objects.filter(
                    shop_id=OuterRef("pk"),
                    user_id=user.pk,
                )
            )
        )
    else:
        queryset = queryset.annotate(
            is_following=Value(False, output_field=BooleanField()),
        )
    return queryset.first()


class PublicShopView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        parameters=[PublicShopQuerySerializer],
        responses={200: PublicShopResponseSerializer},
    )
    def get(self, request, slug: str):
        query = PublicShopQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        shop = get_public_shop(slug=slug, user=request.user)
        if shop is None:
            raise BusinessError("Không tìm thấy gian hàng", http_status=404)

        products = ProductSelector.filter_public(
            ProductSelector.public_list(),
            {
                "shop": shop.pk,
                "sort": SHOP_SORTS[query.validated_data["sort"]],
            },
        )
        paginator = Paginator(products, query.validated_data["page_size"])
        try:
            page = paginator.page(query.validated_data["page"])
        except EmptyPage as exc:
            raise BusinessError("Trang sản phẩm không tồn tại", http_status=404) from exc

        return success_response(
            message="Lấy thông tin gian hàng thành công",
            data={
                "shop": PublicShopSerializer(shop).data,
                "products": PublicProductListSerializer(
                    page.object_list,
                    many=True,
                    context={"request": request},
                ).data,
                "available_filters": ["category", "brand", "price", "rating"],
                "available_sorts": list(SHOP_SORTS),
            },
            meta={
                "page": page.number,
                "page_size": query.validated_data["page_size"],
                "total_items": paginator.count,
                "total_pages": paginator.num_pages,
            },
        )
