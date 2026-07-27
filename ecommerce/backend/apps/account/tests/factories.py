import factory
from django.utils import timezone

from apps.account.models import SellerProfile, Shop, User


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    email = factory.Sequence(lambda number: f"user-{number}@example.com")
    full_name = factory.Faker("name")
    is_email_verified = True

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        password = kwargs.pop("password", "StrongPass!234")
        return model_class.objects.create_user(*args, password=password, **kwargs)


class SellerProfileFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = SellerProfile

    user = factory.SubFactory(UserFactory)
    business_name = factory.Sequence(lambda number: f"Shop {number}")
    business_address = "1 Nguyễn Huệ, Quận 1, TP.HCM"
    tax_code = factory.Sequence(lambda number: f"031{number:07d}")
    contact_phone = "0901234567"
    submitted_at = factory.LazyFunction(timezone.now)


class ShopFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Shop

    owner = factory.SubFactory(UserFactory, role=User.Role.SELLER)
    name = factory.Sequence(lambda number: f"Approved Shop {number}")
    slug = factory.Sequence(lambda number: f"approved-shop-{number}")
    status = Shop.Status.APPROVED
