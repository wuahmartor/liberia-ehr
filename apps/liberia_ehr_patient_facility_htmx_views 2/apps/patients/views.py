from __future__ import annotations

from typing import Type

from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.db import models
from django.db.models import Prefetch, Q
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.views.generic import CreateView, DeleteView, UpdateView

from apps.core.htmx import is_htmx

from .forms import (
    EmergencyContactForm,
    InsuranceCoverageForm,
    PatientAddressForm,
    PatientAliasForm,
    PatientConsentForm,
    PatientContactPointForm,
    PatientFlagForm,
    PatientForm,
    PatientIdentifierForm,
    PatientRelationshipForm,
)
from .models import (
    EmergencyContact,
    InsuranceCoverage,
    Patient,
    PatientAddress,
    PatientAlias,
    PatientConsent,
    PatientContactPoint,
    PatientFlag,
    PatientIdentifier,
    PatientRelationship,
)


PATIENT_PAGE_SIZE = 25


def patient_queryset():
    return (
        Patient.objects.select_related("registration_facility")
        .prefetch_related(
            "identifiers",
            "addresses",
            "contact_points",
            "emergency_contacts",
            "consents",
            "insurance_coverages",
            Prefetch(
                "flags",
                queryset=PatientFlag.objects.filter(is_active=True),
            ),
        )
    )


@login_required
def patient_list(request: HttpRequest) -> HttpResponse:
    query = request.GET.get("q", "").strip()
    status = request.GET.get("status", "active").strip()
    facility_id = request.GET.get("facility", "").strip()

    patients = patient_queryset()

    if query:
        patients = patients.filter(
            Q(mrn__icontains=query)
            | Q(first_name__icontains=query)
            | Q(middle_name__icontains=query)
            | Q(last_name__icontains=query)
            | Q(preferred_name__icontains=query)
            | Q(identifiers__value__icontains=query)
            | Q(contact_points__value__icontains=query)
        ).distinct()

    if status == "active":
        patients = patients.filter(is_active=True, record_status="active")
    elif status == "inactive":
        patients = patients.filter(is_active=False)
    elif status == "deceased":
        patients = patients.filter(is_deceased=True)
    elif status == "merged":
        patients = patients.filter(record_status="merged")

    if facility_id:
        patients = patients.filter(registration_facility_id=facility_id)

    paginator = Paginator(patients, PATIENT_PAGE_SIZE)
    page = paginator.get_page(request.GET.get("page"))

    context = {
        "page_obj": page,
        "patients": page.object_list,
        "query": query,
        "status": status,
        "selected_facility": facility_id,
        "active_primary_nav": "clinical",
        "active_secondary_nav": "patients",
    }

    template = (
        "patients/partials/patient_table.html"
        if is_htmx(request)
        else "patients/patient_list.html"
    )
    return render(request, template, context)


@login_required
def patient_search(request: HttpRequest) -> HttpResponse:
    query = request.GET.get("q", "").strip()

    patients = Patient.objects.none()
    if len(query) >= 2:
        patients = (
            patient_queryset()
            .filter(
                Q(mrn__icontains=query)
                | Q(first_name__icontains=query)
                | Q(middle_name__icontains=query)
                | Q(last_name__icontains=query)
                | Q(preferred_name__icontains=query)
                | Q(identifiers__value__icontains=query)
                | Q(contact_points__value__icontains=query)
            )
            .distinct()[:12]
        )

    return render(
        request,
        "patients/partials/search_results.html",
        {
            "query": query,
            "patients": patients,
        },
    )


@login_required
def patient_detail(request: HttpRequest, patient_id) -> HttpResponse:
    patient = get_object_or_404(patient_queryset(), pk=patient_id)

    context = {
        "patient": patient,
        "active_primary_nav": "clinical",
        "active_secondary_nav": "patients",
    }

    template = (
        "patients/partials/patient_overview.html"
        if is_htmx(request)
        else "patients/patient_detail.html"
    )
    return render(request, template, context)


@login_required
def patient_sidebar(request: HttpRequest, patient_id) -> HttpResponse:
    patient = get_object_or_404(patient_queryset(), pk=patient_id)
    return render(
        request,
        "patients/partials/patient_sidebar.html",
        {"patient": patient},
    )


class PatientCreateView(LoginRequiredMixin, CreateView):
    model = Patient
    form_class = PatientForm
    template_name = "patients/patient_form.html"

    def get_template_names(self):
        if is_htmx(self.request):
            return ["patients/partials/patient_form.html"]
        return [self.template_name]

    def form_valid(self, form):
        patient = form.save(commit=False)
        patient.created_by = self.request.user
        patient.updated_by = self.request.user
        patient.save()
        self.object = patient

        if is_htmx(self.request):
            response = HttpResponse(status=204)
            response["HX-Trigger"] = "patientCreated"
            response["HX-Redirect"] = reverse(
                "patients:detail",
                kwargs={"patient_id": patient.pk},
            )
            return response

        return redirect("patients:detail", patient_id=patient.pk)


class PatientUpdateView(LoginRequiredMixin, UpdateView):
    model = Patient
    form_class = PatientForm
    pk_url_kwarg = "patient_id"
    template_name = "patients/patient_form.html"

    def get_template_names(self):
        if is_htmx(self.request):
            return ["patients/partials/patient_form.html"]
        return [self.template_name]

    def form_valid(self, form):
        patient = form.save(commit=False)
        patient.updated_by = self.request.user
        patient.save()
        self.object = patient

        if is_htmx(self.request):
            response = HttpResponse(status=204)
            response["HX-Trigger"] = "patientUpdated"
            return response

        return redirect("patients:detail", patient_id=patient.pk)


class PatientDeleteView(LoginRequiredMixin, DeleteView):
    model = Patient
    pk_url_kwarg = "patient_id"
    template_name = "patients/patient_confirm_delete.html"
    success_url = reverse_lazy("patients:list")

    def get_template_names(self):
        if is_htmx(self.request):
            return ["patients/partials/patient_confirm_delete.html"]
        return [self.template_name]

    def form_valid(self, form):
        response = super().form_valid(form)

        if is_htmx(self.request):
            htmx_response = HttpResponse(status=204)
            htmx_response["HX-Trigger"] = "patientDeleted"
            htmx_response["HX-Redirect"] = reverse("patients:list")
            return htmx_response

        return response


CHILD_CONFIG = {
    "identifier": (
        PatientIdentifier,
        PatientIdentifierForm,
        "identifiers",
    ),
    "alias": (
        PatientAlias,
        PatientAliasForm,
        "aliases",
    ),
    "address": (
        PatientAddress,
        PatientAddressForm,
        "addresses",
    ),
    "contact": (
        PatientContactPoint,
        PatientContactPointForm,
        "contact_points",
    ),
    "emergency-contact": (
        EmergencyContact,
        EmergencyContactForm,
        "emergency_contacts",
    ),
    "relationship": (
        PatientRelationship,
        PatientRelationshipForm,
        "relationships_from",
    ),
    "consent": (
        PatientConsent,
        PatientConsentForm,
        "consents",
    ),
    "insurance": (
        InsuranceCoverage,
        InsuranceCoverageForm,
        "insurance_coverages",
    ),
    "flag": (
        PatientFlag,
        PatientFlagForm,
        "flags",
    ),
}


def _child_config(kind: str):
    try:
        return CHILD_CONFIG[kind]
    except KeyError as exc:
        raise Http404("Unsupported patient record type.") from exc


@login_required
def patient_child_list(
    request: HttpRequest,
    patient_id,
    kind: str,
) -> HttpResponse:
    patient = get_object_or_404(Patient, pk=patient_id)
    model_class, _, related_name = _child_config(kind)
    records = getattr(patient, related_name).all()

    return render(
        request,
        "patients/partials/child_list.html",
        {
            "patient": patient,
            "records": records,
            "kind": kind,
            "model_name": model_class._meta.verbose_name,
        },
    )


@login_required
def patient_child_create(
    request: HttpRequest,
    patient_id,
    kind: str,
) -> HttpResponse:
    patient = get_object_or_404(Patient, pk=patient_id)
    _, form_class, _ = _child_config(kind)

    form = form_class(request.POST or None)

    if request.method == "POST" and form.is_valid():
        record = form.save(commit=False)
        record.patient = patient

        if hasattr(record, "created_by_id"):
            record.created_by = request.user
        if hasattr(record, "updated_by_id"):
            record.updated_by = request.user

        record.save()

        if is_htmx(request):
            response = HttpResponse(status=204)
            response["HX-Trigger"] = "patientChildSaved"
            return response

        return redirect("patients:detail", patient_id=patient.pk)

    template = (
        "patients/partials/child_form.html"
        if is_htmx(request)
        else "patients/child_form.html"
    )

    return render(
        request,
        template,
        {
            "patient": patient,
            "form": form,
            "kind": kind,
            "record": None,
        },
    )


@login_required
def patient_child_update(
    request: HttpRequest,
    patient_id,
    kind: str,
    record_id,
) -> HttpResponse:
    patient = get_object_or_404(Patient, pk=patient_id)
    model_class, form_class, _ = _child_config(kind)
    record = get_object_or_404(
        model_class,
        pk=record_id,
        patient=patient,
    )

    form = form_class(request.POST or None, instance=record)

    if request.method == "POST" and form.is_valid():
        record = form.save(commit=False)

        if hasattr(record, "updated_by_id"):
            record.updated_by = request.user

        record.save()

        if is_htmx(request):
            response = HttpResponse(status=204)
            response["HX-Trigger"] = "patientChildSaved"
            return response

        return redirect("patients:detail", patient_id=patient.pk)

    template = (
        "patients/partials/child_form.html"
        if is_htmx(request)
        else "patients/child_form.html"
    )

    return render(
        request,
        template,
        {
            "patient": patient,
            "form": form,
            "kind": kind,
            "record": record,
        },
    )


@login_required
def patient_child_delete(
    request: HttpRequest,
    patient_id,
    kind: str,
    record_id,
) -> HttpResponse:
    patient = get_object_or_404(Patient, pk=patient_id)
    model_class, _, _ = _child_config(kind)
    record = get_object_or_404(
        model_class,
        pk=record_id,
        patient=patient,
    )

    if request.method == "POST":
        record.delete()

        if is_htmx(request):
            response = HttpResponse(status=204)
            response["HX-Trigger"] = "patientChildDeleted"
            return response

        return redirect("patients:detail", patient_id=patient.pk)

    return render(
        request,
        "patients/partials/child_confirm_delete.html",
        {
            "patient": patient,
            "record": record,
            "kind": kind,
        },
    )
