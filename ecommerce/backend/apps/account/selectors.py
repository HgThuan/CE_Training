from django.contrib.auth import get_user_model

from .models import SellerDocument, SellerProfile, Shop

User = get_user_model()


def get_user_by_email(email: str):
    normalized_email = User.objects.normalize_login_email(email)
    return User.objects.filter(email=normalized_email, is_deleted=False).first()


def get_user_for_profile(user_id: int):
    return (
        User.objects.select_related("customer_profile", "seller_profile", "admin_profile")
        .filter(pk=user_id)
        .first()
    )


def get_customer_for_admin(user_id: int):
    return (
        User.objects.select_related("customer_profile")
        .prefetch_related("addresses")
        .filter(pk=user_id, role=User.Role.CUSTOMER, is_deleted=False)
        .first()
    )


def get_seller_application_for_user(user):
    return (
        SellerProfile.objects.select_related("user", "reviewed_by")
        .prefetch_related("documents")
        .filter(user=user, is_deleted=False)
        .first()
    )


def get_seller_application_for_admin(profile_id: int):
    return (
        SellerProfile.objects.select_related("user", "reviewed_by")
        .prefetch_related(
            "documents",
        )
        .filter(pk=profile_id, is_deleted=False)
        .first()
    )


def seller_applications_for_admin():
    return (
        SellerProfile.objects.select_related("user", "reviewed_by")
        .prefetch_related("documents")
        .filter(is_deleted=False)
    )


def sellers_for_admin():
    return User.objects.select_related("seller_profile", "shop").filter(
        role=User.Role.SELLER, is_deleted=False
    )


def get_seller_for_admin(user_id: int):
    return (
        sellers_for_admin().prefetch_related("seller_profile__documents").filter(pk=user_id).first()
    )


def get_shop_for_owner(user, shop_id: int | None = None):
    queryset = Shop.objects.select_related("owner").filter(owner=user, is_deleted=False)
    if shop_id is not None:
        queryset = queryset.filter(pk=shop_id)
    return queryset.first()


def get_public_shop(slug: str):
    return (
        Shop.objects.select_related("owner")
        .filter(
            slug=slug,
            status=Shop.Status.APPROVED,
            is_deleted=False,
            owner__is_active=True,
            owner__is_deleted=False,
        )
        .first()
    )


def get_document_for_admin(document_id: int):
    return (
        SellerDocument.objects.select_related("seller_profile__user")
        .filter(pk=document_id, is_deleted=False)
        .first()
    )
