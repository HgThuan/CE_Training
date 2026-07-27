from collections import defaultdict

from django.db.models import QuerySet

from .models import Brand, Category


class CategorySelector:
    @staticmethod
    def public_tree() -> list[Category]:
        categories = list(
            Category.objects.filter(is_active=True, is_deleted=False).order_by(
                "sort_order",
                "name",
                "id",
            )
        )
        categories_by_id = {category.pk: category for category in categories}
        children_by_parent: dict = defaultdict(list)
        for category in categories:
            children_by_parent[category.parent_id].append(category)

        for category in categories:
            category._tree_children = children_by_parent[category.pk]

        return [
            category
            for category in children_by_parent[None]
            if category.parent_id is None and category.pk in categories_by_id
        ]

    @staticmethod
    def admin_list() -> QuerySet[Category]:
        return (
            Category.objects.filter(is_deleted=False)
            .select_related("parent")
            .order_by(
                "sort_order",
                "name",
                "id",
            )
        )

    @staticmethod
    def get_for_admin(category_id) -> Category | None:
        return CategorySelector.admin_list().filter(pk=category_id).first()


class BrandSelector:
    @staticmethod
    def public_list() -> QuerySet[Brand]:
        return Brand.objects.filter(is_active=True, is_deleted=False).order_by("name", "id")

    @staticmethod
    def admin_list() -> QuerySet[Brand]:
        return Brand.objects.filter(is_deleted=False).order_by("name", "id")

    @staticmethod
    def get_for_admin(brand_id) -> Brand | None:
        return BrandSelector.admin_list().filter(pk=brand_id).first()
