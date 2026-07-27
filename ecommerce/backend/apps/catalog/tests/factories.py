import factory

from apps.catalog.models import Brand, Category


class CategoryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Category

    name = factory.Sequence(lambda number: f"Category {number}")
    slug = factory.Sequence(lambda number: f"category-{number}")


class BrandFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Brand

    name = factory.Sequence(lambda number: f"Brand {number}")
    slug = factory.Sequence(lambda number: f"brand-{number}")
