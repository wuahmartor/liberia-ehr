from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render


@login_required
def dashboard(request: HttpRequest) -> HttpResponse:
    return render(
        request,
        "orders/dashboard.html",
        {
            "active_primary_nav": "clinical",
            "active_clinical_module": "orders",
            "active_clinical_section": "dashboard",
        },
    )


@login_required
def order_list(request: HttpRequest) -> HttpResponse:
    return render(
        request,
        "orders/order_list.html",
        {
            "active_primary_nav": "clinical",
            "active_clinical_module": "orders",
            "active_clinical_section": "all-orders",
        },
    )


@login_required
def laboratory_orders(request: HttpRequest) -> HttpResponse:
    return render(
        request,
        "orders/laboratory_orders.html",
        {
            "active_primary_nav": "clinical",
            "active_clinical_module": "orders",
            "active_clinical_section": "laboratory",
        },
    )


@login_required
def imaging_orders(request: HttpRequest) -> HttpResponse:
    return render(
        request,
        "orders/imaging_orders.html",
        {
            "active_primary_nav": "clinical",
            "active_clinical_module": "orders",
            "active_clinical_section": "imaging",
        },
    )


@login_required
def pending_orders(request: HttpRequest) -> HttpResponse:
    return render(
        request,
        "orders/pending_orders.html",
        {
            "active_primary_nav": "clinical",
            "active_clinical_module": "orders",
            "active_clinical_section": "pending",
        },
    )