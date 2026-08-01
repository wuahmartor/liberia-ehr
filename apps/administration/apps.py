from django.apps import AppConfig


class AdministrationConfig(AppConfig):
    """
    Application configuration for the Liberia EHR
    administration module.
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.administration"
    verbose_name = "Administration"