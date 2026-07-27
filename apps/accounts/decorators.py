
from functools import wraps

from django.contrib.auth.views import redirect_to_login
from django.http import HttpResponse
from django.shortcuts import redirect
from django.urls import reverse


def _deny_access(request):
    access_denied_url = reverse("accounts:access_denied")

    if request.headers.get("HX-Request") == "true":
        response = HttpResponse(status=403)
        response["HX-Redirect"] = access_denied_url
        return response

    return redirect(access_denied_url)


def active_staff_required(view_func):
    """
    Allow authenticated superusers or users with an active EHR profile.
    """

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(
                request.get_full_path(),
            )

        if request.user.is_superuser:
            return view_func(
                request,
                *args,
                **kwargs,
            )

        profile = getattr(
            request.user,
            "profile",
            None,
        )

        if profile is None:
            return _deny_access(request)

        if not profile.is_active_staff:
            return _deny_access(request)

        return view_func(
            request,
            *args,
            **kwargs,
        )

    return wrapper

def role_required(*allowed_roles):
    """
    Allow superusers or active users whose role is permitted.
    """

    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect_to_login(
                    request.get_full_path(),
                )

            if request.user.is_superuser:
                return view_func(
                    request,
                    *args,
                    **kwargs,
                )

            profile = getattr(
                request.user,
                "profile",
                None,
            )

            if profile is None:
                return _deny_access(request)

            if not profile.is_active_staff:
                return _deny_access(request)

            if profile.role not in allowed_roles:
                return _deny_access(request)

            return view_func(
                request,
                *args,
                **kwargs,
            )

        return wrapper

    return decorator


def clinical_staff_required(view_func):
    """
    Allow superusers or active clinical users.
    """

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(
                request.get_full_path(),
            )

        if request.user.is_superuser:
            return view_func(
                request,
                *args,
                **kwargs,
            )

        profile = getattr(
            request.user,
            "profile",
            None,
        )

        if profile is None:
            return _deny_access(request)

        if not profile.is_active_staff:
            return _deny_access(request)

        if not profile.is_clinician:
            return _deny_access(request)

        return view_func(
            request,
            *args,
            **kwargs,
        )

    return wrapper