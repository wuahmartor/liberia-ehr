from __future__ import annotations

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.urls import reverse
from django.views.generic.edit import FormMixin

from .htmx import is_htmx


class HtmxTemplateResponseMixin:
    """
    Select a fragment template for HTMX and a full-page template otherwise.
    """

    template_name: str | None = None
    htmx_template_name: str | None = None

    def get_template_names(self):
        if is_htmx(self.request) and self.htmx_template_name:
            return [self.htmx_template_name]
        return super().get_template_names()


class UserTrackingFormMixin:
    """
    Assign created_by/updated_by when those model fields exist.
    """

    def form_valid(self, form):
        instance = form.save(commit=False)

        if hasattr(instance, "created_by_id") and not instance.created_by_id:
            instance.created_by = self.request.user

        if hasattr(instance, "updated_by_id"):
            instance.updated_by = self.request.user

        instance.save()
        form.save_m2m()
        self.object = instance

        return self.get_success_response()


class HtmxSuccessResponseMixin:
    """
    HTMX saves return 204 and fire a browser event.
    Normal saves redirect using Django's regular success URL.
    """

    hx_trigger_name = "recordSaved"

    def get_success_response(self):
        if is_htmx(self.request):
            response = HttpResponse(status=204)
            response["HX-Trigger"] = self.hx_trigger_name
            return response

        return super().form_valid(self.form_class(instance=self.object))

    def form_valid(self, form):
        if not isinstance(self, UserTrackingFormMixin):
            self.object = form.save()

        if is_htmx(self.request):
            response = HttpResponse(status=204)
            response["HX-Trigger"] = self.hx_trigger_name
            return response

        return super().form_valid(form)


class HtmxDeleteResponseMixin:
    hx_trigger_name = "recordDeleted"

    def delete(self, request, *args, **kwargs):
        response = super().delete(request, *args, **kwargs)

        if is_htmx(request):
            htmx_response = HttpResponse(status=204)
            htmx_response["HX-Trigger"] = self.hx_trigger_name
            return htmx_response

        return response


class SecureHtmxViewMixin(LoginRequiredMixin, HtmxTemplateResponseMixin):
    """Shared base mixin for authenticated full-page/fragment views."""

    login_url = "accounts:login"
