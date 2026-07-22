from django.contrib.auth import get_user_model

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
