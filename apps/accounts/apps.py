from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.accounts"
    verbose_name = "User Accounts and Access Control"

    def ready(self):
        # Register signals when Django starts.
        import apps.accounts.signals  # noqa: F401