from urllib.parse import urlencode

from django.http import HttpResponse
from django.shortcuts import redirect
from django.urls import reverse


class LoginRequiredMiddleware:
    """
    Require login across the EHR while keeping authentication pages public.
    """

    def __init__(self, get_response):
        self.get_response = get_response

        self.public_url_names = {
            "accounts:login",
            "password_reset",
            "password_reset_done",
            "password_reset_confirm",
            "password_reset_complete",
        }

    def __call__(self, request):
        if request.user.is_authenticated:
            return self.get_response(request)

        resolver_match = request.resolver_match

        if resolver_match:
            current_url_name = resolver_match.view_name

            if current_url_name in self.public_url_names:
                return self.get_response(request)

        login_url = reverse("accounts:login")

        query_string = urlencode(
            {
                "next": request.get_full_path(),
            }
        )

        redirect_url = f"{login_url}?{query_string}"

        if request.headers.get("HX-Request") == "true":
            response = HttpResponse(status=401)
            response["HX-Redirect"] = redirect_url
            return response

        return redirect(redirect_url)