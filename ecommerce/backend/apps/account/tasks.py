import logging
from urllib.parse import urlencode

from celery import shared_task
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail

from .services import AccountService
from .tokens import EmailVerificationTokenService

User = get_user_model()
logger = logging.getLogger(__name__)


def _send_one_email(**message_options) -> int:
    sent_count = send_mail(**message_options)
    if sent_count != 1:
        raise RuntimeError("Email backend không chấp nhận thư")
    return sent_count


@shared_task(autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def send_verification_email(user_id: int) -> int:
    user = User.objects.filter(pk=user_id, is_active=True, is_email_verified=False).first()
    if user is None:
        return 0

    token = EmailVerificationTokenService.generate(user)
    query = urlencode({"token": token})
    verification_url = f"{settings.FRONTEND_URL.rstrip('/')}/auth/verify-email?{query}"
    sent_count = _send_one_email(
        subject="Xác thực tài khoản Multi-Vendor AI E-commerce",
        message=(
            "Chào bạn,\n\n"
            f"Hãy xác thực tài khoản bằng liên kết sau: {verification_url}\n\n"
            "Nếu bạn không đăng ký tài khoản, hãy bỏ qua email này."
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
    )
    logger.info("Verification email accepted by email backend", extra={"user_id": user_id})
    return sent_count


@shared_task(autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def send_password_reset_email(user_id: int, admin_initiated: bool = False) -> int:
    user = User.objects.filter(pk=user_id, is_active=True).first()
    if user is None:
        return 0

    query = urlencode(AccountService.password_reset_token_data(user))
    reset_url = f"{settings.FRONTEND_URL.rstrip('/')}/auth/reset-password?{query}"
    sent_count = _send_one_email(
        subject=(
            "Admin yêu cầu đặt lại mật khẩu Multi-Vendor AI E-commerce"
            if admin_initiated
            else "Đặt lại mật khẩu Multi-Vendor AI E-commerce"
        ),
        message=(
            "Chào bạn,\n\n"
            + (
                "Quản trị viên đã thu hồi mật khẩu hiện tại của tài khoản.\n"
                if admin_initiated
                else ""
            )
            + f"Đặt lại mật khẩu bằng liên kết sau: {reset_url}\n\n"
            + (
                "Hãy liên hệ quản trị viên nếu bạn cho rằng đây là nhầm lẫn."
                if admin_initiated
                else "Nếu bạn không yêu cầu đặt lại mật khẩu, hãy bỏ qua email này."
            )
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
    )
    logger.info("Password reset email accepted by email backend", extra={"user_id": user_id})
    return sent_count


@shared_task(autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def send_account_status_email(user_id: int, is_active: bool, reason: str) -> int:
    user = User.objects.filter(pk=user_id, is_deleted=False).first()
    if user is None:
        return 0

    status_text = "được mở khóa" if is_active else "bị khóa"
    sent_count = _send_one_email(
        subject=f"Tài khoản đã {status_text}",
        message=(
            "Chào bạn,\n\n"
            f"Tài khoản {user.email} đã {status_text}.\n"
            f"Lý do: {reason}\n\n"
            "Vui lòng liên hệ quản trị viên nếu bạn cần hỗ trợ."
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
    )
    logger.info("Account status email accepted by email backend", extra={"user_id": user_id})
    return sent_count


@shared_task(autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def send_seller_application_status_email(
    user_id: int,
    approved: bool,
    reason: str,
) -> int:
    user = User.objects.filter(pk=user_id, is_deleted=False).first()
    if user is None:
        return 0
    status_text = "đã được duyệt" if approved else "đã bị từ chối"
    detail = (
        "Bạn có thể đăng nhập lại để truy cập Seller workspace." if approved else f"Lý do: {reason}"
    )
    sent_count = _send_one_email(
        subject=f"Hồ sơ seller {status_text}",
        message=f"Chào bạn,\n\nHồ sơ seller của bạn {status_text}.\n{detail}",
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
    )
    logger.info("Seller application email accepted by email backend", extra={"user_id": user_id})
    return sent_count


@shared_task(autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def send_shop_status_email(user_id: int, locked: bool, reason: str) -> int:
    user = User.objects.filter(pk=user_id, is_deleted=False).first()
    if user is None:
        return 0
    status_text = "bị khóa" if locked else "được mở khóa"
    sent_count = _send_one_email(
        subject=f"Gian hàng đã {status_text}",
        message=(
            f"Chào bạn,\n\nGian hàng của bạn đã {status_text}.\n"
            f"Lý do/Ghi chú: {reason}\n\n"
            "Gian hàng bị khóa không thể tạo sản phẩm hoặc đơn hàng mới."
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
    )
    logger.info("Shop status email accepted by email backend", extra={"user_id": user_id})
    return sent_count
