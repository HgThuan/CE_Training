import logging
from functools import partial
from io import BytesIO
from pathlib import Path
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
from django.utils.text import slugify
from PIL import Image, ImageOps, UnidentifiedImageError
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken

from apps.common.exceptions import BusinessError
from apps.common.models import AuditLog

from .constants import SHOP_IMAGE_SIZES
from .models import (
    Address,
    AdminProfile,
    CustomerProfile,
    Notification,
    SellerDocument,
    SellerProfile,
    Shop,
)
from .selectors import get_user_by_email
from .tokens import AuthTokenService, EmailVerificationTokenService

User = get_user_model()
logger = logging.getLogger(__name__)


class AccountService:
    @staticmethod
    def _release_deleted_email(user) -> None:
        """Keep the deleted row for history while freeing its login email."""
        user.email = f"deleted-{user.pk}-{uuid4().hex}@deleted.invalid"
        user.save(update_fields=["email", "updated_at"])

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

        existing_user = (
            User.objects.select_for_update().filter(email__iexact=normalized_email).first()
        )
        if existing_user is not None:
            if not existing_user.is_deleted:
                raise BusinessError(
                    "Email đã được sử dụng",
                    errors={"email": ["Hãy đăng nhập hoặc sử dụng chức năng quên mật khẩu"]},
                )
            AccountService._release_deleted_email(existing_user)

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
    def assign_role(*, actor, target_user_id: int, role: str, request_id: str = ""):
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
        if role == User.Role.SELLER:
            profile = SellerProfile.objects.select_for_update().get(user=target)
            if profile.onboarding_status != SellerProfile.OnboardingStatus.APPROVED:
                profile.business_name = profile.business_name or target.full_name or target.email
                profile.onboarding_status = SellerProfile.OnboardingStatus.APPROVED
                profile.rejection_reason = ""
                profile.reviewed_by = actor
                profile.reviewed_at = timezone.now()
                profile.save()
            SellerOnboardingService._create_shop(profile=profile)
        if old_role == User.Role.SELLER and role != User.Role.SELLER:
            Shop.objects.filter(owner=target, is_deleted=False).update(
                status=Shop.Status.LOCKED,
                lock_reason="Vai trò Seller đã bị thu hồi",
                locked_at=timezone.now(),
                updated_at=timezone.now(),
            )
        AccountService.invalidate_all_sessions(user=target)
        AuditLog.objects.create(
            actor=actor,
            action="assign_role",
            target_type="User",
            target_id=target.pk,
            reason="Thay đổi vai trò người dùng",
            request_id=request_id,
            diff={"role": {"before": old_role, "after": role}},
        )
        logger.info(
            "Admin changed user role",
            extra={
                "request_id": request_id,
                "user_id": actor.pk,
                "target_user_id": target.pk,
                "old_role": old_role,
                "new_role": role,
            },
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
        AccountService._release_deleted_email(target)
        target.save(
            update_fields=["is_active", "is_deleted", "deleted_at", "updated_at"],
        )
        AccountService.invalidate_all_sessions(user=target)
        AuditLog.objects.create(
            actor=actor,
            action="delete_customer",
            target_type="User",
            target_id=target.pk,
            diff={
                "is_deleted": {"before": False, "after": True},
                "email_released_for_registration": True,
            },
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
        request_id: str = "",
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
            reason=normalized_reason,
            request_id=request_id,
            diff={
                "is_active": {"before": previous, "after": is_active},
                "reason": normalized_reason,
            },
        )
        logger.info(
            "Admin changed account status",
            extra={
                "request_id": request_id,
                "user_id": actor.pk,
                "target_user_id": target.pk,
                "is_active": is_active,
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
    def admin_reset_password(
        *,
        actor,
        target_user_id: int,
        reason: str = "",
        request_id: str = "",
    ):
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
            reason=reason.strip(),
            request_id=request_id,
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


class SellerOnboardingService:
    @staticmethod
    @transaction.atomic
    def submit_application(*, user, application_data: dict):
        locked_user = User.objects.select_for_update().get(pk=user.pk, is_deleted=False)
        profile, _ = SellerProfile.objects.select_for_update().get_or_create(user=locked_user)
        if profile.onboarding_status == SellerProfile.OnboardingStatus.APPROVED:
            raise BusinessError(
                "Hồ sơ seller đã được duyệt",
                errors={"application": ["Không thể nộp lại hồ sơ đã được duyệt"]},
            )
        if (
            profile.onboarding_status == SellerProfile.OnboardingStatus.PENDING
            and profile.submitted_at
        ):
            raise BusinessError(
                "Hồ sơ đang chờ duyệt",
                errors={"application": ["Vui lòng chờ Admin xử lý hồ sơ hiện tại"]},
            )

        for field, value in application_data.items():
            setattr(profile, field, value)
        profile.onboarding_status = SellerProfile.OnboardingStatus.PENDING
        profile.rejection_reason = ""
        profile.submitted_at = timezone.now()
        profile.reviewed_at = None
        profile.reviewed_by = None
        profile.is_deleted = False
        profile.deleted_at = None
        profile.save()
        return profile

    @staticmethod
    @transaction.atomic
    def add_document(*, user, document_type: str, uploaded_file):
        profile = (
            SellerProfile.objects.select_for_update().filter(user=user, is_deleted=False).first()
        )
        if profile is None or not profile.submitted_at:
            raise BusinessError(
                "Chưa có hồ sơ seller",
                errors={"application": ["Hãy hoàn tất bước thông tin trước khi tải giấy tờ"]},
            )
        if profile.onboarding_status == SellerProfile.OnboardingStatus.APPROVED:
            raise BusinessError(
                "Hồ sơ seller đã được duyệt",
                errors={"document": ["Không thể thay đổi giấy tờ onboarding"]},
            )

        previous_documents = SellerDocument.objects.select_for_update().filter(
            seller_profile=profile,
            document_type=document_type,
            is_deleted=False,
        )
        now = timezone.now()
        previous_documents.update(is_deleted=True, deleted_at=now, updated_at=now)
        document = SellerDocument.objects.create(
            seller_profile=profile,
            document_type=document_type,
            file=uploaded_file,
            original_name=Path(uploaded_file.name).name,
        )
        profile.verification_status = SellerProfile.VerificationStatus.PENDING
        profile.save(update_fields=["verification_status", "updated_at"])
        return document

    @staticmethod
    @transaction.atomic
    def review_application(
        *,
        actor,
        profile_id: int,
        approved: bool,
        reason: str = "",
        request_id: str = "",
    ):
        profile = (
            SellerProfile.objects.select_for_update()
            .select_related("user")
            .filter(pk=profile_id, is_deleted=False)
            .first()
        )
        if profile is None:
            raise BusinessError("Không tìm thấy hồ sơ seller", http_status=404)
        if profile.onboarding_status != SellerProfile.OnboardingStatus.PENDING:
            raise BusinessError(
                "Hồ sơ không còn ở trạng thái chờ duyệt",
                errors={"status": [profile.get_onboarding_status_display()]},
            )

        normalized_reason = reason.strip()
        if not approved and not normalized_reason:
            raise BusinessError(
                "Lý do từ chối là bắt buộc",
                errors={"reason": ["Vui lòng nhập lý do từ chối"]},
            )
        if (
            approved
            and not SellerDocument.objects.filter(
                seller_profile=profile,
                is_deleted=False,
            ).exists()
        ):
            raise BusinessError(
                "Hồ sơ chưa có giấy tờ",
                errors={"documents": ["Cần ít nhất một giấy tờ trước khi duyệt"]},
            )

        previous_status = profile.onboarding_status
        profile.onboarding_status = (
            SellerProfile.OnboardingStatus.APPROVED
            if approved
            else SellerProfile.OnboardingStatus.REJECTED
        )
        profile.rejection_reason = "" if approved else normalized_reason
        profile.reviewed_by = actor
        profile.reviewed_at = timezone.now()
        profile.save(
            update_fields=[
                "onboarding_status",
                "rejection_reason",
                "reviewed_by",
                "reviewed_at",
                "updated_at",
            ],
        )

        shop = None
        if approved:
            shop = SellerOnboardingService._create_shop(profile=profile)
            profile.user.role = User.Role.SELLER
            profile.user.is_staff = False
            profile.user.save(update_fields=["role", "is_staff", "updated_at"])
            AccountService.invalidate_all_sessions(user=profile.user)

        action = "approve_seller" if approved else "reject_seller"
        title = "Hồ sơ seller đã được duyệt" if approved else "Hồ sơ seller bị từ chối"
        message = f"Gian hàng {shop.name} đã sẵn sàng." if shop else f"Lý do: {normalized_reason}"
        Notification.objects.create(
            user=profile.user,
            kind=Notification.Kind.SELLER_APPLICATION,
            title=title,
            message=message,
            metadata={"seller_profile_id": profile.pk, "shop_id": shop.pk if shop else None},
        )
        AuditLog.objects.create(
            actor=actor,
            action=action,
            target_type="SellerProfile",
            target_id=profile.pk,
            reason=normalized_reason,
            request_id=request_id,
            diff={
                "onboarding_status": {
                    "before": previous_status,
                    "after": profile.onboarding_status,
                },
                "shop_id": shop.pk if shop else None,
            },
        )
        logger.info(
            "Admin reviewed seller application",
            extra={
                "request_id": request_id,
                "user_id": actor.pk,
                "target_user_id": profile.user_id,
                "approved": approved,
            },
        )

        from .tasks import send_seller_application_status_email

        transaction.on_commit(
            partial(
                send_seller_application_status_email.delay,
                profile.user_id,
                approved,
                normalized_reason,
            ),
        )
        return profile

    @staticmethod
    def _create_shop(*, profile: SellerProfile):
        existing_shop = Shop.objects.select_for_update().filter(owner=profile.user).first()
        if existing_shop:
            if existing_shop.is_deleted:
                existing_shop.is_deleted = False
                existing_shop.deleted_at = None
                existing_shop.status = Shop.Status.APPROVED
                existing_shop.lock_reason = ""
                existing_shop.locked_at = None
                existing_shop.save()
            return existing_shop

        base_slug = slugify(profile.business_name) or f"shop-{profile.user_id}"
        slug = base_slug
        suffix = 2
        while Shop.objects.filter(slug=slug).exists():
            slug = f"{base_slug}-{suffix}"
            suffix += 1
        return Shop.objects.create(
            owner=profile.user,
            name=profile.business_name,
            slug=slug,
            description="",
            status=Shop.Status.APPROVED,
        )


class SellerDocumentService:
    @staticmethod
    @transaction.atomic
    def review_document(
        *,
        actor,
        document_id: int,
        review_status: str,
        reason: str = "",
        request_id: str = "",
    ):
        document = (
            SellerDocument.objects.select_for_update()
            .select_related("seller_profile__user")
            .filter(pk=document_id, is_deleted=False)
            .first()
        )
        if document is None:
            raise BusinessError("Không tìm thấy giấy tờ seller", http_status=404)
        normalized_reason = reason.strip()
        if (
            review_status == SellerDocument.ReviewStatus.ADDITIONAL_REQUIRED
            and not normalized_reason
        ):
            raise BusinessError(
                "Lý do yêu cầu bổ sung là bắt buộc",
                errors={"reason": ["Vui lòng mô tả giấy tờ cần bổ sung"]},
            )

        previous_status = document.review_status
        document.review_status = review_status
        document.review_reason = normalized_reason
        document.reviewed_by = actor
        document.reviewed_at = timezone.now()
        document.save(
            update_fields=[
                "review_status",
                "review_reason",
                "reviewed_by",
                "reviewed_at",
                "updated_at",
            ],
        )
        profile = document.seller_profile
        active_documents = SellerDocument.objects.filter(
            seller_profile=profile,
            is_deleted=False,
        )
        if active_documents.filter(
            review_status=SellerDocument.ReviewStatus.ADDITIONAL_REQUIRED
        ).exists():
            profile.verification_status = SellerProfile.VerificationStatus.UNVERIFIED
        elif (
            active_documents.exists()
            and not active_documents.exclude(
                review_status=SellerDocument.ReviewStatus.VERIFIED
            ).exists()
        ):
            profile.verification_status = SellerProfile.VerificationStatus.VERIFIED
        else:
            profile.verification_status = SellerProfile.VerificationStatus.PENDING
        profile.save(update_fields=["verification_status", "updated_at"])

        Notification.objects.create(
            user=profile.user,
            kind=Notification.Kind.DOCUMENT_REVIEW,
            title="Cập nhật xác minh giấy tờ",
            message=normalized_reason or document.get_review_status_display(),
            metadata={"document_id": document.pk, "review_status": review_status},
        )
        AuditLog.objects.create(
            actor=actor,
            action="review_seller_document",
            target_type="SellerDocument",
            target_id=document.pk,
            reason=normalized_reason,
            request_id=request_id,
            diff={"review_status": {"before": previous_status, "after": review_status}},
        )
        return document


class ShopBusinessPolicy:
    @staticmethod
    def can_create_new_resource(*, shop: Shop) -> bool:
        return not shop.is_deleted and shop.status == Shop.Status.APPROVED

    @staticmethod
    def ensure_can_create_new_resource(*, shop: Shop) -> None:
        if not ShopBusinessPolicy.can_create_new_resource(shop=shop):
            raise BusinessError(
                "Gian hàng đang bị khóa",
                errors={"shop": ["Không thể tạo sản phẩm hoặc đơn hàng mới"]},
                http_status=403,
            )


class ShopService:
    @staticmethod
    @transaction.atomic
    def update_shop_image(*, user, image_type: str, uploaded_file):
        target_size = SHOP_IMAGE_SIZES.get(image_type)
        if target_size is None:
            raise BusinessError(
                "Loại ảnh gian hàng không hợp lệ",
                errors={"image_type": ["Chỉ chấp nhận logo hoặc cover"]},
            )
        shop = Shop.objects.select_for_update().filter(owner=user, is_deleted=False).first()
        if shop is None:
            raise BusinessError("Không tìm thấy gian hàng", http_status=404)

        try:
            uploaded_file.seek(0)
            with Image.open(uploaded_file) as candidate:
                candidate.verify()
            uploaded_file.seek(0)
            with Image.open(uploaded_file) as source:
                if source.width * source.height > 40_000_000:
                    raise BusinessError(
                        "Ảnh gian hàng có độ phân giải quá lớn",
                        errors={"image": ["Ảnh không được vượt quá 40 triệu điểm ảnh"]},
                    )
                normalized = ImageOps.exif_transpose(source).convert("RGB")
                normalized = ImageOps.fit(
                    normalized,
                    target_size,
                    method=Image.Resampling.LANCZOS,
                    centering=(0.5, 0.5),
                )
                output = BytesIO()
                normalized.save(output, format="WEBP", quality=88, method=6)
        except (UnidentifiedImageError, OSError, ValueError) as exc:
            raise BusinessError(
                "Tệp ảnh gian hàng không hợp lệ",
                errors={"image": ["Nội dung tệp không phải JPEG, PNG hoặc WebP hợp lệ"]},
            ) from exc

        image_field = getattr(shop, image_type)
        previous_name = image_field.name
        image_field.save(f"{uuid4().hex}.webp", ContentFile(output.getvalue()), save=False)
        shop.save(update_fields=[image_type, "updated_at"])
        if previous_name:
            transaction.on_commit(partial(default_storage.delete, previous_name))
        return shop

    @staticmethod
    @transaction.atomic
    def update_own_shop(*, user, shop_data: dict):
        shop = Shop.objects.select_for_update().filter(owner=user, is_deleted=False).first()
        if shop is None:
            raise BusinessError("Không tìm thấy gian hàng", http_status=404)
        for field, value in shop_data.items():
            setattr(shop, field, value)
        shop.save()
        return shop

    @staticmethod
    @transaction.atomic
    def update_shop_by_admin(*, actor, shop_id: int, shop_data: dict, request_id: str = ""):
        shop = Shop.objects.select_for_update().filter(pk=shop_id, is_deleted=False).first()
        if shop is None:
            raise BusinessError("Không tìm thấy gian hàng", http_status=404)
        diff = {}
        for field, value in shop_data.items():
            previous = getattr(shop, field)
            if previous != value:
                setattr(shop, field, value)
                diff[field] = {"before": previous, "after": value}
        if diff:
            shop.save()
            AuditLog.objects.create(
                actor=actor,
                action="update_shop",
                target_type="Shop",
                target_id=shop.pk,
                request_id=request_id,
                diff=diff,
            )
        return shop

    @staticmethod
    @transaction.atomic
    def set_shop_locked(
        *,
        actor,
        shop_id: int,
        locked: bool,
        reason: str,
        request_id: str = "",
    ):
        shop = (
            Shop.objects.select_for_update()
            .select_related("owner")
            .filter(pk=shop_id, is_deleted=False)
            .first()
        )
        if shop is None:
            raise BusinessError("Không tìm thấy gian hàng", http_status=404)
        normalized_reason = reason.strip()
        target_status = Shop.Status.LOCKED if locked else Shop.Status.APPROVED
        if shop.status == target_status:
            return shop

        previous_status = shop.status
        shop.status = target_status
        shop.lock_reason = normalized_reason if locked else ""
        shop.locked_at = timezone.now() if locked else None
        shop.save(update_fields=["status", "lock_reason", "locked_at", "updated_at"])
        Notification.objects.create(
            user=shop.owner,
            kind=Notification.Kind.SHOP_STATUS,
            title="Gian hàng bị khóa" if locked else "Gian hàng đã được mở khóa",
            message=normalized_reason,
            metadata={"shop_id": shop.pk, "status": target_status},
        )
        AuditLog.objects.create(
            actor=actor,
            action="lock_shop" if locked else "unlock_shop",
            target_type="Shop",
            target_id=shop.pk,
            reason=normalized_reason,
            request_id=request_id,
            diff={"status": {"before": previous_status, "after": target_status}},
        )
        logger.info(
            "Admin changed shop status",
            extra={
                "request_id": request_id,
                "user_id": actor.pk,
                "shop_id": shop.pk,
                "locked": locked,
            },
        )

        from .tasks import send_shop_status_email

        transaction.on_commit(
            partial(send_shop_status_email.delay, shop.owner_id, locked, normalized_reason),
        )
        return shop

    @staticmethod
    @transaction.atomic
    def soft_delete_seller(*, actor, target_user_id: int, reason: str, request_id: str = ""):
        target = (
            User.objects.select_for_update()
            .filter(pk=target_user_id, role=User.Role.SELLER, is_deleted=False)
            .first()
        )
        if target is None:
            raise BusinessError("Không tìm thấy seller", http_status=404)
        now = timezone.now()
        Shop.objects.select_for_update().filter(owner=target, is_deleted=False).update(
            is_deleted=True,
            deleted_at=now,
            status=Shop.Status.LOCKED,
            lock_reason=reason.strip(),
            locked_at=now,
            updated_at=now,
        )
        SellerProfile.objects.select_for_update().filter(user=target, is_deleted=False).update(
            is_deleted=True,
            deleted_at=now,
            updated_at=now,
        )
        target.is_active = False
        target.is_deleted = True
        target.deleted_at = now
        AccountService._release_deleted_email(target)
        target.save(update_fields=["is_active", "is_deleted", "deleted_at", "updated_at"])
        AccountService.invalidate_all_sessions(user=target)
        AuditLog.objects.create(
            actor=actor,
            action="delete_seller",
            target_type="User",
            target_id=target.pk,
            reason=reason.strip(),
            request_id=request_id,
            diff={"is_deleted": {"before": False, "after": True}},
        )
