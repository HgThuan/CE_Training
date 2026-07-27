from unittest.mock import patch
from urllib.parse import urlparse

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from apps.account.models import Notification, SellerDocument, SellerProfile, Shop, User
from apps.account.services import SellerOnboardingService, ShopBusinessPolicy
from apps.common.exceptions import BusinessError
from apps.common.models import AuditLog

from .factories import SellerProfileFactory, ShopFactory, UserFactory


@pytest.fixture(autouse=True)
def isolated_media_root(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path


@pytest.mark.django_db
def test_seller_onboarding_approval_creates_shop_role_notification_and_audit(
    api_client,
    admin_user,
    django_capture_on_commit_callbacks,
):
    customer = UserFactory()
    api_client.force_authenticate(customer)
    submitted = api_client.post(
        reverse("account:seller-application-me"),
        {
            "business_name": "Cửa hàng Tương Lai",
            "business_address": "12 Lê Lợi, Quận 1, TP.HCM",
            "tax_code": "0312345678",
            "contact_phone": "0901234567",
            "user_id": admin_user.pk,
        },
        format="json",
    )
    profile = SellerProfile.objects.get(user=customer)
    document_response = api_client.post(
        reverse("account:seller-document-upload"),
        {
            "document_type": SellerDocument.DocumentType.BUSINESS_LICENSE,
            "document": SimpleUploadedFile(
                "license.pdf",
                b"%PDF-1.4 seller license",
                content_type="application/pdf",
            ),
            "seller_profile_id": 999999,
        },
        format="multipart",
    )

    api_client.force_authenticate(admin_user)
    with (
        patch("apps.account.tasks.send_seller_application_status_email.delay") as send_email,
        django_capture_on_commit_callbacks(execute=True),
    ):
        approved = api_client.post(
            reverse(
                "account:admin-seller-application-approve",
                kwargs={"profile_id": profile.pk},
            ),
            {},
            format="json",
            HTTP_X_REQUEST_ID="approve-request-1",
        )

    customer.refresh_from_db()
    profile.refresh_from_db()
    shop = Shop.objects.get(owner=customer)
    assert submitted.status_code == 201
    assert document_response.status_code == 201
    assert approved.status_code == 200
    assert customer.role == User.Role.SELLER
    assert profile.onboarding_status == SellerProfile.OnboardingStatus.APPROVED
    assert shop.slug == "cua-hang-tuong-lai"
    assert Notification.objects.filter(user=customer).exists()
    assert AuditLog.objects.filter(
        action="approve_seller",
        request_id="approve-request-1",
    ).exists()
    send_email.assert_called_once_with(customer.pk, True, "")


@pytest.mark.django_db
def test_seller_rejection_requires_reason_and_sends_notification(
    api_client,
    admin_user,
    django_capture_on_commit_callbacks,
):
    profile = SellerProfileFactory()
    api_client.force_authenticate(admin_user)

    missing_reason = api_client.post(
        reverse(
            "account:admin-seller-application-reject",
            kwargs={"profile_id": profile.pk},
        ),
        {},
        format="json",
    )
    with (
        patch("apps.account.tasks.send_seller_application_status_email.delay") as send_email,
        django_capture_on_commit_callbacks(execute=True),
    ):
        rejected = api_client.post(
            reverse(
                "account:admin-seller-application-reject",
                kwargs={"profile_id": profile.pk},
            ),
            {"reason": "Thiếu giấy phép kinh doanh hợp lệ"},
            format="json",
        )

    profile.refresh_from_db()
    assert missing_reason.status_code == 400
    assert rejected.status_code == 200
    assert profile.onboarding_status == SellerProfile.OnboardingStatus.REJECTED
    assert profile.rejection_reason == "Thiếu giấy phép kinh doanh hợp lệ"
    assert Notification.objects.filter(user=profile.user).exists()
    send_email.assert_called_once_with(
        profile.user_id,
        False,
        "Thiếu giấy phép kinh doanh hợp lệ",
    )


@pytest.mark.django_db
def test_admin_can_verify_document_and_request_additional_information(api_client, admin_user):
    profile = SellerProfileFactory()
    document = SellerDocument.objects.create(
        seller_profile=profile,
        document_type=SellerDocument.DocumentType.ID_CARD,
        file=SimpleUploadedFile("id.pdf", b"%PDF-1.4"),
        original_name="id.pdf",
    )
    api_client.force_authenticate(admin_user)

    response = api_client.post(
        reverse(
            "account:admin-seller-document-review",
            kwargs={"document_id": document.pk},
        ),
        {
            "review_status": SellerDocument.ReviewStatus.ADDITIONAL_REQUIRED,
            "reason": "Ảnh bị mờ, cần tải lại",
        },
        format="json",
    )

    document.refresh_from_db()
    profile.refresh_from_db()
    assert response.status_code == 200
    assert document.review_status == SellerDocument.ReviewStatus.ADDITIONAL_REQUIRED
    assert profile.verification_status == SellerProfile.VerificationStatus.UNVERIFIED


@pytest.mark.django_db
def test_seller_document_upload_rejects_spoofed_pdf(api_client):
    customer = UserFactory()
    SellerProfileFactory(user=customer)
    api_client.force_authenticate(customer)

    response = api_client.post(
        reverse("account:seller-document-upload"),
        {
            "document_type": SellerDocument.DocumentType.ID_CARD,
            "document": SimpleUploadedFile(
                "fake.pdf",
                b"not a real pdf",
                content_type="application/pdf",
            ),
        },
        format="multipart",
    )

    assert response.status_code == 400
    assert SellerDocument.objects.count() == 0


@pytest.mark.django_db
def test_seller_document_uses_expiring_protected_download_link(api_client):
    customer = UserFactory()
    SellerProfileFactory(user=customer)
    api_client.force_authenticate(customer)
    uploaded = api_client.post(
        reverse("account:seller-document-upload"),
        {
            "document_type": SellerDocument.DocumentType.ID_CARD,
            "document": SimpleUploadedFile(
                "identity.pdf",
                b"%PDF-1.4 protected",
                content_type="application/pdf",
            ),
        },
        format="multipart",
    )
    download_path = urlparse(uploaded.data["data"]["file_url"]).path

    downloaded = api_client.get(download_path)
    content = b"".join(downloaded.streaming_content)
    downloaded.close()
    tampered = api_client.get(f"{download_path}tampered/")
    document = SellerDocument.objects.get()

    assert uploaded.status_code == 201
    assert download_path.startswith("/protected-media/seller-documents/")
    assert "/media/private/" not in uploaded.data["data"]["file_url"]
    assert document.file.name.startswith("private/seller-documents/")
    assert downloaded.status_code == 200
    assert content.startswith(b"%PDF-")
    assert tampered.status_code == 404


@pytest.mark.django_db
def test_seller_a_cannot_read_or_update_seller_b_shop_by_changing_url_id(api_client):
    seller_a = UserFactory(role=User.Role.SELLER)
    seller_b = UserFactory(role=User.Role.SELLER)
    SellerProfileFactory(
        user=seller_a,
        onboarding_status=SellerProfile.OnboardingStatus.APPROVED,
    )
    SellerProfileFactory(
        user=seller_b,
        onboarding_status=SellerProfile.OnboardingStatus.APPROVED,
    )
    shop_a = ShopFactory(owner=seller_a)
    shop_b = ShopFactory(owner=seller_b)
    api_client.force_authenticate(seller_a)

    read_other = api_client.get(
        reverse("account:seller-shop-detail", kwargs={"shop_id": shop_b.pk}),
    )
    update_other = api_client.patch(
        reverse("account:seller-shop-detail", kwargs={"shop_id": shop_b.pk}),
        {"name": "Compromised"},
        format="json",
    )
    update_own = api_client.patch(
        reverse("account:seller-shop-detail", kwargs={"shop_id": shop_a.pk}),
        {"name": "Seller A Updated"},
        format="json",
    )

    shop_a.refresh_from_db()
    shop_b.refresh_from_db()
    assert read_other.status_code == 404
    assert update_other.status_code == 404
    assert update_own.status_code == 200
    assert shop_a.name == "Seller A Updated"
    assert shop_b.name != "Compromised"


@pytest.mark.django_db
def test_seller_updates_logo_and_cover_urls(api_client):
    seller = UserFactory(role=User.Role.SELLER)
    SellerProfileFactory(
        user=seller,
        onboarding_status=SellerProfile.OnboardingStatus.APPROVED,
    )
    shop = ShopFactory(owner=seller)
    api_client.force_authenticate(seller)

    logo_url = "https://cdn.example.com/shops/seller/logo.webp"
    cover_url = "https://cdn.example.com/shops/seller/cover.webp"
    response = api_client.patch(
        reverse("account:seller-shop"),
        {
            "logo_url": logo_url,
            "cover_url": cover_url,
        },
        format="json",
    )

    shop.refresh_from_db()
    api_client.force_authenticate(user=None)
    public_response = api_client.get(
        reverse("account:public-shop", kwargs={"slug": shop.slug}),
    )
    assert response.status_code == 200
    assert shop.logo_url == logo_url
    assert shop.cover_url == cover_url
    assert response.data["data"]["logo_url"] == logo_url
    assert response.data["data"]["cover_url"] == cover_url
    assert public_response.status_code == 200
    assert public_response.data["data"]["shop"]["logo_url"] == logo_url
    assert public_response.data["data"]["shop"]["cover_url"] == cover_url


@pytest.mark.django_db
def test_shop_update_rejects_invalid_image_urls_and_non_seller(api_client):
    seller = UserFactory(role=User.Role.SELLER)
    customer = UserFactory()
    SellerProfileFactory(
        user=seller,
        onboarding_status=SellerProfile.OnboardingStatus.APPROVED,
    )
    ShopFactory(owner=seller)

    api_client.force_authenticate(seller)
    invalid_url = api_client.patch(
        reverse("account:seller-shop"),
        {"logo_url": "not-a-public-url"},
        format="json",
    )
    api_client.force_authenticate(customer)
    forbidden = api_client.patch(
        reverse("account:seller-shop"),
        {"logo_url": "https://cdn.example.com/shops/customer/logo.webp"},
        format="json",
    )

    assert invalid_url.status_code == 400
    assert forbidden.status_code == 403


@pytest.mark.django_db
def test_admin_shop_lock_hides_public_shop_and_blocks_new_resource_policy(
    api_client,
    admin_user,
    django_capture_on_commit_callbacks,
):
    seller = UserFactory(role=User.Role.SELLER)
    SellerProfileFactory(
        user=seller,
        onboarding_status=SellerProfile.OnboardingStatus.APPROVED,
    )
    shop = ShopFactory(owner=seller)
    public_url = reverse("account:public-shop", kwargs={"slug": shop.slug})
    assert api_client.get(public_url).status_code == 200

    api_client.force_authenticate(admin_user)
    with (
        patch("apps.account.tasks.send_shop_status_email.delay") as send_email,
        django_capture_on_commit_callbacks(execute=True),
    ):
        locked = api_client.post(
            reverse("account:admin-shop-lock", kwargs={"shop_id": shop.pk}),
            {"reason": "Vi phạm chính sách hàng giả"},
            format="json",
        )

    shop.refresh_from_db()
    api_client.force_authenticate(user=None)
    hidden = api_client.get(public_url)
    assert locked.status_code == 200
    assert hidden.status_code == 404
    assert ShopBusinessPolicy.can_create_new_resource(shop=shop) is False
    send_email.assert_called_once_with(seller.pk, True, "Vi phạm chính sách hàng giả")


@pytest.mark.django_db
def test_admin_seller_list_edit_and_soft_delete(api_client, admin_user):
    seller = UserFactory(role=User.Role.SELLER)
    SellerProfileFactory(
        user=seller,
        onboarding_status=SellerProfile.OnboardingStatus.APPROVED,
    )
    shop = ShopFactory(owner=seller)
    api_client.force_authenticate(admin_user)

    listed = api_client.get(reverse("account:admin-seller-list"), {"search": shop.name})
    updated = api_client.patch(
        reverse("account:admin-seller-detail", kwargs={"user_id": seller.pk}),
        {"name": "Admin Updated Shop"},
        format="json",
    )
    deleted = api_client.delete(
        reverse("account:admin-seller-detail", kwargs={"user_id": seller.pk}),
        {"reason": "Seller yêu cầu đóng tài khoản"},
        format="json",
    )

    seller.refresh_from_db()
    shop.refresh_from_db()
    assert listed.status_code == 200
    assert listed.data["meta"]["total_items"] == 1
    assert updated.status_code == 200
    assert deleted.status_code == 200
    assert seller.is_deleted is True
    assert shop.is_deleted is True
    assert shop.status == Shop.Status.LOCKED


@pytest.mark.django_db
@pytest.mark.parametrize("role", [User.Role.CUSTOMER, User.Role.SELLER])
def test_non_admin_roles_cannot_access_sensitive_admin_seller_apis(api_client, role):
    user = UserFactory(role=role)
    api_client.force_authenticate(user)

    applications = api_client.get(reverse("account:admin-seller-application-list"))
    sellers = api_client.get(reverse("account:admin-seller-list"))

    assert applications.status_code == 403
    assert sellers.status_code == 403


@pytest.mark.django_db
def test_seller_application_queries_ignore_client_supplied_identity(api_client):
    customer = UserFactory()
    victim = UserFactory()
    victim_profile = SellerProfileFactory(user=victim)
    api_client.force_authenticate(customer)

    response = api_client.post(
        reverse("account:seller-application-me"),
        {
            "business_name": "Safe Shop",
            "business_address": "Hà Nội",
            "tax_code": "0101234567",
            "contact_phone": "0912345678",
            "user_id": victim.pk,
            "seller_profile_id": victim_profile.pk,
        },
        format="json",
    )

    assert response.status_code == 201
    assert SellerProfile.objects.get(user=customer).business_name == "Safe Shop"
    victim_profile.refresh_from_db()
    assert victim_profile.business_name != "Safe Shop"


@pytest.mark.django_db
def test_onboarding_service_rejects_duplicate_pending_submission():
    customer = UserFactory()
    payload = {
        "business_name": "First Shop",
        "business_address": "Đà Nẵng",
        "tax_code": "0401234567",
        "contact_phone": "0909876543",
    }
    SellerOnboardingService.submit_application(user=customer, application_data=payload)

    with pytest.raises(BusinessError) as exception:
        SellerOnboardingService.submit_application(user=customer, application_data=payload)

    assert "đang chờ duyệt" in str(exception.value)
