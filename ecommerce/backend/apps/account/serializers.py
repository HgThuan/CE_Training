from datetime import date

from django.conf import settings
from django.core import signing
from django.urls import reverse
from PIL import Image, UnidentifiedImageError
from rest_framework import serializers

from .models import (
    Address,
    AdminProfile,
    CustomerProfile,
    SellerDocument,
    SellerProfile,
    Shop,
    User,
)
from .validators import validate_matching_passwords, validate_new_password


class BlankToNullDateField(serializers.DateField):
    """Accept the empty value emitted when an optional HTML date input is cleared."""

    def to_internal_value(self, value):
        if value == "":
            return None
        return super().to_internal_value(value)


class CustomerProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomerProfile
        fields = ("loyalty_points", "wallet_balance")
        read_only_fields = fields


class SellerDocumentSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = SellerDocument
        fields = (
            "id",
            "document_type",
            "file_url",
            "original_name",
            "review_status",
            "review_reason",
            "reviewed_at",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields

    def get_file_url(self, obj) -> str:
        if not obj.file:
            return ""
        request = self.context.get("request")
        token = signing.dumps(
            {"document_id": obj.pk},
            salt="seller-document-download",
        )
        url = reverse("seller-document-download", kwargs={"token": token})
        return request.build_absolute_uri(url) if request else url


class SellerProfileSerializer(serializers.ModelSerializer):
    documents = serializers.SerializerMethodField()

    class Meta:
        model = SellerProfile
        fields = (
            "id",
            "business_name",
            "business_address",
            "tax_code",
            "contact_phone",
            "onboarding_status",
            "rejection_reason",
            "verification_status",
            "submitted_at",
            "reviewed_at",
            "documents",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields

    def get_documents(self, obj) -> list[dict]:
        documents = [document for document in obj.documents.all() if not document.is_deleted]
        return SellerDocumentSerializer(
            documents,
            many=True,
            context=self.context,
        ).data


class AdminProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdminProfile
        fields = ("permission_level",)
        read_only_fields = fields


class UserSerializer(serializers.ModelSerializer):
    profile = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "role",
            "is_active",
            "is_email_verified",
            "must_change_password",
            "avatar_url",
            "full_name",
            "phone",
            "date_of_birth",
            "gender",
            "profile",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "email",
            "role",
            "is_active",
            "is_email_verified",
            "must_change_password",
            "avatar_url",
            "profile",
            "created_at",
            "updated_at",
        )

    def get_profile(self, obj) -> dict | None:
        serializers_by_role = {
            User.Role.CUSTOMER: ("customer_profile", CustomerProfileSerializer),
            User.Role.SELLER: ("seller_profile", SellerProfileSerializer),
            User.Role.ADMIN: ("admin_profile", AdminProfileSerializer),
        }
        relation_name, serializer_class = serializers_by_role[obj.role]
        try:
            profile = getattr(obj, relation_name)
        except (
            CustomerProfile.DoesNotExist,
            SellerProfile.DoesNotExist,
            AdminProfile.DoesNotExist,
        ):
            return None
        return serializer_class(profile).data

    def validate_date_of_birth(self, value):
        if value and value > date.today():
            raise serializers.ValidationError("Ngày sinh không thể nằm trong tương lai")
        return value


class AvatarUploadSerializer(serializers.Serializer):
    avatar = serializers.ImageField(write_only=True)

    def validate_avatar(self, value):
        max_bytes = settings.MAX_AVATAR_UPLOAD_MB * 1024 * 1024
        if value.size > max_bytes:
            raise serializers.ValidationError(
                f"Ảnh đại diện không được vượt quá {settings.MAX_AVATAR_UPLOAD_MB} MB"
            )
        if value.content_type not in {"image/jpeg", "image/png", "image/webp"}:
            raise serializers.ValidationError("Chỉ chấp nhận ảnh JPEG, PNG hoặc WebP")
        return value


class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = (
            "id",
            "recipient_name",
            "phone",
            "province",
            "district",
            "ward",
            "detail_address",
            "is_default",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")


class AdminCustomerListSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "full_name",
            "phone",
            "is_active",
            "is_email_verified",
            "must_change_password",
            "created_at",
        )
        read_only_fields = fields


class AdminCustomerDetailSerializer(AdminCustomerListSerializer):
    profile = CustomerProfileSerializer(source="customer_profile", read_only=True)
    addresses = serializers.SerializerMethodField()

    class Meta(AdminCustomerListSerializer.Meta):
        fields = AdminCustomerListSerializer.Meta.fields + (
            "avatar_url",
            "date_of_birth",
            "gender",
            "is_deleted",
            "deleted_at",
            "lock_reason",
            "locked_at",
            "profile",
            "addresses",
            "updated_at",
        )
        read_only_fields = fields

    def get_addresses(self, obj) -> list[dict]:
        queryset = obj.addresses.filter(is_deleted=False)
        return AddressSerializer(queryset, many=True).data


class AdminCustomerCreateSerializer(serializers.Serializer):
    email = serializers.EmailField(max_length=255)
    password = serializers.CharField(write_only=True, trim_whitespace=False)
    password_confirm = serializers.CharField(write_only=True, trim_whitespace=False)
    full_name = serializers.CharField(max_length=255, required=False, allow_blank=True)
    phone = serializers.RegexField(
        regex=r"^\+?[0-9]{9,15}$",
        required=False,
        allow_blank=True,
        error_messages={"invalid": "Số điện thoại không hợp lệ"},
    )
    date_of_birth = BlankToNullDateField(required=False, allow_null=True)
    gender = serializers.ChoiceField(
        choices=User.Gender.choices,
        required=False,
        allow_blank=True,
    )
    is_email_verified = serializers.BooleanField(default=False)

    def validate_password(self, value: str) -> str:
        return validate_new_password(value)

    def validate_date_of_birth(self, value):
        if value and value > date.today():
            raise serializers.ValidationError("Ngày sinh không thể nằm trong tương lai")
        return value

    def validate(self, attrs):
        validate_matching_passwords(attrs)
        attrs.pop("password_confirm")
        return attrs


class AdminCustomerUpdateSerializer(serializers.Serializer):
    email = serializers.EmailField(max_length=255, required=False)
    full_name = serializers.CharField(max_length=255, required=False, allow_blank=True)
    phone = serializers.RegexField(
        regex=r"^\+?[0-9]{9,15}$",
        required=False,
        allow_blank=True,
        error_messages={"invalid": "Số điện thoại không hợp lệ"},
    )
    avatar_url = serializers.URLField(max_length=500, required=False, allow_blank=True)
    date_of_birth = BlankToNullDateField(required=False, allow_null=True)
    gender = serializers.ChoiceField(
        choices=User.Gender.choices,
        required=False,
        allow_blank=True,
    )
    is_email_verified = serializers.BooleanField(required=False)

    def validate_date_of_birth(self, value):
        if value and value > date.today():
            raise serializers.ValidationError("Ngày sinh không thể nằm trong tương lai")
        return value


class AccountStatusSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=500, min_length=3)


class AdminResetPasswordSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=500, min_length=3, required=False, allow_blank=True)


class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField(max_length=255)
    password = serializers.CharField(write_only=True, trim_whitespace=False)
    password_confirm = serializers.CharField(write_only=True, trim_whitespace=False)
    full_name = serializers.CharField(max_length=255, required=False, allow_blank=True)

    def validate_password(self, value: str) -> str:
        return validate_new_password(value)

    def validate(self, attrs):
        validate_matching_passwords(attrs)
        attrs.pop("password_confirm")
        return attrs


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField(max_length=255)
    password = serializers.CharField(write_only=True, trim_whitespace=False)


class EmailSerializer(serializers.Serializer):
    email = serializers.EmailField(max_length=255)


class VerifyEmailSerializer(serializers.Serializer):
    token = serializers.CharField(trim_whitespace=False)


class RefreshSerializer(serializers.Serializer):
    refresh = serializers.CharField(required=False, allow_blank=False, trim_whitespace=False)


class ResetPasswordSerializer(serializers.Serializer):
    uid = serializers.CharField(trim_whitespace=False)
    token = serializers.CharField(trim_whitespace=False)
    new_password = serializers.CharField(write_only=True, trim_whitespace=False)
    new_password_confirm = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate_new_password(self, value: str) -> str:
        return validate_new_password(value)

    def validate(self, attrs):
        validate_matching_passwords(attrs, password_field="new_password")
        attrs.pop("new_password_confirm")
        return attrs


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True, trim_whitespace=False)
    new_password = serializers.CharField(write_only=True, trim_whitespace=False)
    new_password_confirm = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate_new_password(self, value: str) -> str:
        return validate_new_password(value, user=self.context["request"].user)

    def validate(self, attrs):
        validate_matching_passwords(attrs, password_field="new_password")
        attrs.pop("new_password_confirm")
        return attrs


class AssignRoleSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=User.Role.choices)


class AdminRoleUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "full_name",
            "phone",
            "role",
            "is_active",
        )
        read_only_fields = fields


class SellerApplicationSubmitSerializer(serializers.Serializer):
    business_name = serializers.CharField(max_length=255)
    business_address = serializers.CharField(max_length=500)
    tax_code = serializers.CharField(max_length=50)
    contact_phone = serializers.RegexField(
        regex=r"^\+?[0-9]{9,15}$",
        error_messages={"invalid": "Số điện thoại không hợp lệ"},
    )


class SellerDocumentUploadSerializer(serializers.Serializer):
    document_type = serializers.ChoiceField(choices=SellerDocument.DocumentType.choices)
    document = serializers.FileField(write_only=True)

    def validate_document(self, value):
        max_size = settings.MAX_SELLER_DOCUMENT_UPLOAD_MB * 1024 * 1024
        if value.size > max_size:
            raise serializers.ValidationError(
                f"Giấy tờ không được vượt quá {settings.MAX_SELLER_DOCUMENT_UPLOAD_MB} MB"
            )
        allowed_types = {"image/jpeg", "image/png", "application/pdf"}
        if value.content_type not in allowed_types:
            raise serializers.ValidationError("Chỉ chấp nhận JPEG, PNG hoặc PDF")
        try:
            value.seek(0)
            if value.content_type == "application/pdf":
                if value.read(5) != b"%PDF-":
                    raise serializers.ValidationError("Nội dung tệp không phải PDF hợp lệ")
            else:
                with Image.open(value) as image:
                    image.verify()
                    expected_formats = {
                        "image/jpeg": "JPEG",
                        "image/png": "PNG",
                    }
                    if image.format != expected_formats[value.content_type]:
                        raise serializers.ValidationError(
                            "Nội dung ảnh không khớp với loại tệp khai báo"
                        )
        except (UnidentifiedImageError, OSError, ValueError) as exc:
            raise serializers.ValidationError("Nội dung giấy tờ không hợp lệ") from exc
        finally:
            value.seek(0)
        return value


class SellerApplicationReviewSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=1000, required=False, allow_blank=True)


class SellerDocumentReviewSerializer(serializers.Serializer):
    review_status = serializers.ChoiceField(choices=SellerDocument.ReviewStatus.choices)
    reason = serializers.CharField(max_length=1000, required=False, allow_blank=True)


class ShopSerializer(serializers.ModelSerializer):
    owner_id = serializers.IntegerField(read_only=True)
    owner_email = serializers.EmailField(source="owner.email", read_only=True)
    total_products = serializers.SerializerMethodField()

    class Meta:
        model = Shop
        fields = (
            "id",
            "owner_id",
            "owner_email",
            "name",
            "slug",
            "description",
            "logo_url",
            "cover_url",
            "status",
            "lock_reason",
            "locked_at",
            "average_rating",
            "total_products",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "owner_id",
            "owner_email",
            "slug",
            "logo_url",
            "cover_url",
            "status",
            "lock_reason",
            "locked_at",
            "average_rating",
            "total_products",
            "created_at",
            "updated_at",
        )

    def get_total_products(self, obj) -> int:
        return 0


class ShopUpdateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255, required=False)
    description = serializers.CharField(required=False, allow_blank=True)
    logo_url = serializers.URLField(max_length=500, required=False, allow_blank=True)
    cover_url = serializers.URLField(max_length=500, required=False, allow_blank=True)


class AdminSellerSerializer(serializers.ModelSerializer):
    seller_profile = SellerProfileSerializer(read_only=True)
    shop = ShopSerializer(read_only=True)

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "full_name",
            "phone",
            "is_active",
            "role",
            "seller_profile",
            "shop",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class TokenDataSerializer(serializers.Serializer):
    access = serializers.CharField()
    access_expires_in = serializers.IntegerField()
    user = UserSerializer()


class UserResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    message = serializers.CharField()
    data = UserSerializer()


class TokenResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    message = serializers.CharField()
    data = TokenDataSerializer()


class SessionResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    message = serializers.CharField()
    data = TokenDataSerializer(allow_null=True)


class EmptyDataResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    message = serializers.CharField()
    data = serializers.JSONField(allow_null=True)


class AddressResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    message = serializers.CharField()
    data = AddressSerializer()


class AddressListResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    message = serializers.CharField()
    data = AddressSerializer(many=True)


class AdminCustomerResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    message = serializers.CharField()
    data = AdminCustomerDetailSerializer()


class PaginationMetaSerializer(serializers.Serializer):
    page = serializers.IntegerField()
    page_size = serializers.IntegerField()
    total_items = serializers.IntegerField()
    total_pages = serializers.IntegerField()


class AdminCustomerListResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    message = serializers.CharField()
    data = AdminCustomerListSerializer(many=True)
    meta = PaginationMetaSerializer()


class AdminRoleUserListResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    message = serializers.CharField()
    data = AdminRoleUserSerializer(many=True)
    meta = PaginationMetaSerializer()


class SellerApplicationResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    message = serializers.CharField()
    data = SellerProfileSerializer(allow_null=True)


class SellerApplicationListResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    message = serializers.CharField()
    data = SellerProfileSerializer(many=True)
    meta = PaginationMetaSerializer()


class SellerDocumentResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    message = serializers.CharField()
    data = SellerDocumentSerializer()


class ShopResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    message = serializers.CharField()
    data = ShopSerializer()


class AdminSellerResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    message = serializers.CharField()
    data = AdminSellerSerializer()


class AdminSellerListResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    message = serializers.CharField()
    data = AdminSellerSerializer(many=True)
    meta = PaginationMetaSerializer()
