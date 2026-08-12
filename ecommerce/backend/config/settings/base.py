from datetime import timedelta
from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parents[2]
REPOSITORY_DIR = BASE_DIR.parent

env = environ.Env(
    DJANGO_DEBUG=(bool, False),
    DJANGO_SECURE_SSL_REDIRECT=(bool, False),
    DJANGO_SESSION_COOKIE_SECURE=(bool, False),
    DJANGO_CSRF_COOKIE_SECURE=(bool, False),
    CELERY_TASK_ALWAYS_EAGER=(bool, False),
    AI_FEATURES_ENABLED=(bool, True),
)

root_env_file = REPOSITORY_DIR / ".env"
if root_env_file.exists():
    environ.Env.read_env(root_env_file)

SECRET_KEY = env("DJANGO_SECRET_KEY")
DEBUG = env.bool("DJANGO_DEBUG")
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])

INSTALLED_APPS = [
    "daphne",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.postgres",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "django_filters",
    "rest_framework",
    "rest_framework_simplejwt.token_blacklist",
    "drf_spectacular",
    "channels",
    "apps.common.apps.CommonConfig",
    "apps.account.apps.AccountConfig",
    "apps.catalog.apps.CatalogConfig",
    "apps.product.apps.ProductConfig",
    "apps.inventory.apps.InventoryConfig",
    "apps.storefront.apps.StorefrontConfig",
    "apps.engagement.apps.EngagementConfig",
    "apps.ai.apps.AIConfig",
    "apps.order.apps.OrderConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "apps.common.middleware.RequestIdMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("POSTGRES_DB"),
        "USER": env("POSTGRES_USER"),
        "PASSWORD": env("POSTGRES_PASSWORD"),
        "HOST": env("POSTGRES_HOST"),
        "PORT": env.int("POSTGRES_PORT", default=5432),
        "CONN_MAX_AGE": env.int("POSTGRES_CONN_MAX_AGE", default=60),
        "OPTIONS": {"sslmode": env("POSTGRES_SSLMODE", default="prefer")},
    }
}

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": env("REDIS_CACHE_URL", default="redis://redis:6379/1"),
        "OPTIONS": {"CLIENT_CLASS": "django_redis.client.DefaultClient"},
    }
}

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [env("CHANNEL_LAYER_URL", default="redis://redis:6379/3")],
        },
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "vi"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = Path(env("STATIC_ROOT", default=str(BASE_DIR / "staticfiles")))
MEDIA_URL = "/media/"
MEDIA_ROOT = Path(env("MEDIA_ROOT", default=str(BASE_DIR / "media")))
MAX_AVATAR_UPLOAD_MB = env.int("MAX_AVATAR_UPLOAD_MB", default=5)
MAX_SELLER_DOCUMENT_UPLOAD_MB = env.int("MAX_SELLER_DOCUMENT_UPLOAD_MB", default=10)
MAX_IMAGE_UPLOAD_MB = env.int("MAX_IMAGE_UPLOAD_MB", default=10)
MAX_VIDEO_UPLOAD_MB = env.int("MAX_VIDEO_UPLOAD_MB", default=100)
SELLER_DOCUMENT_LINK_MAX_AGE_SECONDS = env.int(
    "SELLER_DOCUMENT_LINK_MAX_AGE_SECONDS",
    default=300,
)

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
AUTH_USER_MODEL = "account.User"

CORS_ALLOWED_ORIGINS = env.list("DJANGO_CORS_ALLOWED_ORIGINS", default=[])
CORS_ALLOW_CREDENTIALS = True
CSRF_TRUSTED_ORIGINS = env.list("DJANGO_CSRF_TRUSTED_ORIGINS", default=[])

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ("apps.account.authentication.VersionedJWTAuthentication",),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "DEFAULT_FILTER_BACKENDS": (
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ),
    "DEFAULT_PAGINATION_CLASS": "apps.common.pagination.StandardPagination",
    "EXCEPTION_HANDLER": "apps.common.exception_handler.custom_exception_handler",
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_THROTTLE_RATES": {
        "auth_register": env("AUTH_RATE_LIMIT", default="5/minute"),
        "auth_login": env("AUTH_RATE_LIMIT", default="5/minute"),
        "auth_refresh": env("AUTH_RATE_LIMIT", default="10/minute"),
        "auth_email": env("AUTH_RATE_LIMIT", default="5/minute"),
        "auth_password": env("AUTH_RATE_LIMIT", default="5/minute"),
        "ai_anonymous": env("AI_ANONYMOUS_RATE_LIMIT", default="10/minute"),
        "ai_authenticated": env("AI_AUTHENTICATED_RATE_LIMIT", default="30/minute"),
        "ai_search_anonymous": env("AI_ANONYMOUS_RATE_LIMIT", default="10/minute"),
        "ai_search_authenticated": env("AI_AUTHENTICATED_RATE_LIMIT", default="30/minute"),
        "payment_callback": env("PAYMENT_CALLBACK_RATE_LIMIT", default="120/minute"),
    },
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=env.int("JWT_ACCESS_TOKEN_MINUTES", default=15)),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=env.int("JWT_REFRESH_TOKEN_DAYS", default=7)),
    "ROTATE_REFRESH_TOKENS": env.bool("JWT_ROTATE_REFRESH_TOKENS", default=True),
    "BLACKLIST_AFTER_ROTATION": env.bool("JWT_BLACKLIST_AFTER_ROTATION", default=True),
    "UPDATE_LAST_LOGIN": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
}

JWT_REFRESH_COOKIE_NAME = env("JWT_REFRESH_COOKIE_NAME", default="refresh_token")
JWT_REFRESH_COOKIE_SECURE = env.bool("JWT_REFRESH_COOKIE_SECURE", default=False)
JWT_REFRESH_COOKIE_SAMESITE = env("JWT_REFRESH_COOKIE_SAMESITE", default="Lax")
JWT_REFRESH_COOKIE_PATH = env("JWT_REFRESH_COOKIE_PATH", default="/api/v1/auth/")
JWT_REFRESH_COOKIE_DOMAIN = env("JWT_REFRESH_COOKIE_DOMAIN", default="") or None
PASSWORD_RESET_TIMEOUT = env.int("PASSWORD_RESET_TOKEN_MINUTES", default=30) * 60
EMAIL_VERIFICATION_TOKEN_MAX_AGE = env.int("EMAIL_VERIFICATION_TOKEN_HOURS", default=24) * 3600
FRONTEND_URL = env("FRONTEND_URL", default="http://localhost:8080")

SPECTACULAR_SETTINGS = {
    "TITLE": "Multi-Vendor AI E-commerce API",
    "DESCRIPTION": "REST API for the multi-vendor AI e-commerce platform.",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "ENUM_NAME_OVERRIDES": {
        "ProductStatusEnum": "apps.product.models.Product.Status",
        "StockDocumentStatusEnum": "apps.inventory.models.StockEntry.Status",
    },
}

EMAIL_BACKEND = env("EMAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend")
EMAIL_HOST = env("EMAIL_HOST", default="localhost")
EMAIL_PORT = env.int("EMAIL_PORT", default=1025)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
if EMAIL_HOST.lower() == "smtp.gmail.com":
    # Google displays App Passwords in groups of four; SMTP expects 16 characters.
    EMAIL_HOST_PASSWORD = "".join(EMAIL_HOST_PASSWORD.split())
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=False)
EMAIL_TIMEOUT = env.int("EMAIL_TIMEOUT_SECONDS", default=30)
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="no-reply@example.com")

CELERY_BROKER_URL = env("CELERY_BROKER_URL", default="redis://redis:6379/0")
CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND", default="redis://redis:6379/2")
CELERY_TASK_ALWAYS_EAGER = env.bool("CELERY_TASK_ALWAYS_EAGER")
CELERY_TASK_TIME_LIMIT = env.int("CELERY_TASK_TIME_LIMIT_SECONDS", default=300)
CELERY_TASK_SOFT_TIME_LIMIT = env.int("CELERY_TASK_SOFT_TIME_LIMIT_SECONDS", default=270)
CELERY_TIMEZONE = "UTC"
CELERY_ENABLE_UTC = True
CELERY_BEAT_SCHEDULE = {
    "expire-pending-orders": {
        "task": "apps.order.tasks.expire_pending_orders",
        "schedule": 60.0,
    },
    "release-expired-stock-reservations": {
        "task": "apps.order.tasks.release_expired_stock_reservations",
        "schedule": 300.0,
    },
}

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {"()": "apps.common.logging.JsonFormatter"},
    },
    "filters": {
        "request_context": {"()": "apps.common.logging.RequestContextFilter"},
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "json",
            "filters": ["request_context"],
        },
    },
    "root": {
        "handlers": ["console"],
        "level": env("LOG_LEVEL", default="INFO"),
    },
}

# AI service layer. The database vector schema is pinned to 1536 dimensions;
# changing the runtime value requires a migration and a full re-index.
AI_FEATURES_ENABLED = env.bool("AI_FEATURES_ENABLED", default=True)
AI_PROVIDER = env("AI_PROVIDER", default="gemini")
AI_MODEL = env("AI_MODEL", default="gemini-3.6-flash")
AI_EMBEDDING_MODEL = env("AI_EMBEDDING_MODEL", default="gemini-embedding-2")
AI_EMBEDDING_DIMENSIONS = env.int("AI_EMBEDDING_DIMENSIONS", default=1536)
AI_REQUEST_TIMEOUT_SECONDS = env.float("AI_REQUEST_TIMEOUT_SECONDS", default=20.0)
AI_MAX_RETRIES = env.int("AI_MAX_RETRIES", default=3)
AI_RETRY_BACKOFF_SECONDS = env.float("AI_RETRY_BACKOFF_SECONDS", default=0.25)
AI_CACHE_TTL_SECONDS = env.int("AI_CACHE_TTL_SECONDS", default=3600)
AI_EMBEDDING_CACHE_TTL_SECONDS = env.int(
    "AI_EMBEDDING_CACHE_TTL_SECONDS",
    default=3600,
)
AI_RECOMMENDATION_CACHE_TTL_SECONDS = env.int("AI_RECOMMENDATION_CACHE_TTL_SECONDS", default=900)
AI_SIMILAR_CACHE_TTL_SECONDS = env.int("AI_SIMILAR_CACHE_TTL_SECONDS", default=1800)
AI_MAX_OUTPUT_TOKENS = env.int("AI_MAX_OUTPUT_TOKENS", default=1024)
AI_INPUT_COST_PER_MILLION = env("AI_INPUT_COST_PER_MILLION", default="0")
AI_OUTPUT_COST_PER_MILLION = env("AI_OUTPUT_COST_PER_MILLION", default="0")
GEMINI_API_KEY = env("GEMINI_API_KEY", default="")
GEMINI_GENERATION_BASE_URL = env(
    "GEMINI_GENERATION_BASE_URL",
    default="https://generativelanguage.googleapis.com/v1beta",
)
GEMINI_EMBEDDING_BASE_URL = env(
    "GEMINI_EMBEDDING_BASE_URL",
    default="https://generativelanguage.googleapis.com/v1beta",
)

VNPAY_TMN_CODE = env("VNPAY_TMN_CODE", default="")
VNPAY_HASH_SECRET = env("VNPAY_HASH_SECRET", default="")
VNPAY_PAYMENT_URL = env(
    "VNPAY_PAYMENT_URL", default="https://sandbox.vnpayment.vn/paymentv2/vpcpay.html"
)
VNPAY_RETURN_URL = env("VNPAY_RETURN_URL", default=f"{FRONTEND_URL.rstrip('/')}/payment/return")
