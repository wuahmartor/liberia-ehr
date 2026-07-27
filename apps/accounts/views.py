


from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_http_methods, require_POST

from .forms import EHRLoginForm
from .models import UserProfile


def get_role_redirect_url(user):
    profile = getattr(user, "profile", None)

    if user.is_superuser:
        return reverse("admin:index")

    if profile is None:
        return reverse("core:dashboard")

    role_redirects = {
        UserProfile.Role.SYSTEM_ADMIN: (
            "core:administration_dashboard"
        ),
        UserProfile.Role.FACILITY_ADMIN: (
            "core:administration_dashboard"
        ),
        UserProfile.Role.PHYSICIAN: (
            "core:clinical_dashboard"
        ),
        UserProfile.Role.NURSE: (
            "core:clinical_dashboard"
        ),
        UserProfile.Role.NURSE_PRACTITIONER: (
            "core:clinical_dashboard"
        ),
        UserProfile.Role.COMMUNITY_HEALTH_WORKER: (
            "core:clinical_dashboard"
        ),
        UserProfile.Role.PHARMACIST: (
            "core:pharmacy_dashboard"
        ),
        UserProfile.Role.LAB_TECHNICIAN: (
            "core:laboratory_dashboard"
        ),
        UserProfile.Role.RADIOLOGY_TECHNICIAN: (
            "core:radiology_dashboard"
        ),
        UserProfile.Role.DATA_ANALYST: (
            "core:analytics_dashboard"
        ),
        UserProfile.Role.INFORMATICIST: (
            "core:analytics_dashboard"
        ),
        UserProfile.Role.BILLING_OFFICER: (
            "core:billing_dashboard"
        ),
        UserProfile.Role.RECEPTIONIST: (
            "core:front_desk_dashboard"
        ),
        UserProfile.Role.AUDITOR: (
            "core:audit_dashboard"
        ),
        UserProfile.Role.PATIENT: (
            "core:patient_portal"
        ),
    }

    url_name = role_redirects.get(
        profile.role,
        "core:dashboard",
    )

    return reverse(url_name)


def _safe_next_url(request):
    next_url = (
        request.POST.get("next")
        or request.GET.get("next")
        or ""
    )

    if next_url and url_has_allowed_host_and_scheme(
        url=next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return next_url

    return None


@require_http_methods(["GET", "POST"])
def login_view(request):
    if request.user.is_authenticated:
        return redirect(get_role_redirect_url(request.user))

    if request.method == "POST":
        form = EHRLoginForm(
            request=request,
            data=request.POST,
        )

        if form.is_valid():
            user = form.get_user()

            login(request, user)

            remember_me = form.cleaned_data.get("remember_me")

            if remember_me:
                # Keep the session active for two weeks.
                request.session.set_expiry(60 * 60 * 24 * 14)
            else:
                # End the session when the browser closes.
                request.session.set_expiry(0)

            next_url = _safe_next_url(request)
            redirect_url = next_url or get_role_redirect_url(user)

            messages.success(
                request,
                f"Welcome back, "
                f"{user.get_full_name().strip() or user.username}.",
            )

            if request.headers.get("HX-Request") == "true":
                response = HttpResponse(status=204)
                response["HX-Redirect"] = redirect_url
                return response

            return redirect(redirect_url)

        if request.headers.get("HX-Request") == "true":
            return render(
                request,
                "accounts/partials/login_form.html",
                {
                    "form": form,
                    "next": request.POST.get("next", ""),
                },
                status=422,
            )

    else:
        form = EHRLoginForm(request=request)

    return render(
        request,
        "accounts/login.html",
        {
            "form": form,
            "next": request.GET.get("next", ""),
        },
    )


@require_POST
def logout_view(request):
    logout(request)

    messages.success(
        request,
        "You have been securely signed out.",
    )

    login_url = reverse("accounts:login")

    if request.headers.get("HX-Request") == "true":
        response = HttpResponse(status=204)
        response["HX-Redirect"] = login_url
        return response

    return redirect(login_url)


@login_required
def profile_view(request):
    profile = getattr(request.user, "profile", None)

    return render(
        request,
        "accounts/profile.html",
        {
            "profile": profile,
        },
    )


@login_required
def access_denied_view(request):
    return render(
        request,
        "accounts/access_denied.html",
        status=403,
    )