from django.urls import path

from apps.engagement.public_shop import PublicShopView

from .views import (
    AddressDetailView,
    AddressListCreateView,
    AdminCustomerDetailView,
    AdminCustomerListCreateView,
    AdminResetPasswordView,
    AdminRoleUserListView,
    AdminSellerApplicationApproveView,
    AdminSellerApplicationDetailView,
    AdminSellerApplicationListView,
    AdminSellerApplicationRejectView,
    AdminSellerDetailView,
    AdminSellerDocumentReviewView,
    AdminSellerListView,
    AdminShopLockView,
    AdminShopUnlockView,
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
    SellerApplicationView,
    SellerDocumentUploadView,
    SellerShopView,
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
        "admin/users/",
        AdminRoleUserListView.as_view(),
        name="admin-role-user-list",
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
    path(
        "seller-applications/me/",
        SellerApplicationView.as_view(),
        name="seller-application-me",
    ),
    path(
        "seller-applications/me/documents/",
        SellerDocumentUploadView.as_view(),
        name="seller-document-upload",
    ),
    path(
        "admin/seller-applications/",
        AdminSellerApplicationListView.as_view(),
        name="admin-seller-application-list",
    ),
    path(
        "admin/seller-applications/<int:profile_id>/",
        AdminSellerApplicationDetailView.as_view(),
        name="admin-seller-application-detail",
    ),
    path(
        "admin/seller-applications/<int:profile_id>/approve/",
        AdminSellerApplicationApproveView.as_view(),
        name="admin-seller-application-approve",
    ),
    path(
        "admin/seller-applications/<int:profile_id>/reject/",
        AdminSellerApplicationRejectView.as_view(),
        name="admin-seller-application-reject",
    ),
    path(
        "admin/seller-documents/<int:document_id>/review/",
        AdminSellerDocumentReviewView.as_view(),
        name="admin-seller-document-review",
    ),
    path("admin/sellers/", AdminSellerListView.as_view(), name="admin-seller-list"),
    path(
        "admin/sellers/<int:user_id>/",
        AdminSellerDetailView.as_view(),
        name="admin-seller-detail",
    ),
    path(
        "admin/shops/<int:shop_id>/lock/",
        AdminShopLockView.as_view(),
        name="admin-shop-lock",
    ),
    path(
        "admin/shops/<int:shop_id>/unlock/",
        AdminShopUnlockView.as_view(),
        name="admin-shop-unlock",
    ),
    path("seller/shop/", SellerShopView.as_view(), name="seller-shop"),
    path(
        "seller/shops/<int:shop_id>/",
        SellerShopView.as_view(),
        name="seller-shop-detail",
    ),
    path("shops/<slug:slug>/", PublicShopView.as_view(), name="public-shop"),
]
