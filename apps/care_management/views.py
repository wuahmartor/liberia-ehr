from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render


@login_required
def dashboard(request: HttpRequest) -> HttpResponse:
    return render(
        request,
        "care_management/dashboard.html",
        {
            "active_primary_nav": "clinical",
            "active_clinical_module": "care-management",
            "active_clinical_section": "dashboard",
        },
    )


@login_required
def care_plans(request: HttpRequest) -> HttpResponse:
    return render(
        request,
        "care_management/care_plans.html",
        {
            "active_primary_nav": "clinical",
            "active_clinical_module": "care-management",
            "active_clinical_section": "care-plans",
        },
    )


@login_required
def referrals(request: HttpRequest) -> HttpResponse:
    return render(
        request,
        "care_management/referrals.html",
        {
            "active_primary_nav": "clinical",
            "active_clinical_module": "care-management",
            "active_clinical_section": "referrals",
        },
    )


@login_required
def follow_ups(request: HttpRequest) -> HttpResponse:
    return render(
        request,
        "care_management/follow_ups.html",
        {
            "active_primary_nav": "clinical",
            "active_clinical_module": "care-management",
            "active_clinical_section": "follow-ups",
        },
    )


@login_required
def discharge_planning(request: HttpRequest) -> HttpResponse:
    return render(
        request,
        "care_management/discharge_planning.html",
        {
            "active_primary_nav": "clinical",
            "active_clinical_module": "care-management",
            "active_clinical_section": "discharge",
        },
    )