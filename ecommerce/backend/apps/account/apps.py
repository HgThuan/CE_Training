from django.apps import AppConfig


class AccountConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.account"
    verbose_name = "Account and Authentication"

    def ready(self) -> None:
        from . import schema  # noqa: F401
