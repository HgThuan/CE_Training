from uuid import UUID

import pytest
from django.db.models.deletion import RestrictedError

from apps.catalog.services import BrandService, CategoryService


@pytest.mark.django_db
def test_category_and_brand_creation_generate_slugs_and_uuid_primary_keys():
    category = CategoryService.create(name="Dien thoai va phu kien")
    brand = BrandService.create(name="Thuong hieu Viet")

    assert isinstance(category.pk, UUID)
    assert category.slug == "dien-thoai-va-phu-kien"
    assert category.created_at is not None
    assert category.updated_at is not None
    assert isinstance(brand.pk, UUID)
    assert brand.slug == "thuong-hieu-viet"
    assert brand.created_at is not None
    assert brand.updated_at is not None


@pytest.mark.django_db
def test_slug_override_is_normalized_and_duplicate_auto_slug_gets_suffix():
    first = CategoryService.create(name="Laptop")
    second = CategoryService.create(name="Laptop")
    brand = BrandService.create(name="Cong nghe Viet", slug="Viet Brand")

    assert first.slug == "laptop"
    assert second.slug == "laptop-2"
    assert brand.slug == "viet-brand"


@pytest.mark.django_db
def test_parent_foreign_key_restricts_hard_delete():
    parent = CategoryService.create(name="Thiet bi")
    CategoryService.create(name="Thiet bi deo", parent=parent)

    with pytest.raises(RestrictedError):
        parent.delete()


@pytest.mark.django_db
def test_category_and_brand_soft_delete_fields_are_populated_together():
    category = CategoryService.create(name="Danh muc tam")
    brand = BrandService.create(name="Thuong hieu tam")

    deleted_category = CategoryService.soft_delete(category=category)
    deleted_brand = BrandService.soft_delete(brand=brand)

    for deleted_object in (deleted_category, deleted_brand):
        assert deleted_object.is_deleted is True
        assert deleted_object.is_active is False
        assert deleted_object.deleted_at is not None
