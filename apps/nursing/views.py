from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render


@login_required
def dashboard(request: HttpRequest) -> HttpResponse:
    return render(
        request,
        "nursing/dashboard.html",
        {
            "active_primary_nav": "clinical",
            "active_clinical_module": "nursing",
            "active_clinical_section": "dashboard",
        },
    )


@login_required
def assessments(request: HttpRequest) -> HttpResponse:
    return render(
        request,
        "nursing/assessments.html",
        {
            "active_primary_nav": "clinical",
            "active_clinical_module": "nursing",
            "active_clinical_section": "assessments",
        },
    )


@login_required
def vitals(request: HttpRequest) -> HttpResponse:
    return render(
        request,
        "nursing/vitals.html",
        {
            "active_primary_nav": "clinical",
            "active_clinical_module": "nursing",
            "active_clinical_section": "vitals",
        },
    )


@login_required
def tasks(request: HttpRequest) -> HttpResponse:
    return render(
        request,
        "nursing/tasks.html",
        {
            "active_primary_nav": "clinical",
            "active_clinical_module": "nursing",
            "active_clinical_section": "tasks",
        },
    )