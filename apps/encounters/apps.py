from django.apps import AppConfig


class EncountersConfig(AppConfig):
    """
    Django application configuration for encounters.
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.encounters"
    verbose_name = "Encounters"