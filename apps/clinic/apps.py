from django.apps import AppConfig


class ClinicConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name               = "apps.clinic"
    verbose_name       = "Медицинская клиника"

    def ready(self) -> None:
        # Место для подключения сигналов, если понадобятся в будущем.
        # Например: import apps.clinic.signals  # noqa: F401
        pass
