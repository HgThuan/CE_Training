from rest_framework import serializers

from .models import Brand, Category


class CategoryCreateSerializer(serializers.ModelSerializer):
    slug = serializers.SlugField(max_length=180, required=False)
    image_url = serializers.URLField(allow_blank=True, allow_null=True, required=False)
    parent = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.filter(is_deleted=False),
        allow_null=True,
        required=False,
    )
    sort_order = serializers.IntegerField(default=0, min_value=0)

    class Meta:
        model = Category
        fields = ("name", "slug", "parent", "image_url", "sort_order", "is_active")


class CategoryUpdateSerializer(serializers.ModelSerializer):
    slug = serializers.SlugField(max_length=180, required=False)
    image_url = serializers.URLField(allow_blank=True, allow_null=True, required=False)
    parent = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.filter(is_deleted=False),
        allow_null=True,
        required=False,
    )
    sort_order = serializers.IntegerField(min_value=0, required=False)

    class Meta:
        model = Category
        fields = ("name", "slug", "parent", "image_url", "sort_order", "is_active")
        extra_kwargs = {
            "name": {"required": False},
            "is_active": {"required": False},
        }

    def validate(self, attrs):
        if not attrs:
            raise serializers.ValidationError("Cần cung cấp ít nhất một trường để cập nhật")
        return attrs


class CategoryTreeSerializer(serializers.ModelSerializer):
    parent_id = serializers.UUIDField(allow_null=True, read_only=True)
    children = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = (
            "id",
            "parent_id",
            "name",
            "slug",
            "image_url",
            "sort_order",
            "is_active",
            "children",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields

    def get_children(self, category: Category) -> list[dict]:
        children = getattr(category, "_tree_children", [])
        return CategoryTreeSerializer(children, many=True, context=self.context).data


class CategoryReorderItemSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    parent_id = serializers.UUIDField(allow_null=True, required=False)
    sort_order = serializers.IntegerField(min_value=0)


class CategoryReorderSerializer(serializers.Serializer):
    items = CategoryReorderItemSerializer(many=True, allow_empty=False)

    def validate_items(self, items):
        category_ids = [item["id"] for item in items]
        if len(category_ids) != len(set(category_ids)):
            raise serializers.ValidationError("Mỗi danh mục chỉ được xuất hiện một lần")
        return items


class BrandCreateSerializer(serializers.ModelSerializer):
    slug = serializers.SlugField(max_length=180, required=False)
    logo_url = serializers.URLField(allow_blank=True, allow_null=True, required=False)

    class Meta:
        model = Brand
        fields = ("name", "slug", "logo_url", "description", "is_active")


class BrandUpdateSerializer(serializers.ModelSerializer):
    slug = serializers.SlugField(max_length=180, required=False)
    logo_url = serializers.URLField(allow_blank=True, allow_null=True, required=False)

    class Meta:
        model = Brand
        fields = ("name", "slug", "logo_url", "description", "is_active")
        extra_kwargs = {
            "name": {"required": False},
            "description": {"required": False, "allow_null": True, "allow_blank": True},
            "is_active": {"required": False},
        }

    def validate(self, attrs):
        if not attrs:
            raise serializers.ValidationError("Cần cung cấp ít nhất một trường để cập nhật")
        return attrs


class BrandListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Brand
        fields = (
            "id",
            "name",
            "slug",
            "logo_url",
            "description",
            "is_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class CatalogPaginationMetaSerializer(serializers.Serializer):
    page = serializers.IntegerField()
    page_size = serializers.IntegerField()
    total_items = serializers.IntegerField()
    total_pages = serializers.IntegerField()


class CategoryResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    message = serializers.CharField()
    data = CategoryTreeSerializer()


class CategoryTreeResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    message = serializers.CharField()
    data = CategoryTreeSerializer(many=True)


class CategoryListResponseSerializer(CategoryTreeResponseSerializer):
    meta = CatalogPaginationMetaSerializer()


class CategoryReorderResponseSerializer(CategoryTreeResponseSerializer):
    pass


class BrandResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    message = serializers.CharField()
    data = BrandListSerializer()


class BrandListResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    message = serializers.CharField()
    data = BrandListSerializer(many=True)
    meta = CatalogPaginationMetaSerializer()


class DeleteResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    message = serializers.CharField()
    data = serializers.DictField()
