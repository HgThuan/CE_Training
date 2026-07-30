from django.conf import settings
from django.contrib.auth.models import update_last_login
from django.core import signing
from django.http import FileResponse, Http404
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import OpenApiTypes, extend_schema
from rest_framework import filters, generics
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from apps.common.exceptions import BusinessError
from apps.common.responses import success_response

from .models import Address, SellerDocument, User
from .permissions import IsAdmin, IsCustomer, IsSellerApplicationOwner, IsShopOwner
from .selectors import (
    get_customer_for_admin,
    get_public_shop,
    get_seller_application_for_admin,
    get_seller_application_for_user,
    get_seller_for_admin,
    get_shop_for_owner,
    get_user_for_profile,
    seller_applications_for_admin,
    sellers_for_admin,
)
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
    AdminSellerListResponseSerializer,
    AdminSellerResponseSerializer,
    AdminSellerSerializer,
    AssignRoleSerializer,
    AvatarUploadSerializer,
    ChangePasswordSerializer,
    EmailSerializer,
    EmptyDataResponseSerializer,
    LoginSerializer,
    RefreshSerializer,
    RegisterSerializer,
    ResetPasswordSerializer,
    SellerApplicationListResponseSerializer,
    SellerApplicationResponseSerializer,
    SellerApplicationReviewSerializer,
    SellerApplicationSubmitSerializer,
    SellerDocumentResponseSerializer,
    SellerDocumentReviewSerializer,
    SellerDocumentSerializer,
    SellerDocumentUploadSerializer,
    SellerProfileSerializer,
    SessionResponseSerializer,
    ShopImageUploadSerializer,
    ShopResponseSerializer,
    ShopSerializer,
    ShopUpdateSerializer,
    TokenResponseSerializer,
    UserResponseSerializer,
    UserSerializer,
    VerifyEmailSerializer,
)
from .services import AccountService, SellerDocumentService, SellerOnboardingService, ShopService
from .tokens import VersionedTokenRefreshSerializer


@extend_schema(
    operation_id="seller_documents_download",
    responses={
        200: OpenApiTypes.BINARY,
        404: OpenApiTypes.OBJECT,
    },
    description="Tải xuống tài liệu người bán thông qua token",
)
@api_view(["GET"])
@authentication_classes([])
@permission_classes([AllowAny])
def seller_document_download(request, token: str):
    try:
        payload = signing.loads(
            token,
            salt="seller-document-download",
            max_age=settings.SELLER_DOCUMENT_LINK_MAX_AGE_SECONDS,
        )
    except signing.BadSignature as exc:
        raise Http404("Liên kết giấy tờ không hợp lệ hoặc đã hết hạn") from exc

    document = (
        SellerDocument.objects.select_related("seller_profile__user")
        .filter(
            pk=payload.get("document_id"),
            is_deleted=False,
            seller_profile__is_deleted=False,
            seller_profile__user__is_deleted=False,
        )
        .first()
    )
    if document is None or not document.file:
        raise Http404("Không tìm thấy giấy tờ")
    return FileResponse(
        document.file.open("rb"),
        as_attachment=True,
        filename=document.original_name,
    )


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
            request_id=request.request_id,
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
            request_id=request.request_id,
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
            request_id=request.request_id,
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
            request_id=request.request_id,
            **serializer.validated_data,
        )
        return success_response(
            message="Đã thu hồi mật khẩu cũ và gửi liên kết đặt lại qua email",
        )


class SellerApplicationView(APIView):
    def get_permissions(self):
        classes = [IsCustomer] if self.request.method == "POST" else [IsSellerApplicationOwner]
        return [permission() for permission in classes]

    @extend_schema(responses={200: SellerApplicationResponseSerializer})
    def get(self, request):
        profile = get_seller_application_for_user(request.user)
        if profile is not None:
            self.check_object_permissions(request, profile)
        return success_response(
            message="Lấy trạng thái hồ sơ seller thành công",
            data=(
                SellerProfileSerializer(profile, context={"request": request}).data
                if profile
                else None
            ),
        )

    @extend_schema(
        request=SellerApplicationSubmitSerializer,
        responses={201: SellerApplicationResponseSerializer},
    )
    def post(self, request):
        serializer = SellerApplicationSubmitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        profile = SellerOnboardingService.submit_application(
            user=request.user,
            application_data=dict(serializer.validated_data),
        )
        self.check_object_permissions(request, profile)
        return success_response(
            message="Đã gửi hồ sơ seller để xét duyệt",
            data=SellerProfileSerializer(profile, context={"request": request}).data,
            status_code=201,
        )


class SellerDocumentUploadView(APIView):
    permission_classes = [IsCustomer]
    parser_classes = [MultiPartParser, FormParser]

    @extend_schema(
        request=SellerDocumentUploadSerializer,
        responses={201: SellerDocumentResponseSerializer},
    )
    def post(self, request):
        serializer = SellerDocumentUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        document = SellerOnboardingService.add_document(
            user=request.user,
            document_type=serializer.validated_data["document_type"],
            uploaded_file=serializer.validated_data["document"],
        )
        return success_response(
            message="Tải giấy tờ seller thành công",
            data=SellerDocumentSerializer(document, context={"request": request}).data,
            status_code=201,
        )


class AdminSellerApplicationListView(generics.GenericAPIView):
    permission_classes = [IsAdmin]
    serializer_class = SellerProfileSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ("onboarding_status", "verification_status")
    search_fields = ("business_name", "tax_code", "user__email", "user__full_name")
    ordering_fields = ("submitted_at", "created_at", "business_name")
    ordering = ("-submitted_at",)

    def get_queryset(self):
        return seller_applications_for_admin()

    @extend_schema(
        operation_id="admin_seller_applications_list",
        responses={200: SellerApplicationListResponseSerializer},
    )
    def get(self, request):
        page = self.paginate_queryset(self.filter_queryset(self.get_queryset()))
        serializer = self.get_serializer(page, many=True, context={"request": request})
        return self.get_paginated_response(serializer.data)


class AdminSellerApplicationDetailView(APIView):
    permission_classes = [IsAdmin]

    @extend_schema(
        operation_id="admin_seller_applications_retrieve",
        responses={200: SellerApplicationResponseSerializer},
    )
    def get(self, request, profile_id: int):
        profile = get_seller_application_for_admin(profile_id)
        if profile is None:
            raise BusinessError("Không tìm thấy hồ sơ seller", http_status=404)
        return success_response(
            data=SellerProfileSerializer(profile, context={"request": request}).data,
        )


class AdminSellerApplicationApproveView(APIView):
    permission_classes = [IsAdmin]

    @extend_schema(
        request=SellerApplicationReviewSerializer,
        responses={200: SellerApplicationResponseSerializer},
    )
    def post(self, request, profile_id: int):
        serializer = SellerApplicationReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        profile = SellerOnboardingService.review_application(
            actor=request.user,
            profile_id=profile_id,
            approved=True,
            request_id=request.request_id,
            **serializer.validated_data,
        )
        return success_response(
            message="Duyệt hồ sơ seller thành công",
            data=SellerProfileSerializer(profile, context={"request": request}).data,
        )


class AdminSellerApplicationRejectView(APIView):
    permission_classes = [IsAdmin]

    @extend_schema(
        request=SellerApplicationReviewSerializer,
        responses={200: SellerApplicationResponseSerializer},
    )
    def post(self, request, profile_id: int):
        serializer = SellerApplicationReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        profile = SellerOnboardingService.review_application(
            actor=request.user,
            profile_id=profile_id,
            approved=False,
            request_id=request.request_id,
            **serializer.validated_data,
        )
        return success_response(
            message="Đã từ chối hồ sơ seller",
            data=SellerProfileSerializer(profile, context={"request": request}).data,
        )


class AdminSellerDocumentReviewView(APIView):
    permission_classes = [IsAdmin]

    @extend_schema(
        request=SellerDocumentReviewSerializer,
        responses={200: SellerDocumentResponseSerializer},
    )
    def post(self, request, document_id: int):
        serializer = SellerDocumentReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        document = SellerDocumentService.review_document(
            actor=request.user,
            document_id=document_id,
            request_id=request.request_id,
            **serializer.validated_data,
        )
        return success_response(
            message="Cập nhật xác minh giấy tờ thành công",
            data=SellerDocumentSerializer(document, context={"request": request}).data,
        )


class AdminSellerListView(generics.GenericAPIView):
    permission_classes = [IsAdmin]
    serializer_class = AdminSellerSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ("is_active", "shop__status")
    search_fields = ("email", "full_name", "phone", "shop__name")
    ordering_fields = ("created_at", "email", "shop__name")
    ordering = ("-created_at",)

    def get_queryset(self):
        return sellers_for_admin()

    @extend_schema(
        operation_id="admin_sellers_list",
        responses={200: AdminSellerListResponseSerializer},
    )
    def get(self, request):
        page = self.paginate_queryset(self.filter_queryset(self.get_queryset()))
        serializer = self.get_serializer(page, many=True, context={"request": request})
        return self.get_paginated_response(serializer.data)


class AdminSellerDetailView(APIView):
    permission_classes = [IsAdmin]

    @staticmethod
    def get_seller(user_id: int):
        seller = get_seller_for_admin(user_id)
        if seller is None:
            raise BusinessError("Không tìm thấy seller", http_status=404)
        return seller

    @extend_schema(
        operation_id="admin_sellers_retrieve",
        responses={200: AdminSellerResponseSerializer},
    )
    def get(self, request, user_id: int):
        seller = self.get_seller(user_id)
        return success_response(
            data=AdminSellerSerializer(seller, context={"request": request}).data,
        )

    @extend_schema(request=ShopUpdateSerializer, responses={200: AdminSellerResponseSerializer})
    def patch(self, request, user_id: int):
        seller = self.get_seller(user_id)
        shop = get_shop_for_owner(seller)
        if shop is None:
            raise BusinessError("Seller chưa có gian hàng", http_status=404)
        serializer = ShopUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        ShopService.update_shop_by_admin(
            actor=request.user,
            shop_id=shop.pk,
            shop_data=dict(serializer.validated_data),
            request_id=request.request_id,
        )
        seller = self.get_seller(user_id)
        return success_response(
            message="Cập nhật gian hàng seller thành công",
            data=AdminSellerSerializer(seller, context={"request": request}).data,
        )

    @extend_schema(request=AccountStatusSerializer, responses={200: EmptyDataResponseSerializer})
    def delete(self, request, user_id: int):
        serializer = AccountStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ShopService.soft_delete_seller(
            actor=request.user,
            target_user_id=user_id,
            request_id=request.request_id,
            **serializer.validated_data,
        )
        return success_response(message="Xóa seller thành công")


class SellerShopView(APIView):
    permission_classes = [IsShopOwner]

    def get_shop(self, request, shop_id: int | None = None):
        shop = get_shop_for_owner(request.user, shop_id)
        if shop is None:
            raise BusinessError("Không tìm thấy gian hàng", http_status=404)
        self.check_object_permissions(request, shop)
        return shop

    @extend_schema(responses={200: ShopResponseSerializer})
    def get(self, request, shop_id: int | None = None):
        shop = self.get_shop(request, shop_id)
        return success_response(
            data=ShopSerializer(shop, context={"request": request}).data,
        )

    @extend_schema(request=ShopUpdateSerializer, responses={200: ShopResponseSerializer})
    def patch(self, request, shop_id: int | None = None):
        self.get_shop(request, shop_id)
        serializer = ShopUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        shop = ShopService.update_own_shop(
            user=request.user,
            shop_data=dict(serializer.validated_data),
        )
        return success_response(
            message="Cập nhật gian hàng thành công",
            data=ShopSerializer(shop, context={"request": request}).data,
        )


class SellerShopImageUploadView(APIView):
    permission_classes = [IsShopOwner]
    parser_classes = [MultiPartParser, FormParser]
    image_type = ""

    @extend_schema(request=ShopImageUploadSerializer, responses={200: ShopResponseSerializer})
    def post(self, request):
        shop = get_shop_for_owner(request.user)
        if shop is None:
            raise BusinessError("Không tìm thấy gian hàng", http_status=404)
        self.check_object_permissions(request, shop)
        serializer = ShopImageUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        shop = ShopService.update_shop_image(
            user=request.user,
            image_type=self.image_type,
            uploaded_file=serializer.validated_data["image"],
        )
        return success_response(
            message="Cập nhật ảnh gian hàng thành công",
            data=ShopSerializer(shop, context={"request": request}).data,
        )


class AdminShopLockView(APIView):
    permission_classes = [IsAdmin]

    @extend_schema(request=AccountStatusSerializer, responses={200: ShopResponseSerializer})
    def post(self, request, shop_id: int):
        serializer = AccountStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        shop = ShopService.set_shop_locked(
            actor=request.user,
            shop_id=shop_id,
            locked=True,
            request_id=request.request_id,
            **serializer.validated_data,
        )
        return success_response(
            message="Khóa gian hàng thành công",
            data=ShopSerializer(shop).data,
        )


class AdminShopUnlockView(APIView):
    permission_classes = [IsAdmin]

    @extend_schema(request=AccountStatusSerializer, responses={200: ShopResponseSerializer})
    def post(self, request, shop_id: int):
        serializer = AccountStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        shop = ShopService.set_shop_locked(
            actor=request.user,
            shop_id=shop_id,
            locked=False,
            request_id=request.request_id,
            **serializer.validated_data,
        )
        return success_response(
            message="Mở khóa gian hàng thành công",
            data=ShopSerializer(shop).data,
        )


class PublicShopView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(responses={200: ShopResponseSerializer})
    def get(self, request, slug: str):
        shop = get_public_shop(slug)
        if shop is None:
            raise BusinessError("Không tìm thấy gian hàng", http_status=404)
        try:
            page = max(int(request.query_params.get("page", 1)), 1)
            page_size = min(max(int(request.query_params.get("page_size", 20)), 1), 100)
        except ValueError as exc:
            raise BusinessError(
                "Tham số phân trang không hợp lệ",
                errors={"pagination": ["page và page_size phải là số nguyên"]},
            ) from exc
        return success_response(
            message="Lấy thông tin gian hàng thành công",
            data={
                "shop": ShopSerializer(shop, context={"request": request}).data,
                "products": [],
                "available_filters": [],
                "available_sorts": ["newest", "price_asc", "price_desc", "rating"],
            },
            meta={
                "page": page,
                "page_size": page_size,
                "total_items": 0,
                "total_pages": 1,
            },
        )
