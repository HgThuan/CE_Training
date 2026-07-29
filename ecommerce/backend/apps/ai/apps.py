from django.apps import AppConfig


class AIConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.ai"
    verbose_name = "AI Services"

    def ready(self) -> None:
        from . import signals  # noqa: F401
