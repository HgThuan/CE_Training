from decimal import Decimal
from pathlib import Path
from uuid import uuid4

from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.core.validators import RegexValidator
from django.db import models
from django.db.models.functions import Lower

phone_validator = RegexValidator(
    regex=r"^\+?[0-9]{9,15}$",
    message="Số điện thoại phải gồm 9-15 chữ số và có thể bắt đầu bằng dấu +",
)


def seller_document_upload_to(instance, filename: str) -> str:
    extension = Path(filename).suffix.lower()
    return f"private/seller-documents/{instance.seller_profile.user_id}/{uuid4().hex}{extension}"


# Kept for migration 0004 compatibility. Shop images are URL-only from migration 0005 onward.
def shop_logo_upload_to(instance, filename: str) -> str:
    return f"shops/{instance.owner_id}/logo/{uuid4().hex}.webp"


# Kept for migration 0004 compatibility. Shop images are URL-only from migration 0005 onward.
def shop_cover_upload_to(instance, filename: str) -> str:
    return f"shops/{instance.owner_id}/cover/{uuid4().hex}.webp"


class UserManager(BaseUserManager):
    use_in_migrations = True

    @staticmethod
    def normalize_login_email(email: str) -> str:
        return BaseUserManager.normalize_email(email).strip().lower()

    def _create_user(self, email: str, password: str | None, **extra_fields):
        if not email:
            raise ValueError("Email là bắt buộc")

        email = self.normalize_login_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email: str, password: str | None = None, **extra_fields):
        extra_fields.setdefault("role", User.Role.CUSTOMER)
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email: str, password: str | None = None, **extra_fields):
        extra_fields.setdefault("role", User.Role.ADMIN)
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_email_verified", True)

        if extra_fields.get("role") != User.Role.ADMIN:
            raise ValueError("Superuser phải có vai trò admin")
        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser phải có is_staff=True")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser phải có is_superuser=True")

        user = self._create_user(email, password, **extra_fields)
        AdminProfile.objects.get_or_create(user=user)
        return user


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class User(AbstractBaseUser, PermissionsMixin, TimeStampedModel):
    class Role(models.TextChoices):
        ADMIN = "admin", "Admin"
        SELLER = "seller", "Seller"
        CUSTOMER = "customer", "Customer"

    class Gender(models.TextChoices):
        MALE = "male", "Nam"
        FEMALE = "female", "Nữ"
        OTHER = "other", "Khác"

    email = models.EmailField(max_length=255, unique=True)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.CUSTOMER)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_email_verified = models.BooleanField(default=False)
    must_change_password = models.BooleanField(default=False)
    token_version = models.PositiveIntegerField(default=0)
    google_id = models.CharField(max_length=255, unique=True, null=True, blank=True)
    avatar_url = models.URLField(max_length=500, blank=True)
    full_name = models.CharField(max_length=255, blank=True)
    phone = models.CharField(max_length=20, blank=True, validators=[phone_validator])
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=10, choices=Gender.choices, blank=True)
    is_deleted = models.BooleanField(default=False, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    lock_reason = models.CharField(max_length=500, blank=True)
    locked_at = models.DateTimeField(null=True, blank=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS: list[str] = []

    class Meta:
        ordering = ("-created_at",)
        constraints = [
            models.UniqueConstraint(Lower("email"), name="account_user_email_ci_unique"),
        ]
        indexes = [
            models.Index(fields=["role"], name="account_user_role_idx"),
            models.Index(fields=["is_active"], name="account_user_active_idx"),
        ]

    def __str__(self) -> str:
        return self.email


class CustomerProfile(TimeStampedModel):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="customer_profile",
    )
    loyalty_points = models.PositiveIntegerField(default=0)
    wallet_balance = models.DecimalField(max_digits=12, decimal_places=0, default=Decimal("0"))

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(wallet_balance__gte=0),
                name="customer_wallet_balance_nonnegative",
            ),
        ]


class Address(TimeStampedModel):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="addresses",
    )
    recipient_name = models.CharField(max_length=255)
    phone = models.CharField(max_length=20, validators=[phone_validator])
    province = models.CharField(max_length=100)
    district = models.CharField(max_length=100)
    ward = models.CharField(max_length=100)
    detail_address = models.CharField(max_length=500)
    is_default = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-is_default", "-updated_at")
        constraints = [
            models.UniqueConstraint(
                fields=["user"],
                condition=models.Q(is_default=True, is_deleted=False),
                name="account_address_one_active_default",
            ),
        ]
        indexes = [
            models.Index(
                fields=["user", "is_deleted"],
                name="acct_addr_user_active_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.recipient_name} - {self.detail_address}"


class SellerProfile(TimeStampedModel):
    class OnboardingStatus(models.TextChoices):
        PENDING = "pending", "Chờ duyệt"
        APPROVED = "approved", "Đã duyệt"
        REJECTED = "rejected", "Từ chối"

    class VerificationStatus(models.TextChoices):
        UNVERIFIED = "unverified", "Chưa xác minh"
        PENDING = "pending", "Chờ xác minh"
        VERIFIED = "verified", "Đã xác minh"

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="seller_profile",
    )
    business_name = models.CharField(max_length=255, blank=True)
    business_address = models.CharField(max_length=500, blank=True)
    tax_code = models.CharField(max_length=50, blank=True)
    contact_phone = models.CharField(
        max_length=20,
        blank=True,
        validators=[phone_validator],
    )
    onboarding_status = models.CharField(
        max_length=20,
        choices=OnboardingStatus.choices,
        default=OnboardingStatus.PENDING,
        db_index=True,
    )
    rejection_reason = models.TextField(blank=True)
    id_card_document_url = models.URLField(max_length=500, blank=True)
    business_license_url = models.URLField(max_length=500, blank=True)
    verification_status = models.CharField(
        max_length=20,
        choices=VerificationStatus.choices,
        default=VerificationStatus.UNVERIFIED,
        db_index=True,
    )
    submitted_at = models.DateTimeField(null=True, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        related_name="reviewed_seller_profiles",
        null=True,
        blank=True,
    )
    is_deleted = models.BooleanField(default=False, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-submitted_at", "-created_at")
        indexes = [
            models.Index(
                fields=["onboarding_status", "created_at"],
                name="seller_status_created_idx",
            ),
        ]


class SellerDocument(TimeStampedModel):
    class DocumentType(models.TextChoices):
        ID_CARD = "id_card", "CCCD/CMND"
        BUSINESS_LICENSE = "business_license", "Giấy phép kinh doanh"
        TAX_REGISTRATION = "tax_registration", "Đăng ký thuế"
        OTHER = "other", "Khác"

    class ReviewStatus(models.TextChoices):
        PENDING = "pending", "Chờ xác minh"
        VERIFIED = "verified", "Đã xác minh"
        ADDITIONAL_REQUIRED = "additional_required", "Yêu cầu bổ sung"

    seller_profile = models.ForeignKey(
        SellerProfile,
        on_delete=models.CASCADE,
        related_name="documents",
    )
    document_type = models.CharField(
        max_length=30,
        choices=DocumentType.choices,
        db_index=True,
    )
    file = models.FileField(upload_to=seller_document_upload_to)
    original_name = models.CharField(max_length=255)
    review_status = models.CharField(
        max_length=30,
        choices=ReviewStatus.choices,
        default=ReviewStatus.PENDING,
        db_index=True,
    )
    review_reason = models.TextField(blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        related_name="reviewed_seller_documents",
        null=True,
        blank=True,
    )
    is_deleted = models.BooleanField(default=False, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("document_type", "-created_at")
        indexes = [
            models.Index(
                fields=["seller_profile", "is_deleted"],
                name="seller_doc_profile_active_idx",
            ),
        ]


class Shop(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Chờ duyệt"
        APPROVED = "approved", "Đã duyệt"
        REJECTED = "rejected", "Từ chối"
        LOCKED = "locked", "Bị khóa"

    owner = models.OneToOneField(
        User,
        on_delete=models.PROTECT,
        related_name="shop",
    )
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    description = models.TextField(blank=True)
    logo_url = models.URLField(max_length=500, blank=True)
    cover_url = models.URLField(max_length=500, blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.APPROVED,
        db_index=True,
    )
    lock_reason = models.TextField(blank=True)
    locked_at = models.DateTimeField(null=True, blank=True)
    average_rating = models.DecimalField(max_digits=3, decimal_places=2, default=Decimal("0"))
    is_deleted = models.BooleanField(default=False, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["status", "is_deleted"], name="shop_status_active_idx"),
            models.Index(fields=["created_at"], name="shop_created_idx"),
        ]

    def __str__(self) -> str:
        return self.name


class Notification(TimeStampedModel):
    class Kind(models.TextChoices):
        SELLER_APPLICATION = "seller_application", "Hồ sơ seller"
        DOCUMENT_REVIEW = "document_review", "Xác minh giấy tờ"
        SHOP_STATUS = "shop_status", "Trạng thái gian hàng"

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    kind = models.CharField(max_length=30, choices=Kind.choices, db_index=True)
    title = models.CharField(max_length=255)
    message = models.TextField()
    metadata = models.JSONField(default=dict, blank=True)
    is_read = models.BooleanField(default=False, db_index=True)
    is_deleted = models.BooleanField(default=False, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(
                fields=["user", "is_read", "created_at"],
                name="notif_user_read_created_idx",
            ),
        ]


class AdminProfile(TimeStampedModel):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="admin_profile",
    )
    permission_level = models.CharField(max_length=50, default="full")
