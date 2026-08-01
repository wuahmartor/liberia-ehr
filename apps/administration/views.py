from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView

from apps.patients.models import Patient


User = get_user_model()


class AdministrationDashboardView(LoginRequiredMixin, TemplateView):
    """
    Display the Liberia EHR administration dashboard.

    Full browser requests render the complete application shell.
    HTMX requests render only the administration workspace.
    """

    template_name = "administration/dashboard.html"
    login_url = "accounts:login"

    def get_template_names(self):
        """
        Return only the workspace partial when HTMX requests the page.
        """

        is_htmx_request = (
            self.request.headers.get("HX-Request") == "true"
        )

        if is_htmx_request:
            return [
                "administration/partials/dashboard_workspace.html"
            ]

        return [self.template_name]

    def get_context_data(self, **kwargs):
        """
        Add navigation state and administration dashboard metrics.
        """

        context = super().get_context_data(**kwargs)

        context.update(
            {
                "active_primary_nav": "administration",
                "active_administration_module": "dashboard",
                "total_patients": Patient.objects.count(),
                "total_users": User.objects.count(),
                "active_users": User.objects.filter(
                    is_active=True,
                ).count(),
            }
        )

        return context