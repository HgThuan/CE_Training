from functools import partial
from io import BytesIO
from uuid import uuid4

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.validators import validate_email
from django.db import IntegrityError, transaction
from django.utils import timezone
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from PIL import Image, ImageOps, UnidentifiedImageError
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken

from apps.common.exceptions import BusinessError
from apps.common.models import AuditLog

from .models import Address, AdminProfile, CustomerProfile, SellerProfile
from .selectors import get_user_by_email
from .tokens import AuthTokenService, EmailVerificationTokenService

User = get_user_model()


class AccountService:
    @staticmethod
    @transaction.atomic
    def register_customer(*, email: str, password: str, full_name: str = ""):
        normalized_email = User.objects.normalize_login_email(email)
        try:
            validate_email(normalized_email)
        except DjangoValidationError as exc:
            raise BusinessError(
                "Dữ liệu không hợp lệ",
                errors={"email": list(exc.messages)},
            ) from exc

        try:
            user = User.objects.create_user(
                email=normalized_email,
                password=password,
                full_name=full_name.strip(),
                role=User.Role.CUSTOMER,
                is_email_verified=False,
            )
            CustomerProfile.objects.create(user=user)
        except IntegrityError as exc:
            raise BusinessError(
                "Email đã được sử dụng",
                errors={"email": ["Hãy đăng nhập hoặc sử dụng chức năng quên mật khẩu"]},
            ) from exc

        from .tasks import send_verification_email

        transaction.on_commit(partial(send_verification_email.delay, user.pk))
        return user

    @staticmethod
    def authenticate(*, email: str, password: str):
        user = get_user_by_email(email)
        if user is None or not user.check_password(password):
            raise BusinessError(
                "Email hoặc mật khẩu không chính xác",
                errors={"credentials": ["Thông tin đăng nhập không hợp lệ"]},
                http_status=401,
            )
        if not user.is_active:
            raise BusinessError(
                "Tài khoản đã bị khóa",
                errors={"account": ["Vui lòng liên hệ quản trị viên"]},
                http_status=403,
            )
        if not user.is_email_verified:
            raise BusinessError(
                "Email chưa được xác thực",
                errors={"email": ["Vui lòng kiểm tra email hoặc yêu cầu gửi lại liên kết"]},
                http_status=403,
            )
        return user, AuthTokenService.issue_pair(user)

    @staticmethod
    @transaction.atomic
    def verify_email(*, token: str):
        resolved_user = EmailVerificationTokenService.resolve(token)
        user = User.objects.select_for_update().get(pk=resolved_user.pk)
        if not user.is_active:
            raise BusinessError("Tài khoản đã bị khóa", http_status=403)
        if not user.is_email_verified:
            user.is_email_verified = True
            user.save(update_fields=["is_email_verified", "updated_at"])
        return user

    @staticmethod
    def resend_verification(*, email: str) -> None:
        user = get_user_by_email(email)
        if user is None or user.is_email_verified or not user.is_active:
            return

        from .tasks import send_verification_email

        send_verification_email.delay(user.pk)

    @staticmethod
    def request_password_reset(*, email: str) -> None:
        user = get_user_by_email(email)
        if user is None or not user.is_active or not user.has_usable_password():
            return

        from .tasks import send_password_reset_email

        send_password_reset_email.delay(user.pk)

    @staticmethod
    @transaction.atomic
    def reset_password(*, uid: str, token: str, new_password: str):
        try:
            user_id = force_str(urlsafe_base64_decode(uid))
            user = User.objects.select_for_update().get(pk=user_id)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist) as exc:
            raise BusinessError(
                "Liên kết đặt lại mật khẩu không hợp lệ",
                errors={"token": ["Token không hợp lệ hoặc đã hết hạn"]},
            ) from exc

        if not user.is_active or not default_token_generator.check_token(user, token):
            raise BusinessError(
                "Liên kết đặt lại mật khẩu không hợp lệ",
                errors={"token": ["Token không hợp lệ hoặc đã hết hạn"]},
            )

        user.set_password(new_password)
        user.must_change_password = False
        user.save(update_fields=["password", "must_change_password", "updated_at"])
        AccountService.invalidate_all_sessions(user=user)
        return user

    @staticmethod
    @transaction.atomic
    def change_password(*, user, old_password: str, new_password: str):
        locked_user = User.objects.select_for_update().get(pk=user.pk)
        if not locked_user.check_password(old_password):
            raise BusinessError(
                "Mật khẩu hiện tại không chính xác",
                errors={"old_password": ["Mật khẩu hiện tại không đúng"]},
            )
        locked_user.set_password(new_password)
        locked_user.must_change_password = False
        locked_user.save(update_fields=["password", "must_change_password", "updated_at"])
        AccountService.invalidate_all_sessions(user=locked_user)
        return locked_user

    @staticmethod
    @transaction.atomic
    def update_avatar(*, user, uploaded_file):
        """Validate and re-encode an avatar so uploaded metadata/content is never trusted."""
        try:
            uploaded_file.seek(0)
            with Image.open(uploaded_file) as candidate:
                candidate.verify()
            uploaded_file.seek(0)
            with Image.open(uploaded_file) as source:
                if source.width * source.height > 25_000_000:
                    raise BusinessError(
                        "Ảnh đại diện có độ phân giải quá lớn",
                        errors={"avatar": ["Ảnh không được vượt quá 25 triệu điểm ảnh"]},
                    )
                image = ImageOps.exif_transpose(source)
                image.thumbnail((512, 512), Image.Resampling.LANCZOS)
                if image.mode != "RGB":
                    background = Image.new("RGB", image.size, "white")
                    if "A" in image.getbands():
                        background.paste(image, mask=image.getchannel("A"))
                    else:
                        background.paste(image)
                    image = background

                output = BytesIO()
                image.save(output, format="JPEG", quality=88, optimize=True)
        except (UnidentifiedImageError, OSError, ValueError) as exc:
            raise BusinessError(
                "Tệp ảnh đại diện không hợp lệ",
                errors={"avatar": ["Nội dung tệp không phải ảnh JPEG, PNG hoặc WebP hợp lệ"]},
            ) from exc

        storage_path = f"avatars/{user.pk}/{uuid4().hex}.jpg"
        saved_path = default_storage.save(storage_path, ContentFile(output.getvalue()))
        locked_user = User.objects.select_for_update().get(pk=user.pk)
        locked_user.avatar_url = f"{settings.MEDIA_URL.rstrip('/')}/{saved_path}"
        locked_user.save(update_fields=["avatar_url", "updated_at"])
        return locked_user

    @staticmethod
    def invalidate_all_sessions(*, user) -> None:
        user.token_version += 1
        user.save(update_fields=["token_version", "updated_at"])
        tokens = OutstandingToken.objects.filter(user=user).exclude(blacklistedtoken__isnull=False)
        BlacklistedToken.objects.bulk_create(
            [BlacklistedToken(token=token) for token in tokens],
            ignore_conflicts=True,
        )

    @staticmethod
    @transaction.atomic
    def assign_role(*, actor, target_user_id: int, role: str):
        target = User.objects.select_for_update().filter(pk=target_user_id).first()
        if target is None:
            raise BusinessError("Không tìm thấy người dùng", http_status=404)
        if target.pk == actor.pk:
            raise BusinessError(
                "Không thể tự thay đổi vai trò của chính mình",
                errors={"role": ["Hãy nhờ một Admin khác thực hiện"]},
            )
        if target.is_superuser:
            raise BusinessError(
                "Không thể thay đổi vai trò của Superuser",
                errors={"role": ["Tài khoản hệ thống được bảo vệ"]},
            )

        old_role = target.role
        if old_role == role:
            return target

        target.role = role
        target.is_staff = role == User.Role.ADMIN
        target.save(update_fields=["role", "is_staff", "updated_at"])
        AccountService.ensure_role_profile(user=target)
        AccountService.invalidate_all_sessions(user=target)
        AuditLog.objects.create(
            actor=actor,
            action="assign_role",
            target_type="User",
            target_id=target.pk,
            diff={"role": {"before": old_role, "after": role}},
        )
        return target

    @staticmethod
    @transaction.atomic
    def create_address(*, user, address_data: dict):
        User.objects.select_for_update().get(pk=user.pk)
        active_addresses = Address.objects.select_for_update().filter(
            user=user,
            is_deleted=False,
        )
        has_address = active_addresses.exists()
        make_default = address_data.pop("is_default", False) or not has_address
        if make_default:
            active_addresses.filter(is_default=True).update(is_default=False)
        return Address.objects.create(user=user, is_default=make_default, **address_data)

    @staticmethod
    @transaction.atomic
    def update_address(*, user, address_id: int, address_data: dict):
        User.objects.select_for_update().get(pk=user.pk)
        address = (
            Address.objects.select_for_update()
            .filter(pk=address_id, user=user, is_deleted=False)
            .first()
        )
        if address is None:
            raise BusinessError("Không tìm thấy địa chỉ", http_status=404)

        make_default = address_data.pop("is_default", None)
        if make_default is True:
            Address.objects.select_for_update().filter(
                user=user,
                is_deleted=False,
                is_default=True,
            ).exclude(pk=address.pk).update(is_default=False)

        for field, value in address_data.items():
            setattr(address, field, value)
        if make_default is not None:
            address.is_default = make_default
        address.save()
        return address

    @staticmethod
    @transaction.atomic
    def delete_address(*, user, address_id: int) -> None:
        User.objects.select_for_update().get(pk=user.pk)
        addresses = Address.objects.select_for_update().filter(user=user, is_deleted=False)
        address = addresses.filter(pk=address_id).first()
        if address is None:
            raise BusinessError("Không tìm thấy địa chỉ", http_status=404)

        was_default = address.is_default
        address.is_default = False
        address.is_deleted = True
        address.deleted_at = timezone.now()
        address.save(update_fields=["is_default", "is_deleted", "deleted_at", "updated_at"])

        if was_default:
            replacement = addresses.exclude(pk=address.pk).order_by("-updated_at").first()
            if replacement is not None:
                replacement.is_default = True
                replacement.save(update_fields=["is_default", "updated_at"])

    @staticmethod
    @transaction.atomic
    def set_default_address(*, user, address_id: int):
        User.objects.select_for_update().get(pk=user.pk)
        addresses = Address.objects.select_for_update().filter(user=user, is_deleted=False)
        address = addresses.filter(pk=address_id).first()
        if address is None:
            raise BusinessError("Không tìm thấy địa chỉ", http_status=404)
        if address.is_default:
            return address

        addresses.filter(is_default=True).update(is_default=False)
        address.is_default = True
        address.save(update_fields=["is_default", "updated_at"])
        return address

    @staticmethod
    @transaction.atomic
    def create_customer_by_admin(
        *,
        actor,
        email: str,
        password: str,
        full_name: str = "",
        phone: str = "",
        date_of_birth=None,
        gender: str = "",
        is_email_verified: bool = False,
    ):
        normalized_email = User.objects.normalize_login_email(email)
        try:
            validate_email(normalized_email)
        except DjangoValidationError as exc:
            raise BusinessError(
                "Dữ liệu không hợp lệ",
                errors={"email": list(exc.messages)},
            ) from exc

        try:
            user = User.objects.create_user(
                email=normalized_email,
                password=password,
                full_name=full_name.strip(),
                phone=phone,
                date_of_birth=date_of_birth,
                gender=gender,
                role=User.Role.CUSTOMER,
                is_email_verified=is_email_verified,
            )
            CustomerProfile.objects.create(user=user)
        except IntegrityError as exc:
            raise BusinessError(
                "Email đã được sử dụng",
                errors={"email": ["Vui lòng chọn email khác"]},
            ) from exc

        AuditLog.objects.create(
            actor=actor,
            action="create_customer",
            target_type="User",
            target_id=user.pk,
            diff={"email": {"before": None, "after": user.email}},
        )
        if not user.is_email_verified:
            from .tasks import send_verification_email

            transaction.on_commit(partial(send_verification_email.delay, user.pk))
        return user

    @staticmethod
    @transaction.atomic
    def update_customer_by_admin(*, actor, target_user_id: int, customer_data: dict):
        target = (
            User.objects.select_for_update()
            .filter(
                pk=target_user_id,
                role=User.Role.CUSTOMER,
                is_deleted=False,
            )
            .first()
        )
        if target is None:
            raise BusinessError("Không tìm thấy khách hàng", http_status=404)

        changes = dict(customer_data)
        if "email" in changes:
            normalized_email = User.objects.normalize_login_email(changes["email"])
            if User.objects.filter(email__iexact=normalized_email).exclude(pk=target.pk).exists():
                raise BusinessError(
                    "Email đã được sử dụng",
                    errors={"email": ["Vui lòng chọn email khác"]},
                )
            changes["email"] = normalized_email
            if normalized_email != target.email and "is_email_verified" not in changes:
                changes["is_email_verified"] = False

        diff = {}
        changed_fields = []
        for field, value in changes.items():
            previous = getattr(target, field)
            if previous != value:
                setattr(target, field, value)
                changed_fields.append(field)
                diff[field] = {
                    "before": previous.isoformat() if hasattr(previous, "isoformat") else previous,
                    "after": value.isoformat() if hasattr(value, "isoformat") else value,
                }

        if not changed_fields:
            return target

        try:
            target.save(update_fields=[*changed_fields, "updated_at"])
        except IntegrityError as exc:
            raise BusinessError(
                "Email đã được sử dụng",
                errors={"email": ["Vui lòng chọn email khác"]},
            ) from exc

        AuditLog.objects.create(
            actor=actor,
            action="update_customer",
            target_type="User",
            target_id=target.pk,
            diff=diff,
        )
        if "email" in changed_fields and not target.is_email_verified:
            from .tasks import send_verification_email

            transaction.on_commit(partial(send_verification_email.delay, target.pk))
        return target

    @staticmethod
    @transaction.atomic
    def delete_customer_by_admin(*, actor, target_user_id: int) -> None:
        target = (
            User.objects.select_for_update()
            .filter(
                pk=target_user_id,
                role=User.Role.CUSTOMER,
                is_deleted=False,
            )
            .first()
        )
        if target is None:
            raise BusinessError("Không tìm thấy khách hàng", http_status=404)

        target.is_active = False
        target.is_deleted = True
        target.deleted_at = timezone.now()
        target.save(
            update_fields=["is_active", "is_deleted", "deleted_at", "updated_at"],
        )
        AccountService.invalidate_all_sessions(user=target)
        AuditLog.objects.create(
            actor=actor,
            action="delete_customer",
            target_type="User",
            target_id=target.pk,
            diff={"is_deleted": {"before": False, "after": True}},
        )

    @staticmethod
    def _get_protected_admin_target(*, actor, target_user_id: int):
        target = (
            User.objects.select_for_update().filter(pk=target_user_id, is_deleted=False).first()
        )
        if target is None:
            raise BusinessError("Không tìm thấy người dùng", http_status=404)
        if target.pk == actor.pk:
            raise BusinessError(
                "Không thể thực hiện thao tác này với chính mình",
                errors={"user": ["Hãy nhờ một Admin khác thực hiện"]},
            )
        if target.is_superuser:
            raise BusinessError(
                "Không thể thay đổi tài khoản Superuser",
                errors={"user": ["Tài khoản hệ thống được bảo vệ"]},
            )
        return target

    @staticmethod
    @transaction.atomic
    def set_account_active(
        *,
        actor,
        target_user_id: int,
        is_active: bool,
        reason: str,
    ):
        target = AccountService._get_protected_admin_target(
            actor=actor,
            target_user_id=target_user_id,
        )
        normalized_reason = reason.strip()
        if target.is_active == is_active:
            return target

        previous = target.is_active
        target.is_active = is_active
        target.lock_reason = "" if is_active else normalized_reason
        target.locked_at = None if is_active else timezone.now()
        target.save(
            update_fields=["is_active", "lock_reason", "locked_at", "updated_at"],
        )
        AccountService.invalidate_all_sessions(user=target)
        AuditLog.objects.create(
            actor=actor,
            action="unlock_user" if is_active else "lock_user",
            target_type="User",
            target_id=target.pk,
            diff={
                "is_active": {"before": previous, "after": is_active},
                "reason": normalized_reason,
            },
        )

        from .tasks import send_account_status_email

        transaction.on_commit(
            partial(
                send_account_status_email.delay,
                target.pk,
                is_active,
                normalized_reason,
            ),
        )
        return target

    @staticmethod
    @transaction.atomic
    def admin_reset_password(*, actor, target_user_id: int, reason: str = ""):
        target = AccountService._get_protected_admin_target(
            actor=actor,
            target_user_id=target_user_id,
        )
        if not target.is_active:
            raise BusinessError(
                "Không thể reset mật khẩu cho tài khoản đang bị khóa",
                errors={"user": ["Hãy mở khóa tài khoản trước"]},
            )

        target.set_unusable_password()
        target.must_change_password = True
        target.save(update_fields=["password", "must_change_password", "updated_at"])
        AccountService.invalidate_all_sessions(user=target)
        AuditLog.objects.create(
            actor=actor,
            action="admin_reset_password",
            target_type="User",
            target_id=target.pk,
            diff={"reason": reason.strip(), "sessions_revoked": True},
        )

        from .tasks import send_password_reset_email

        transaction.on_commit(partial(send_password_reset_email.delay, target.pk, True))
        return target

    @staticmethod
    def ensure_role_profile(*, user) -> None:
        profile_by_role = {
            User.Role.CUSTOMER: CustomerProfile,
            User.Role.SELLER: SellerProfile,
            User.Role.ADMIN: AdminProfile,
        }
        profile_by_role[user.role].objects.get_or_create(user=user)

    @staticmethod
    def password_reset_token_data(user) -> dict[str, str]:
        return {
            "uid": urlsafe_base64_encode(force_bytes(user.pk)),
            "token": default_token_generator.make_token(user),
        }
