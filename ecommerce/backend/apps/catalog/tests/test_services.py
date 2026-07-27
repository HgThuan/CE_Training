import pytest

from apps.catalog.models import Category
from apps.catalog.selectors import BrandSelector, CategorySelector
from apps.catalog.services import BrandService, CategoryService
from apps.common.exceptions import BusinessError


@pytest.mark.django_db
def test_category_service_create_update_and_soft_delete():
    category = CategoryService.create(
        name="  Phụ kiện  ",
        image_url="https://cdn.example.com/category.png",
    )
    updated = CategoryService.update(
        category=category,
        data={
            "name": "Phụ kiện công nghệ",
            "sort_order": 4,
            "is_active": False,
        },
    )
    deleted = CategoryService.soft_delete(category=updated)

    assert updated.name == "Phụ kiện công nghệ"
    assert updated.slug == "phu-kien"
    assert updated.sort_order == 4
    assert deleted.is_deleted is True
    assert deleted.deleted_at is not None


@pytest.mark.django_db
def test_brand_service_create_update_and_soft_delete():
    brand = BrandService.create(name="  Local Brand  ")
    updated = BrandService.update(
        brand=brand,
        data={
            "name": "Local Brand Vietnam",
            "description": "Thương hiệu nội địa",
        },
    )
    deleted = BrandService.soft_delete(brand=updated)

    assert updated.name == "Local Brand Vietnam"
    assert updated.slug == "local-brand"
    assert updated.description == "Thương hiệu nội địa"
    assert deleted.is_deleted is True
    assert deleted.deleted_at is not None


@pytest.mark.django_db
def test_category_selector_builds_multilevel_public_tree():
    root = CategoryService.create(name="Điện tử", sort_order=1)
    child = CategoryService.create(name="Điện thoại", parent=root, sort_order=1)
    grandchild = CategoryService.create(name="Android", parent=child, sort_order=1)
    CategoryService.create(name="Danh mục ẩn", is_active=False)

    tree = CategorySelector.public_tree()

    assert [category.pk for category in tree] == [root.pk]
    root_node = tree[0]
    child_node = root_node._tree_children[0]
    grandchild_node = child_node._tree_children[0]
    assert [category.pk for category in root_node._tree_children] == [child.pk]
    assert [category.pk for category in child_node._tree_children] == [grandchild.pk]
    assert grandchild_node._tree_children == []


@pytest.mark.django_db
def test_admin_and_public_selectors_apply_expected_visibility():
    active_category = CategoryService.create(name="Category active")
    inactive_category = CategoryService.create(name="Category inactive", is_active=False)
    active_brand = BrandService.create(name="Brand active")
    inactive_brand = BrandService.create(name="Brand inactive", is_active=False)

    assert set(CategorySelector.admin_list().values_list("pk", flat=True)) == {
        active_category.pk,
        inactive_category.pk,
    }
    assert list(BrandSelector.public_list().values_list("pk", flat=True)) == [active_brand.pk]
    assert set(BrandSelector.admin_list().values_list("pk", flat=True)) == {
        active_brand.pk,
        inactive_brand.pk,
    }


@pytest.mark.django_db
def test_category_service_rejects_parent_child_cycle():
    root = CategoryService.create(name="Root")
    child = CategoryService.create(name="Child", parent=root)

    with pytest.raises(BusinessError, match="vòng lặp"):
        CategoryService.update(category=root, data={"parent": child})

    root.refresh_from_db()
    assert root.parent_id is None


@pytest.mark.django_db
def test_category_reorder_updates_parent_and_order_atomically():
    first = CategoryService.create(name="First")
    second = CategoryService.create(name="Second")

    reordered = CategoryService.reorder(
        items=[
            {"id": first.pk, "sort_order": 2},
            {"id": second.pk, "parent_id": first.pk, "sort_order": 1},
        ]
    )

    first.refresh_from_db()
    second.refresh_from_db()
    assert [category.pk for category in reordered] == [first.pk, second.pk]
    assert first.sort_order == 2
    assert second.parent_id == first.pk
    assert second.sort_order == 1


@pytest.mark.django_db
def test_category_reorder_rejects_cycle_and_rolls_back():
    first = CategoryService.create(name="First")
    second = CategoryService.create(name="Second")

    with pytest.raises(BusinessError, match="vòng lặp"):
        CategoryService.reorder(
            items=[
                {"id": first.pk, "parent_id": second.pk, "sort_order": 0},
                {"id": second.pk, "parent_id": first.pk, "sort_order": 1},
            ]
        )

    assert Category.objects.get(pk=first.pk).parent_id is None
    assert Category.objects.get(pk=second.pk).parent_id is None


@pytest.mark.django_db
def test_soft_delete_parent_requires_children_to_be_removed_first():
    parent = CategoryService.create(name="Parent")
    child = CategoryService.create(name="Child", parent=parent)

    with pytest.raises(BusinessError, match="danh mục con"):
        CategoryService.soft_delete(category=parent)

    CategoryService.soft_delete(category=child)
    deleted_parent = CategoryService.soft_delete(category=parent)
    assert deleted_parent.is_deleted is True
    assert deleted_parent.is_active is False
    assert deleted_parent.deleted_at is not None


@pytest.mark.django_db
def test_brand_name_is_unique_case_insensitively():
    BrandService.create(name="OpenAI")

    with pytest.raises(BusinessError, match="đã được sử dụng"):
        BrandService.create(name="openai", slug="openai-vietnam")
