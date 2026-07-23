from datetime import date

from django.conf import settings
from rest_framework import serializers

from .models import Address, AdminProfile, CustomerProfile, SellerProfile, User
from .validators import validate_matching_passwords, validate_new_password


class CustomerProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomerProfile
        fields = ("loyalty_points", "wallet_balance")
        read_only_fields = fields


class SellerProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = SellerProfile
        fields = (
            "onboarding_status",
            "rejection_reason",
            "id_card_document_url",
            "business_license_url",
            "verification_status",
        )
        read_only_fields = fields


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
    date_of_birth = serializers.DateField(required=False, allow_null=True)
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
    date_of_birth = serializers.DateField(required=False, allow_null=True)
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
