from urllib.parse import urlencode

from celery import shared_task
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail

from .services import AccountService
from .tokens import EmailVerificationTokenService

User = get_user_model()


@shared_task(autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def send_verification_email(user_id: int) -> None:
    user = User.objects.filter(pk=user_id, is_active=True, is_email_verified=False).first()
    if user is None:
        return

    token = EmailVerificationTokenService.generate(user)
    query = urlencode({"token": token})
    verification_url = f"{settings.FRONTEND_URL.rstrip('/')}/auth/verify-email?{query}"
    send_mail(
        subject="Xác thực tài khoản Multi-Vendor AI E-commerce",
        message=(
            "Chào bạn,\n\n"
            f"Hãy xác thực tài khoản bằng liên kết sau: {verification_url}\n\n"
            "Nếu bạn không đăng ký tài khoản, hãy bỏ qua email này."
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
    )


@shared_task(autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def send_password_reset_email(user_id: int, admin_initiated: bool = False) -> None:
    user = User.objects.filter(pk=user_id, is_active=True).first()
    if user is None:
        return

    query = urlencode(AccountService.password_reset_token_data(user))
    reset_url = f"{settings.FRONTEND_URL.rstrip('/')}/auth/reset-password?{query}"
    send_mail(
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


@shared_task(autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def send_account_status_email(user_id: int, is_active: bool, reason: str) -> None:
    user = User.objects.filter(pk=user_id, is_deleted=False).first()
    if user is None:
        return

    status_text = "được mở khóa" if is_active else "bị khóa"
    send_mail(
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
