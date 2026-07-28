from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render


@login_required
def dashboard(request: HttpRequest) -> HttpResponse:
    return render(
        request,
        "medications/dashboard.html",
        {
            "active_primary_nav": "clinical",
            "active_clinical_module": "medications",
            "active_clinical_section": "dashboard",
        },
    )


@login_required
def medication_list(request: HttpRequest) -> HttpResponse:
    return render(
        request,
        "medications/medication_list.html",
        {
            "active_primary_nav": "clinical",
            "active_clinical_module": "medications",
            "active_clinical_section": "list",
        },
    )


@login_required
def prescriptions(request: HttpRequest) -> HttpResponse:
    return render(
        request,
        "medications/prescriptions.html",
        {
            "active_primary_nav": "clinical",
            "active_clinical_module": "medications",
            "active_clinical_section": "prescriptions",
        },
    )


@login_required
def medication_administration_record(
    request: HttpRequest,
) -> HttpResponse:
    return render(
        request,
        "medications/mar.html",
        {
            "active_primary_nav": "clinical",
            "active_clinical_module": "medications",
            "active_clinical_section": "mar",
        },
    )


@login_required
def reconciliation(request: HttpRequest) -> HttpResponse:
    return render(
        request,
        "medications/reconciliation.html",
        {
            "active_primary_nav": "clinical",
            "active_clinical_module": "medications",
            "active_clinical_section": "reconciliation",
        },
    )