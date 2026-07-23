from django.conf import settings
from django.contrib.auth.models import update_last_login
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from rest_framework import filters, generics
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from apps.common.exceptions import BusinessError
from apps.common.responses import success_response

from .models import Address, User
from .permissions import IsAdmin, IsCustomer
from .selectors import get_customer_for_admin, get_user_for_profile
from .serializers import (
    AccountStatusSerializer,
    AddressListResponseSerializer,
    AddressResponseSerializer,
    AddressSerializer,
    AdminCustomerCreateSerializer,
    AdminCustomerDetailSerializer,
    AdminCustomerListResponseSerializer,
    AdminCustomerListSerializer,
    AdminCustomerResponseSerializer,
    AdminCustomerUpdateSerializer,
    AdminResetPasswordSerializer,
    AssignRoleSerializer,
    AvatarUploadSerializer,
    ChangePasswordSerializer,
    EmailSerializer,
    EmptyDataResponseSerializer,
    LoginSerializer,
    RefreshSerializer,
    RegisterSerializer,
    ResetPasswordSerializer,
    SessionResponseSerializer,
    TokenResponseSerializer,
    UserResponseSerializer,
    UserSerializer,
    VerifyEmailSerializer,
)
from .services import AccountService
from .tokens import VersionedTokenRefreshSerializer


def set_refresh_cookie(response, refresh_token: str) -> None:
    response.set_cookie(
        key=settings.JWT_REFRESH_COOKIE_NAME,
        value=refresh_token,
        max_age=int(settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].total_seconds()),
        secure=settings.JWT_REFRESH_COOKIE_SECURE,
        httponly=True,
        samesite=settings.JWT_REFRESH_COOKIE_SAMESITE,
        path=settings.JWT_REFRESH_COOKIE_PATH,
        domain=settings.JWT_REFRESH_COOKIE_DOMAIN,
    )


def clear_refresh_cookie(response) -> None:
    response.delete_cookie(
        key=settings.JWT_REFRESH_COOKIE_NAME,
        path=settings.JWT_REFRESH_COOKIE_PATH,
        domain=settings.JWT_REFRESH_COOKIE_DOMAIN,
        samesite=settings.JWT_REFRESH_COOKIE_SAMESITE,
    )


def token_response(*, user, access: str, message: str):
    return success_response(
        message=message,
        data={
            "access": access,
            "access_expires_in": int(settings.SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"].total_seconds()),
            "user": UserSerializer(user).data,
        },
    )


def refresh_session(*, refresh: str, message: str):
    serializer = VersionedTokenRefreshSerializer(data={"refresh": refresh})
    serializer.is_valid(raise_exception=True)
    rotated_refresh = serializer.validated_data.get("refresh")
    user_id = RefreshToken(rotated_refresh or refresh)["user_id"]
    user = get_user_for_profile(user_id)
    response = token_response(
        user=user,
        access=serializer.validated_data["access"],
        message=message,
    )
    if rotated_refresh:
        set_refresh_cookie(response, rotated_refresh)
    return response


class RegisterView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth_register"

    @extend_schema(request=RegisterSerializer, responses={201: UserResponseSerializer})
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = AccountService.register_customer(**serializer.validated_data)
        return success_response(
            message="Đăng ký thành công. Vui lòng kiểm tra email để xác thực tài khoản",
            data=UserSerializer(user).data,
            status_code=201,
        )


class VerifyEmailView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth_email"

    @extend_schema(request=VerifyEmailSerializer, responses={200: UserResponseSerializer})
    def post(self, request):
        serializer = VerifyEmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = AccountService.verify_email(**serializer.validated_data)
        return success_response(
            message="Xác thực email thành công",
            data=UserSerializer(user).data,
        )


class ResendVerificationView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth_email"

    @extend_schema(request=EmailSerializer, responses={200: EmptyDataResponseSerializer})
    def post(self, request):
        serializer = EmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        AccountService.resend_verification(**serializer.validated_data)
        return success_response(
            message="Nếu tài khoản cần xác thực, email hướng dẫn sẽ được gửi",
        )


class LoginView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth_login"

    @extend_schema(request=LoginSerializer, responses={200: TokenResponseSerializer})
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user, tokens = AccountService.authenticate(**serializer.validated_data)
        update_last_login(None, user)
        response = token_response(
            user=user,
            access=tokens["access"],
            message="Đăng nhập thành công",
        )
        set_refresh_cookie(response, tokens["refresh"])
        return response


class RefreshView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth_refresh"

    @extend_schema(request=RefreshSerializer, responses={200: TokenResponseSerializer})
    def post(self, request):
        input_serializer = RefreshSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)
        refresh = input_serializer.validated_data.get("refresh") or request.COOKIES.get(
            settings.JWT_REFRESH_COOKIE_NAME
        )
        return refresh_session(
            refresh=refresh,
            message="Làm mới phiên đăng nhập thành công",
        )


class SessionView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth_refresh"

    @extend_schema(request=None, responses={200: SessionResponseSerializer})
    def post(self, request):
        refresh = request.COOKIES.get(settings.JWT_REFRESH_COOKIE_NAME)
        if not refresh:
            return success_response(
                message="Không có phiên đăng nhập",
                data=None,
            )

        try:
            return refresh_session(
                refresh=refresh,
                message="Khôi phục phiên đăng nhập thành công",
            )
        except BusinessError:
            response = success_response(
                message="Phiên đăng nhập không còn hiệu lực",
                data=None,
            )
            clear_refresh_cookie(response)
            return response


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(request=RefreshSerializer, responses={200: EmptyDataResponseSerializer})
    def post(self, request):
        serializer = RefreshSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        refresh = serializer.validated_data.get("refresh") or request.COOKIES.get(
            settings.JWT_REFRESH_COOKIE_NAME
        )
        if refresh:
            try:
                RefreshToken(refresh).blacklist()
            except TokenError:
                pass

        response = success_response(message="Đăng xuất thành công")
        clear_refresh_cookie(response)
        return response


class ForgotPasswordView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth_password"

    @extend_schema(request=EmailSerializer, responses={200: EmptyDataResponseSerializer})
    def post(self, request):
        serializer = EmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        AccountService.request_password_reset(**serializer.validated_data)
        return success_response(
            message="Nếu email tồn tại, hướng dẫn đặt lại mật khẩu sẽ được gửi",
        )


class ResetPasswordView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth_password"

    @extend_schema(request=ResetPasswordSerializer, responses={200: EmptyDataResponseSerializer})
    def post(self, request):
        serializer = ResetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        AccountService.reset_password(**serializer.validated_data)
        return success_response(message="Đặt lại mật khẩu thành công")


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: UserResponseSerializer})
    def get(self, request):
        return success_response(data=UserSerializer(request.user).data)

    @extend_schema(request=UserSerializer, responses={200: UserResponseSerializer})
    def patch(self, request):
        serializer = UserSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success_response(
            message="Cập nhật hồ sơ thành công",
            data=serializer.data,
        )


class AvatarUploadView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    @extend_schema(request=AvatarUploadSerializer, responses={200: UserResponseSerializer})
    def post(self, request):
        serializer = AvatarUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = AccountService.update_avatar(
            user=request.user,
            uploaded_file=serializer.validated_data["avatar"],
        )
        return success_response(
            message="Cập nhật ảnh đại diện thành công",
            data=UserSerializer(user).data,
        )


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth_password"

    @extend_schema(request=ChangePasswordSerializer, responses={200: EmptyDataResponseSerializer})
    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        AccountService.change_password(user=request.user, **serializer.validated_data)
        response = success_response(
            message="Đổi mật khẩu thành công. Vui lòng đăng nhập lại",
        )
        clear_refresh_cookie(response)
        return response


class AssignRoleView(APIView):
    permission_classes = [IsAdmin]

    @extend_schema(request=AssignRoleSerializer, responses={200: UserResponseSerializer})
    def post(self, request, user_id: int):
        serializer = AssignRoleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = AccountService.assign_role(
            actor=request.user,
            target_user_id=user_id,
            **serializer.validated_data,
        )
        return success_response(
            message="Cập nhật vai trò thành công",
            data=UserSerializer(user).data,
        )


class AddressListCreateView(APIView):
    permission_classes = [IsCustomer]

    @extend_schema(responses={200: AddressListResponseSerializer})
    def get(self, request):
        addresses = Address.objects.filter(user=request.user, is_deleted=False)
        return success_response(data=AddressSerializer(addresses, many=True).data)

    @extend_schema(request=AddressSerializer, responses={201: AddressResponseSerializer})
    def post(self, request):
        serializer = AddressSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        address = AccountService.create_address(
            user=request.user,
            address_data=dict(serializer.validated_data),
        )
        return success_response(
            message="Thêm địa chỉ thành công",
            data=AddressSerializer(address).data,
            status_code=201,
        )


class AddressDetailView(APIView):
    permission_classes = [IsCustomer]

    @extend_schema(request=AddressSerializer, responses={200: AddressResponseSerializer})
    def patch(self, request, address_id: int):
        serializer = AddressSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        address = AccountService.update_address(
            user=request.user,
            address_id=address_id,
            address_data=dict(serializer.validated_data),
        )
        return success_response(
            message="Cập nhật địa chỉ thành công",
            data=AddressSerializer(address).data,
        )

    @extend_schema(responses={200: EmptyDataResponseSerializer})
    def delete(self, request, address_id: int):
        AccountService.delete_address(user=request.user, address_id=address_id)
        return success_response(message="Xóa địa chỉ thành công")


class SetDefaultAddressView(APIView):
    permission_classes = [IsCustomer]

    @extend_schema(request=None, responses={200: AddressResponseSerializer})
    def post(self, request, address_id: int):
        address = AccountService.set_default_address(
            user=request.user,
            address_id=address_id,
        )
        return success_response(
            message="Đã đặt địa chỉ mặc định",
            data=AddressSerializer(address).data,
        )


class AdminCustomerListCreateView(generics.GenericAPIView):
    permission_classes = [IsAdmin]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ("is_active", "is_email_verified")
    search_fields = ("email", "full_name", "phone")
    ordering_fields = ("created_at", "email", "full_name")
    ordering = ("-created_at",)

    def get_queryset(self):
        return User.objects.filter(
            role=User.Role.CUSTOMER,
            is_deleted=False,
        ).select_related("customer_profile")

    def get_serializer_class(self):
        if self.request.method == "POST":
            return AdminCustomerCreateSerializer
        return AdminCustomerListSerializer

    @extend_schema(
        operation_id="admin_customers_list",
        responses={200: AdminCustomerListResponseSerializer},
    )
    def get(self, request):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        serializer = AdminCustomerListSerializer(page, many=True)
        return self.get_paginated_response(serializer.data)

    @extend_schema(
        request=AdminCustomerCreateSerializer,
        responses={201: AdminCustomerResponseSerializer},
    )
    def post(self, request):
        serializer = AdminCustomerCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        customer = AccountService.create_customer_by_admin(
            actor=request.user,
            **serializer.validated_data,
        )
        return success_response(
            message="Tạo khách hàng thành công",
            data=AdminCustomerDetailSerializer(customer).data,
            status_code=201,
        )


class AdminCustomerDetailView(APIView):
    permission_classes = [IsAdmin]

    @staticmethod
    def get_customer(customer_id: int):
        customer = get_customer_for_admin(customer_id)
        if customer is None:
            raise BusinessError("Không tìm thấy khách hàng", http_status=404)
        return customer

    @extend_schema(
        operation_id="admin_customers_retrieve",
        responses={200: AdminCustomerResponseSerializer},
    )
    def get(self, request, customer_id: int):
        customer = self.get_customer(customer_id)
        return success_response(data=AdminCustomerDetailSerializer(customer).data)

    @extend_schema(
        request=AdminCustomerUpdateSerializer,
        responses={200: AdminCustomerResponseSerializer},
    )
    def patch(self, request, customer_id: int):
        serializer = AdminCustomerUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        customer = AccountService.update_customer_by_admin(
            actor=request.user,
            target_user_id=customer_id,
            customer_data=dict(serializer.validated_data),
        )
        return success_response(
            message="Cập nhật khách hàng thành công",
            data=AdminCustomerDetailSerializer(customer).data,
        )

    @extend_schema(responses={200: EmptyDataResponseSerializer})
    def delete(self, request, customer_id: int):
        AccountService.delete_customer_by_admin(
            actor=request.user,
            target_user_id=customer_id,
        )
        return success_response(message="Xóa khách hàng thành công")


class LockUserView(APIView):
    permission_classes = [IsAdmin]

    @extend_schema(request=AccountStatusSerializer, responses={200: UserResponseSerializer})
    def post(self, request, user_id: int):
        serializer = AccountStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = AccountService.set_account_active(
            actor=request.user,
            target_user_id=user_id,
            is_active=False,
            **serializer.validated_data,
        )
        return success_response(
            message="Khóa tài khoản thành công",
            data=UserSerializer(user).data,
        )


class UnlockUserView(APIView):
    permission_classes = [IsAdmin]

    @extend_schema(request=AccountStatusSerializer, responses={200: UserResponseSerializer})
    def post(self, request, user_id: int):
        serializer = AccountStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = AccountService.set_account_active(
            actor=request.user,
            target_user_id=user_id,
            is_active=True,
            **serializer.validated_data,
        )
        return success_response(
            message="Mở khóa tài khoản thành công",
            data=UserSerializer(user).data,
        )


class AdminResetPasswordView(APIView):
    permission_classes = [IsAdmin]

    @extend_schema(
        request=AdminResetPasswordSerializer,
        responses={200: EmptyDataResponseSerializer},
    )
    def post(self, request, user_id: int):
        serializer = AdminResetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        AccountService.admin_reset_password(
            actor=request.user,
            target_user_id=user_id,
            **serializer.validated_data,
        )
        return success_response(
            message="Đã thu hồi mật khẩu cũ và gửi liên kết đặt lại qua email",
        )
