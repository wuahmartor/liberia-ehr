"""
Liberia EHR Patient Views

File:
apps/patients/views.py

Purpose:
- Manage patient registration and demographic records.
- Display patient lists, searches, details, and clinical overview.
- Manage patient allergies, identifiers, addresses, contacts,
  relationships, insurance, consents, and flags.
- Connect the selected patient to an active clinical encounter.
- Restrict encounter-specific sidebar actions unless an active,
  open encounter exists.
"""

from __future__ import annotations

import json

from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Prefetch, Q
from django.http import (
    Http404,
    HttpRequest,
    HttpResponse,
    HttpResponseBadRequest,
)
from django.shortcuts import (
    get_object_or_404,
    redirect,
    render,
)
from django.urls import reverse
from django.views import View
from django.views.generic import CreateView, UpdateView

from apps.core.htmx import is_htmx
from apps.encounters.models import Encounter

from .forms import (
    EmergencyContactForm,
    InsuranceCoverageForm,
    PatientAddressForm,
    PatientAliasForm,
    PatientAllergyForm,
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
    PatientAllergy,
    PatientConsent,
    PatientContactPoint,
    PatientFlag,
    PatientFlagAcknowledgment,
    PatientIdentifier,
    PatientMergeRecord,
    PatientRelationship,
)


# ============================================================
# CONFIGURATION
# ============================================================

PATIENT_PAGE_SIZE = 25
PATIENT_SEARCH_LIMIT = 12
RECENT_ENCOUNTER_LIMIT = 10


# ============================================================
# SHARED QUERYSETS AND CONTEXT
# ============================================================

def patient_queryset():
    """
    Return the standard patient queryset used throughout the app.

    Facility-level and object-level security can later be applied
    here or through a dedicated selector layer.
    """

    return (
        Patient.objects
        .select_related(
            "registration_facility",
            "created_by",
            "updated_by",
        )
        .prefetch_related(
            "identifiers",
            "aliases",
            "addresses",
            "contact_points",
            "emergency_contacts",
            "relationships_from__related_patient",
            "relationships_to__patient",
            "consents",
            "insurance_coverages",
            "allergies",
            Prefetch(
                "flags",
                queryset=PatientFlag.objects.order_by(
                    "-is_active",
                    "-severity",
                    "-starts_at",
                ),
            ),
        )
    )


def active_encounter_queryset():
    """
    Return encounters considered active for clinical documentation.

    Planned and scheduled encounters are intentionally excluded
    because the patient has not yet arrived for direct clinical care.
    """

    return Encounter.objects.filter(
        is_active=True,
        status__in=[
            Encounter.EncounterStatus.ARRIVED,
            Encounter.EncounterStatus.TRIAGED,
            Encounter.EncounterStatus.IN_PROGRESS,
            Encounter.EncounterStatus.ON_HOLD,
        ],
    )


def get_patient_active_encounter(
    patient,
):
    """
    Return the patient's most recent active, open encounter.
    """

    open_statuses = {
        Encounter.EncounterStatus.PLANNED,
        Encounter.EncounterStatus.SCHEDULED,
        Encounter.EncounterStatus.ARRIVED,
        Encounter.EncounterStatus.TRIAGED,
        Encounter.EncounterStatus.IN_PROGRESS,
        Encounter.EncounterStatus.ON_HOLD,
    }

    return (
        Encounter.objects
        .filter(
            patient=patient,
            is_active=True,
            status__in=open_statuses,
        )
        .select_related(
            "patient",
            "attending_provider",
            "created_by",
        )
        .order_by(
            "-start_datetime",
            "-created_at",
        )
        .first()
    )

from apps.encounters.models import Encounter


def patient_recent_encounters(
    patient,
    limit: int = 10,
):
    """
    Return the patient's most recent encounter records.
    """

    return (
        Encounter.objects
        .filter(
            patient=patient,
        )
        .select_related(
            "patient",
            "attending_provider",
            "created_by",
        )
        .order_by(
            "-start_datetime",
            "-created_at",
        )[:limit]
    )

def patient_navigation_context(
    *,
    patient: Patient | None = None,
    subsection: str = "overview",
    active_encounter: Encounter | None = None,
) -> dict:
    """
    Shared navigation context for Clinical > Patients.

    When a patient is supplied and active_encounter is omitted,
    the patient's current active encounter is retrieved.
    """

    if patient is not None and active_encounter is None:
        active_encounter = get_patient_active_encounter(patient)

    return {
        "patient": patient,
        "selected_patient": patient,
        "active_primary_nav": "clinical",
        "active_clinical_module": "patients",
        "active_secondary_nav": "patients",
        "active_patient_section": subsection,
        "active_encounter": active_encounter,
        "has_active_encounter": active_encounter is not None,
    }


def trigger_response(
    event_name: str,
    *,
    redirect_url: str | None = None,
    payload: dict | None = None,
) -> HttpResponse:
    """
    Return a standard HTMX response containing an event trigger.
    """

    response = HttpResponse(status=204)

    if payload is None:
        response["HX-Trigger"] = event_name
    else:
        response["HX-Trigger"] = json.dumps(
            {
                event_name: payload,
            }
        )

    if redirect_url:
        response["HX-Redirect"] = redirect_url

    return response


# ============================================================
# PATIENT LIST AND SEARCH
# ============================================================

@login_required
def patient_list(
    request: HttpRequest,
) -> HttpResponse:
    """
    Display and filter the patient registry.
    """

    query = request.GET.get("q", "").strip()
    status = request.GET.get("status", "all").strip()
    facility_id = request.GET.get("facility", "").strip()

    patients = patient_queryset()

    if query:
        patients = patients.search(query)

    if status == "active":
        patients = patients.filter(
            record_status=Patient.RecordStatus.ACTIVE,
            is_active=True,
        )

    elif status == "inactive":
        patients = (
            patients
            .filter(
                Q(record_status=Patient.RecordStatus.INACTIVE)
                | Q(is_active=False)
            )
            .exclude(
                record_status=Patient.RecordStatus.MERGED,
            )
        )

    elif status == "deceased":
        patients = patients.filter(
            is_deceased=True,
        )

    elif status == "merged":
        patients = patients.filter(
            record_status=Patient.RecordStatus.MERGED,
        )

    elif status == "error":
        patients = patients.filter(
            record_status=Patient.RecordStatus.ENTERED_IN_ERROR,
        )

    elif status != "all":
        status = "all"

    if facility_id:
        patients = patients.filter(
            registration_facility_id=facility_id,
        )

    patients = patients.order_by(
        "last_name",
        "first_name",
        "date_of_birth",
    )

    paginator = Paginator(
        patients,
        PATIENT_PAGE_SIZE,
    )

    page_obj = paginator.get_page(
        request.GET.get("page"),
    )

    context = {
        **patient_navigation_context(),
        "page_obj": page_obj,
        "patients": page_obj.object_list,
        "query": query,
        "status": status,
        "selected_facility": facility_id,
    }

    template_name = (
        "patients/partials/patient_table.html"
        if is_htmx(request)
        else "patients/patient_list.html"
    )

    return render(
        request,
        template_name,
        context,
    )


@login_required
def patient_search(
    request: HttpRequest,
) -> HttpResponse:
    """
    Return patient-search dropdown results.
    """

    query = request.GET.get("q", "").strip()
    patients = Patient.objects.none()

    if len(query) >= 2:
        patients = (
            patient_queryset()
            .search(query)
            .exclude(
                record_status=Patient.RecordStatus.MERGED,
            )
            .exclude(
                record_status=Patient.RecordStatus.ENTERED_IN_ERROR,
            )
            .order_by(
                "last_name",
                "first_name",
                "date_of_birth",
            )[:PATIENT_SEARCH_LIMIT]
        )

    return render(
        request,
        "patients/partials/search_results.html",
        {
            "query": query,
            "patients": patients,
        },
    )


# ============================================================
# ============================================================
# PATIENT DETAIL AND SIDEBAR
# ============================================================

@login_required
def patient_detail(
    request: HttpRequest,
    patient_id,
) -> HttpResponse:
    """
    Display the selected patient's clinical overview.

    Patient history remains available without an encounter.
    Encounter-specific clinical actions are enabled only when the
    patient has an active, open encounter.
    """

    # ========================================================
    # PATIENT
    # ========================================================

    patient = get_object_or_404(
        patient_queryset(),
        pk=patient_id,
    )

    # ========================================================
    # ACTIVE PATIENT FLAGS
    # ========================================================

    active_flags = [
        flag
        for flag in patient.flags.all()
        if flag.currently_active
    ]

    # ========================================================
    # ACTIVE ALLERGIES
    # ========================================================

    allergies = (
        patient.allergies
        .filter(
            status=PatientAllergy.Status.ACTIVE,
        )
        .order_by(
            "-severity",
            "substance",
        )
    )

    # ========================================================
    # ACTIVE ENCOUNTER
    # ========================================================

    active_encounter = get_patient_active_encounter(
        patient,
    )

    # ========================================================
    # RECENT ENCOUNTERS
    # ========================================================

    recent_encounters = patient_recent_encounters(
        patient,
    )

    # ========================================================
    # DIAGNOSES
    #
    # Diagnosis integration can be added when the diagnosis
    # related_name and field names are confirmed.
    # ========================================================

    diagnoses = []

    # ========================================================
    # PAGE CONTEXT
    # ========================================================

    context = {
        **patient_navigation_context(
            patient=patient,
            subsection="overview",
            active_encounter=active_encounter,
        ),

        "patient": patient,
        "selected_patient": patient,

        "active_flags": active_flags,
        "allergies": allergies,

        "active_encounter": active_encounter,
        "recent_encounters": recent_encounters,

        "physicians": [],
        "diagnoses": diagnoses,
        "medications": [],
        "surgeries": [],
        "clinical_records": [],
    }

    # ========================================================
    # HTMX RESPONSE
    # ========================================================

    if request.headers.get("HX-Request") == "true":
        return render(
            request,
            "patients/partials/detail_content.html",
            context,
        )

    # ========================================================
    # FULL PAGE RESPONSE
    # ========================================================

    return render(
        request,
        "patients/patient_detail.html",
        context,
    )

@login_required
def patient_sidebar(
    request: HttpRequest,
    patient_id,
) -> HttpResponse:
    """
    Render the selected patient's sidebar.

    The active encounter is included so encounter-specific sidebar
    actions can be conditionally displayed.
    """

    patient = get_object_or_404(
        patient_queryset(),
        pk=patient_id,
    )

    active_encounter = get_patient_active_encounter(
        patient,
    )

    return render(
        request,
        "patients/partials/patient_sidebar.html",
        patient_navigation_context(
            patient=patient,
            active_encounter=active_encounter,
        ),
    )


@login_required
def patient_overview(
    request: HttpRequest,
    patient_id,
) -> HttpResponse:
    """
    Render the patient overview partial.
    """

    patient = get_object_or_404(
        patient_queryset(),
        pk=patient_id,
    )

    active_encounter = get_patient_active_encounter(
        patient,
    )

    active_flags = [
        flag
        for flag in patient.flags.all()
        if flag.currently_active
    ]

    allergies = (
        patient.allergies
        .filter(
            status=PatientAllergy.Status.ACTIVE,
        )
        .order_by(
            "-severity",
            "substance",
        )
    )

    context = {
        **patient_navigation_context(
            patient=patient,
            subsection="overview",
            active_encounter=active_encounter,
        ),
        "active_flags": active_flags,
        "allergies": allergies,
        "recent_encounters": patient_recent_encounters(patient),
        "physicians": [],
        "diagnoses": [],
        "medications": [],
        "surgeries": [],
        "clinical_records": [],
    }

    return render(
        request,
        "patients/partials/patient_overview.html",
        context,
    )


# ============================================================
# PATIENT ALLERGY QUERYSET
# ============================================================

def patient_allergy_queryset(
    patient: Patient,
):
    """
    Return all allergy records for a patient.

    Active records appear first, followed by severity and substance.
    """

    return (
        PatientAllergy.objects
        .filter(patient=patient)
        .order_by(
            "status",
            "-severity",
            "substance",
        )
    )


# ============================================================
# PATIENT ALLERGY CREATE
# ============================================================

@login_required
def patient_allergy_create(
    request: HttpRequest,
    patient_id,
) -> HttpResponse:
    """
    Display and process the add-allergy form.
    """

    patient = get_object_or_404(
        Patient,
        pk=patient_id,
    )

    if request.method == "POST":
        form = PatientAllergyForm(
            request.POST,
        )

        if form.is_valid():
            allergy = form.save(
                commit=False,
            )

            allergy.patient = patient
            allergy.created_by = request.user
            allergy.updated_by = request.user
            allergy.save()

            allergies = patient_allergy_queryset(
                patient,
            )

            response = render(
                request,
                "patients/partials/allergy_list.html",
                {
                    "patient": patient,
                    "selected_patient": patient,
                    "allergies": allergies,
                },
            )

            response["HX-Trigger"] = json.dumps(
                {
                    "patientAllergySaved": {
                        "message": (
                            f"{allergy.substance} was added successfully."
                        ),
                    },
                }
            )

            return response

        response = render(
            request,
            "patients/partials/allergy_form.html",
            {
                "patient": patient,
                "selected_patient": patient,
                "form": form,
                "form_mode": "create",
                "allergy": None,
            },
        )

        response["HX-Retarget"] = (
            "#patient-allergy-modal-content"
        )
        response["HX-Reswap"] = "innerHTML"

        return response

    form = PatientAllergyForm()

    return render(
        request,
        "patients/partials/allergy_form.html",
        {
            "patient": patient,
            "selected_patient": patient,
            "form": form,
            "form_mode": "create",
            "allergy": None,
        },
    )


# ============================================================
# PATIENT ALLERGY UPDATE
# ============================================================

@login_required
def patient_allergy_update(
    request: HttpRequest,
    patient_id,
    allergy_id: int,
) -> HttpResponse:
    """
    Display and process the update-allergy form.
    """

    patient = get_object_or_404(
        Patient,
        pk=patient_id,
    )

    allergy = get_object_or_404(
        PatientAllergy,
        pk=allergy_id,
        patient=patient,
    )

    if request.method == "POST":
        form = PatientAllergyForm(
            request.POST,
            instance=allergy,
        )

        if form.is_valid():
            allergy = form.save(
                commit=False,
            )

            allergy.updated_by = request.user
            allergy.save()

            allergies = patient_allergy_queryset(
                patient,
            )

            response = render(
                request,
                "patients/partials/allergy_list.html",
                {
                    "patient": patient,
                    "selected_patient": patient,
                    "allergies": allergies,
                },
            )

            response["HX-Trigger"] = json.dumps(
                {
                    "patientAllergySaved": {
                        "message": (
                            f"{allergy.substance} was updated successfully."
                        ),
                    },
                }
            )

            return response

        response = render(
            request,
            "patients/partials/allergy_form.html",
            {
                "patient": patient,
                "selected_patient": patient,
                "form": form,
                "form_mode": "update",
                "allergy": allergy,
            },
        )

        response["HX-Retarget"] = (
            "#patient-allergy-modal-content"
        )
        response["HX-Reswap"] = "innerHTML"

        return response

    form = PatientAllergyForm(
        instance=allergy,
    )

    return render(
        request,
        "patients/partials/allergy_form.html",
        {
            "patient": patient,
            "selected_patient": patient,
            "form": form,
            "form_mode": "update",
            "allergy": allergy,
        },
    )


# ============================================================
# PATIENT CREATE AND UPDATE
# ============================================================

class PatientCreateView(
    LoginRequiredMixin,
    CreateView,
):
    """
    Create a new patient record.

    Standard requests render the complete patient form page.
    HTMX requests render only the form partial.
    """

    model = Patient
    form_class = PatientForm
    template_name = "patients/patient_form.html"
    partial_template_name = (
        "patients/partials/patient_form.html"
    )

    def get_template_names(self):
        """
        Return the full or partial form template.
        """

        if is_htmx(self.request):
            return [self.partial_template_name]

        return [self.template_name]

    def get_context_data(self, **kwargs):
        """
        Add navigation and create-mode context.
        """

        context = super().get_context_data(**kwargs)

        context.update(
            patient_navigation_context(
                subsection="registration",
            )
        )

        context["form_mode"] = "create"

        return context

    @transaction.atomic
    def form_valid(self, form):
        """
        Save the patient and audit users.
        """

        patient = form.save(
            commit=False,
        )

        patient.created_by = self.request.user
        patient.updated_by = self.request.user

        patient.save()
        form.save_m2m()

        self.object = patient

        detail_url = reverse(
            "patients:detail",
            kwargs={
                "patient_id": patient.pk,
            },
        )

        if is_htmx(self.request):
            return trigger_response(
                "patientCreated",
                redirect_url=detail_url,
                payload={
                    "patientId": str(patient.pk),
                    "mrn": patient.mrn,
                },
            )

        return redirect(detail_url)

    def form_invalid(self, form):
        """
        Return validation errors.
        """

        context = self.get_context_data(
            form=form,
        )

        response = render(
            self.request,
            self.get_template_names()[0],
            context,
        )

        if is_htmx(self.request):
            response.status_code = 422

        return response


class PatientUpdateView(
    LoginRequiredMixin,
    UpdateView,
):
    """
    Update an existing patient record.
    """

    model = Patient
    form_class = PatientForm
    pk_url_kwarg = "patient_id"
    template_name = "patients/patient_form.html"
    partial_template_name = (
        "patients/partials/patient_form.html"
    )

    def get_queryset(self):
        """
        Use the shared patient queryset.
        """

        return patient_queryset()

    def get_template_names(self):
        """
        Return the full or partial form template.
        """

        if is_htmx(self.request):
            return [self.partial_template_name]

        return [self.template_name]

    def get_context_data(self, **kwargs):
        """
        Add selected-patient and update-mode context.
        """

        context = super().get_context_data(**kwargs)

        active_encounter = get_patient_active_encounter(
            self.object,
        )

        context.update(
            patient_navigation_context(
                patient=self.object,
                subsection="registration",
                active_encounter=active_encounter,
            )
        )

        context["form_mode"] = "update"

        return context

    @transaction.atomic
    def form_valid(self, form):
        """
        Save patient changes and audit the updater.
        """

        patient = form.save(
            commit=False,
        )

        patient.updated_by = self.request.user

        patient.save()
        form.save_m2m()

        self.object = patient

        detail_url = reverse(
            "patients:detail",
            kwargs={
                "patient_id": patient.pk,
            },
        )

        if is_htmx(self.request):
            return trigger_response(
                "patientUpdated",
                redirect_url=detail_url,
                payload={
                    "patientId": str(patient.pk),
                    "mrn": patient.mrn,
                },
            )

        return redirect(detail_url)

    def form_invalid(self, form):
        """
        Return validation errors.
        """

        context = self.get_context_data(
            form=form,
        )

        response = render(
            self.request,
            self.get_template_names()[0],
            context,
        )

        if is_htmx(self.request):
            response.status_code = 422

        return response


# ============================================================
# PATIENT ARCHIVE / RECORD STATUS
# ============================================================

class PatientArchiveView(
    LoginRequiredMixin,
    View,
):
    """
    Soft-deactivate a patient instead of deleting the record.
    """

    template_name = (
        "patients/patient_confirm_delete.html"
    )

    partial_template_name = (
        "patients/partials/patient_confirm_delete.html"
    )

    def get_object(self, patient_id):
        """
        Retrieve the patient.
        """

        return get_object_or_404(
            patient_queryset(),
            pk=patient_id,
        )

    def get(
        self,
        request: HttpRequest,
        patient_id,
    ) -> HttpResponse:
        """
        Display archive confirmation.
        """

        patient = self.get_object(
            patient_id,
        )

        template_name = (
            self.partial_template_name
            if is_htmx(request)
            else self.template_name
        )

        return render(
            request,
            template_name,
            {
                **patient_navigation_context(
                    patient=patient,
                ),
                "archive_mode": True,
            },
        )

    @transaction.atomic
    def post(
        self,
        request: HttpRequest,
        patient_id,
    ) -> HttpResponse:
        """
        Archive the patient record.
        """

        patient = self.get_object(
            patient_id,
        )

        reason = request.POST.get(
            "archive_reason",
            "",
        ).strip()

        if not reason:
            return HttpResponseBadRequest(
                "An archive reason is required."
            )

        patient.record_status = (
            Patient.RecordStatus.INACTIVE
        )
        patient.is_active = False
        patient.updated_by = request.user

        note = (
            f"Record deactivated by {request.user} "
            f"on {request.POST.get('archive_date', 'today')}. "
            f"Reason: {reason}"
        )

        if patient.registration_notes:
            patient.registration_notes = (
                f"{patient.registration_notes}\n\n{note}"
            )
        else:
            patient.registration_notes = note

        patient.save()

        list_url = reverse(
            "patients:list",
        )

        if is_htmx(request):
            return trigger_response(
                "patientArchived",
                redirect_url=list_url,
                payload={
                    "patientId": str(patient.pk),
                },
            )

        return redirect(list_url)


class PatientRestoreView(
    LoginRequiredMixin,
    View,
):
    """
    Restore an inactive patient record.
    """

    @transaction.atomic
    def post(
        self,
        request: HttpRequest,
        patient_id,
    ) -> HttpResponse:
        """
        Restore an eligible inactive record.
        """

        patient = get_object_or_404(
            patient_queryset(),
            pk=patient_id,
        )

        if patient.record_status in {
            Patient.RecordStatus.MERGED,
            Patient.RecordStatus.ENTERED_IN_ERROR,
        }:
            return HttpResponseBadRequest(
                "Merged and entered-in-error records cannot "
                "be restored using this action."
            )

        if patient.is_deceased:
            return HttpResponseBadRequest(
                "A deceased patient cannot be restored as active."
            )

        patient.record_status = (
            Patient.RecordStatus.ACTIVE
        )
        patient.is_active = True
        patient.updated_by = request.user
        patient.save()

        detail_url = reverse(
            "patients:detail",
            kwargs={
                "patient_id": patient.pk,
            },
        )

        if is_htmx(request):
            return trigger_response(
                "patientRestored",
                redirect_url=detail_url,
            )

        return redirect(detail_url)


# ============================================================
# GENERIC PATIENT CHILD RECORD CONFIGURATION
# ============================================================

CHILD_CONFIG = {
    "identifier": {
        "model": PatientIdentifier,
        "form": PatientIdentifierForm,
        "related_name": "identifiers",
        "label": "Identifier",
    },
    "alias": {
        "model": PatientAlias,
        "form": PatientAliasForm,
        "related_name": "aliases",
        "label": "Alias",
    },
    "address": {
        "model": PatientAddress,
        "form": PatientAddressForm,
        "related_name": "addresses",
        "label": "Address",
    },
    "contact": {
        "model": PatientContactPoint,
        "form": PatientContactPointForm,
        "related_name": "contact_points",
        "label": "Contact",
    },
    "emergency-contact": {
        "model": EmergencyContact,
        "form": EmergencyContactForm,
        "related_name": "emergency_contacts",
        "label": "Emergency contact",
    },
    "relationship": {
        "model": PatientRelationship,
        "form": PatientRelationshipForm,
        "related_name": "relationships_from",
        "label": "Relationship",
    },
    "consent": {
        "model": PatientConsent,
        "form": PatientConsentForm,
        "related_name": "consents",
        "label": "Consent",
    },
    "insurance": {
        "model": InsuranceCoverage,
        "form": InsuranceCoverageForm,
        "related_name": "insurance_coverages",
        "label": "Insurance coverage",
    },
    "flag": {
        "model": PatientFlag,
        "form": PatientFlagForm,
        "related_name": "flags",
        "label": "Patient flag",
    },
}


def child_config(
    kind: str,
) -> dict:
    """
    Return configuration for a child-record type.
    """

    try:
        return CHILD_CONFIG[kind]
    except KeyError as exc:
        raise Http404(
            "Unsupported patient record type."
        ) from exc


# ============================================================
# GENERIC PATIENT CHILD RECORD LIST
# ============================================================

@login_required
def patient_child_list(
    request: HttpRequest,
    patient_id,
    kind: str,
) -> HttpResponse:
    """
    Display a patient's child records.
    """

    patient = get_object_or_404(
        patient_queryset(),
        pk=patient_id,
    )

    config = child_config(
        kind,
    )

    records = getattr(
        patient,
        config["related_name"],
    ).all()

    return render(
        request,
        "patients/partials/child_list.html",
        {
            **patient_navigation_context(
                patient=patient,
                subsection=kind,
            ),
            "records": records,
            "kind": kind,
            "model_name": config["label"],
        },
    )


# ============================================================
# GENERIC PATIENT CHILD RECORD CREATE
# ============================================================

@login_required
def patient_child_create(
    request: HttpRequest,
    patient_id,
    kind: str,
) -> HttpResponse:
    """
    Create a patient child record.
    """

    patient = get_object_or_404(
        patient_queryset(),
        pk=patient_id,
    )

    config = child_config(
        kind,
    )

    form_class = config["form"]

    form = form_class(
        request.POST or None,
        request.FILES or None,
    )

    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            record = form.save(
                commit=False,
            )

            record.patient = patient

            if hasattr(record, "created_by_id"):
                record.created_by = request.user

            if hasattr(record, "updated_by_id"):
                record.updated_by = request.user

            record.save()

            if hasattr(form, "save_m2m"):
                form.save_m2m()

        if is_htmx(request):
            return trigger_response(
                "patientChildSaved",
                payload={
                    "kind": kind,
                    "recordId": str(record.pk),
                    "patientId": str(patient.pk),
                },
            )

        return redirect(
            "patients:detail",
            patient_id=patient.pk,
        )

    template_name = (
        "patients/partials/child_form.html"
        if is_htmx(request)
        else "patients/child_form.html"
    )

    return render(
        request,
        template_name,
        {
            **patient_navigation_context(
                patient=patient,
                subsection=kind,
            ),
            "form": form,
            "kind": kind,
            "record": None,
            "model_name": config["label"],
        },
    )


# ============================================================
# GENERIC PATIENT CHILD RECORD UPDATE
# ============================================================

@login_required
def patient_child_update(
    request: HttpRequest,
    patient_id,
    kind: str,
    record_id: int,
) -> HttpResponse:
    """
    Update a patient child record.
    """

    patient = get_object_or_404(
        patient_queryset(),
        pk=patient_id,
    )

    config = child_config(
        kind,
    )

    model_class = config["model"]
    form_class = config["form"]

    record = get_object_or_404(
        model_class,
        pk=record_id,
        patient=patient,
    )

    form = form_class(
        request.POST or None,
        request.FILES or None,
        instance=record,
    )

    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            record = form.save(
                commit=False,
            )

            if hasattr(record, "updated_by_id"):
                record.updated_by = request.user

            record.save()

            if hasattr(form, "save_m2m"):
                form.save_m2m()

        if is_htmx(request):
            return trigger_response(
                "patientChildSaved",
                payload={
                    "kind": kind,
                    "recordId": str(record.pk),
                    "patientId": str(patient.pk),
                },
            )

        return redirect(
            "patients:detail",
            patient_id=patient.pk,
        )

    template_name = (
        "patients/partials/child_form.html"
        if is_htmx(request)
        else "patients/child_form.html"
    )

    return render(
        request,
        template_name,
        {
            **patient_navigation_context(
                patient=patient,
                subsection=kind,
            ),
            "form": form,
            "kind": kind,
            "record": record,
            "model_name": config["label"],
        },
    )


# ============================================================
# GENERIC PATIENT CHILD RECORD DELETE
# ============================================================

@login_required
def patient_child_delete(
    request: HttpRequest,
    patient_id,
    kind: str,
    record_id: int,
) -> HttpResponse:
    """
    Delete a patient child record.
    """

    patient = get_object_or_404(
        patient_queryset(),
        pk=patient_id,
    )

    config = child_config(
        kind,
    )

    model_class = config["model"]

    record = get_object_or_404(
        model_class,
        pk=record_id,
        patient=patient,
    )

    if request.method == "POST":
        with transaction.atomic():
            record.delete()

        if is_htmx(request):
            return trigger_response(
                "patientChildDeleted",
                payload={
                    "kind": kind,
                    "recordId": str(record_id),
                    "patientId": str(patient.pk),
                },
            )

        return redirect(
            "patients:detail",
            patient_id=patient.pk,
        )

    template_name = (
        "patients/partials/child_confirm_delete.html"
        if is_htmx(request)
        else "patients/child_confirm_delete.html"
    )

    return render(
        request,
        template_name,
        {
            **patient_navigation_context(
                patient=patient,
                subsection=kind,
            ),
            "record": record,
            "kind": kind,
            "model_name": config["label"],
        },
    )


# ============================================================
# FLAG ACKNOWLEDGMENT
# ============================================================

@login_required
@transaction.atomic
def patient_flag_acknowledge(
    request: HttpRequest,
    patient_id,
    flag_id: int,
) -> HttpResponse:
    """
    Acknowledge a patient safety or clinical flag.
    """

    if request.method != "POST":
        return HttpResponseBadRequest(
            "Flag acknowledgment requires POST."
        )

    patient = get_object_or_404(
        Patient,
        pk=patient_id,
    )

    flag = get_object_or_404(
        PatientFlag,
        pk=flag_id,
        patient=patient,
    )

    acknowledgment, created = (
        PatientFlagAcknowledgment.objects.get_or_create(
            flag=flag,
            acknowledged_by=request.user,
            defaults={
                "notes": request.POST.get(
                    "notes",
                    "",
                ).strip(),
            },
        )
    )

    if not created:
        acknowledgment.notes = request.POST.get(
            "notes",
            acknowledgment.notes,
        ).strip()

        acknowledgment.save(
            update_fields=[
                "notes",
                "updated_at",
            ]
        )

    if is_htmx(request):
        return trigger_response(
            "patientFlagAcknowledged",
            payload={
                "flagId": flag.pk,
                "patientId": str(patient.pk),
            },
        )

    return redirect(
        "patients:detail",
        patient_id=patient.pk,
    )


# ============================================================
# PATIENT MERGE WORKFLOW
# ============================================================

@login_required
def patient_merge_review(
    request: HttpRequest,
    patient_id,
) -> HttpResponse:
    """
    Display merge history involving the selected patient.
    """

    patient = get_object_or_404(
        patient_queryset(),
        pk=patient_id,
    )

    merge_records = (
        PatientMergeRecord.objects
        .filter(
            Q(surviving_patient=patient)
            | Q(duplicate_patient=patient)
        )
        .select_related(
            "surviving_patient",
            "duplicate_patient",
            "reviewed_by",
        )
        .order_by(
            "-created_at",
        )
    )

    return render(
        request,
        "patients/patient_merge_review.html",
        {
            **patient_navigation_context(
                patient=patient,
                subsection="merge",
            ),
            "merge_records": merge_records,
        },
    )