from django.urls import path

from .views import (
    AddressDetailView,
    AddressListCreateView,
    AdminCustomerDetailView,
    AdminCustomerListCreateView,
    AdminResetPasswordView,
    AssignRoleView,
    AvatarUploadView,
    ChangePasswordView,
    ForgotPasswordView,
    LockUserView,
    LoginView,
    LogoutView,
    MeView,
    RefreshView,
    RegisterView,
    ResendVerificationView,
    ResetPasswordView,
    SessionView,
    SetDefaultAddressView,
    UnlockUserView,
    VerifyEmailView,
)

app_name = "account"

urlpatterns = [
    path("auth/register/", RegisterView.as_view(), name="register"),
    path("auth/verify-email/", VerifyEmailView.as_view(), name="verify-email"),
    path(
        "auth/resend-verification/",
        ResendVerificationView.as_view(),
        name="resend-verification",
    ),
    path("auth/login/", LoginView.as_view(), name="login"),
    path("auth/session/", SessionView.as_view(), name="session"),
    path("auth/refresh/", RefreshView.as_view(), name="refresh"),
    path("auth/logout/", LogoutView.as_view(), name="logout"),
    path("auth/forgot-password/", ForgotPasswordView.as_view(), name="forgot-password"),
    path("auth/reset-password/", ResetPasswordView.as_view(), name="reset-password"),
    path("users/me/", MeView.as_view(), name="me"),
    path("users/me/avatar/", AvatarUploadView.as_view(), name="avatar-upload"),
    path(
        "users/me/addresses/",
        AddressListCreateView.as_view(),
        name="address-list",
    ),
    path(
        "users/me/addresses/<int:address_id>/",
        AddressDetailView.as_view(),
        name="address-detail",
    ),
    path(
        "users/me/addresses/<int:address_id>/set-default/",
        SetDefaultAddressView.as_view(),
        name="address-set-default",
    ),
    path(
        "users/me/change-password/",
        ChangePasswordView.as_view(),
        name="change-password",
    ),
    path(
        "admin/users/<int:user_id>/assign-role/",
        AssignRoleView.as_view(),
        name="assign-role",
    ),
    path(
        "admin/customers/",
        AdminCustomerListCreateView.as_view(),
        name="admin-customer-list",
    ),
    path(
        "admin/customers/<int:customer_id>/",
        AdminCustomerDetailView.as_view(),
        name="admin-customer-detail",
    ),
    path(
        "admin/users/<int:user_id>/lock/",
        LockUserView.as_view(),
        name="lock-user",
    ),
    path(
        "admin/users/<int:user_id>/unlock/",
        UnlockUserView.as_view(),
        name="unlock-user",
    ),
    path(
        "admin/users/<int:user_id>/reset-password/",
        AdminResetPasswordView.as_view(),
        name="admin-reset-password",
    ),
]
