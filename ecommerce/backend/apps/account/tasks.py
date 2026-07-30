import logging
from urllib.parse import urlencode

from celery import shared_task
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags

from .services import AccountService
from .tokens import EmailVerificationTokenService

User = get_user_model()
logger = logging.getLogger(__name__)


def _send_html_email(subject: str, template_name: str, context: dict, recipient_list: list) -> int:
    html_message = render_to_string(template_name, context)
    plain_message = strip_tags(html_message)
    
    sent_count = send_mail(
        subject=subject,
        message=plain_message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=recipient_list,
        html_message=html_message,
    )
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
    
    sent_count = _send_html_email(
        subject="Xác thực tài khoản Multi-Vendor AI E-commerce",
        template_name="account/verification_email.html",
        context={"verification_url": verification_url, "subject": "Xác thực tài khoản"},
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
    subject = (
        "Admin yêu cầu đặt lại mật khẩu Multi-Vendor AI E-commerce"
        if admin_initiated
        else "Đặt lại mật khẩu Multi-Vendor AI E-commerce"
    )
    
    sent_count = _send_html_email(
        subject=subject,
        template_name="account/password_reset_email.html",
        context={
            "reset_url": reset_url,
            "admin_initiated": admin_initiated,
            "subject": subject,
        },
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
    subject = f"Tài khoản đã {status_text}"
    
    sent_count = _send_html_email(
        subject=subject,
        template_name="account/account_status_email.html",
        context={
            "email": user.email,
            "status_text": status_text,
            "reason": reason,
            "subject": subject,
        },
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
    subject = f"Hồ sơ seller {status_text}"
    login_url = f"{settings.FRONTEND_URL.rstrip('/')}/auth/login"
    
    sent_count = _send_html_email(
        subject=subject,
        template_name="account/seller_application_status_email.html",
        context={
            "status_text": status_text,
            "approved": approved,
            "reason": reason,
            "login_url": login_url,
            "subject": subject,
        },
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
    subject = f"Gian hàng đã {status_text}"
    
    sent_count = _send_html_email(
        subject=subject,
        template_name="account/shop_status_email.html",
        context={
            "status_text": status_text,
            "locked": locked,
            "reason": reason,
            "subject": subject,
        },
        recipient_list=[user.email],
    )
    logger.info("Shop status email accepted by email backend", extra={"user_id": user_id})
    return sent_count
