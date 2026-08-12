from __future__ import annotations

import json
from datetime import timedelta
from typing import Any

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q, QuerySet
from django.http import HttpRequest, HttpResponse
from django.shortcuts import (
    get_object_or_404,
    redirect,
    render,
)
from django.urls import reverse
from django.utils import timezone

from apps.encounters.models import Encounter
from apps.orders.models import MedicationOrder
from apps.patients.models import Patient

from .forms import MedicationAdministrationForm
from .models import MedicationAdministration

# ============================================================

# CONSTANTS

# ============================================================

GLOBAL_LIST_LIMIT = 100

MAR_DUE_WINDOW = timedelta(hours=1)
MAR_REASON_WINDOW = timedelta(hours=3)

MAR_FREQUENCY_INTERVALS = {
    MedicationOrder.Frequency.DAILY: timedelta(days=1),
    MedicationOrder.Frequency.BID: timedelta(hours=12),
    MedicationOrder.Frequency.TID: timedelta(hours=8),
    MedicationOrder.Frequency.QID: timedelta(hours=6),
    MedicationOrder.Frequency.Q4H: timedelta(hours=4),
    MedicationOrder.Frequency.Q6H: timedelta(hours=6),
    MedicationOrder.Frequency.Q8H: timedelta(hours=8),
    MedicationOrder.Frequency.Q12H: timedelta(hours=12),
    MedicationOrder.Frequency.Q24H: timedelta(hours=24),
    MedicationOrder.Frequency.QAM: timedelta(days=1),
    MedicationOrder.Frequency.QPM: timedelta(days=1),
    MedicationOrder.Frequency.QHS: timedelta(days=1),
    MedicationOrder.Frequency.AC: timedelta(hours=8),
    MedicationOrder.Frequency.PC: timedelta(hours=8),
    MedicationOrder.Frequency.AC_HS: timedelta(hours=6),
    MedicationOrder.Frequency.WEEKLY: timedelta(days=7),
}


def _normalized_frequency(order: MedicationOrder) -> str:
    return str(order.frequency or "").strip().lower()


def _order_is_prn(order: MedicationOrder) -> bool:
    return "prn" in _normalized_frequency(order).split()

# ============================================================

# SHARED CONTEXT

# ============================================================

def medication_context(

    *,

    section: str,

    selected_patient: Patient | None = None,

    active_encounter: Encounter | None = None,

) -> dict[str, Any]:

    return {

        "active_primary_nav": "clinical",

        "active_clinical_module": "medications",

        "active_clinical_section": section,

        "selected_patient": selected_patient,

        "active_encounter": active_encounter,

    }

# ============================================================

# HELPERS

# ============================================================

def get_active_patient_encounter(

    patient: Patient,

) -> Encounter | None:

    return (

        Encounter.objects

        .filter(

            patient=patient,

            is_active=True,

        )

        .order_by(

            "-start_datetime",

            "-pk",

        )

        .first()

    )

def medication_order_queryset() -> QuerySet[MedicationOrder]:

    return (

        MedicationOrder.objects

        .select_related(

            "patient",

            "encounter",

            "medication",

            "ordered_by",

        )

    )

def administration_queryset() -> QuerySet[MedicationAdministration]:

    return (

        MedicationAdministration.objects

        .select_related(

            "patient",

            "encounter",

            "medication",

            "medication_order",

            "medication_order__medication",

            "administered_by",

            "witnessed_by",

        )

    )

def _status_value(

    *names: str,

    fallback: str,

) -> str:

    """

    Resolve a MedicationAdministration.Status value without

    hard-coding one exact TextChoices member name.

    This allows the MAR to support model choices such as:

    ADMINISTERED, HELD, OMITTED, NOT_GIVEN, REFUSED, etc.

    """

    status_class = MedicationAdministration.Status

    for name in names:

        member = getattr(

            status_class,

            name,

            None,

        )

        if member is not None:

            return member.value

    available_values = {

        value

        for value, _label

        in status_class.choices

    }

    if fallback in available_values:

        return fallback

    return fallback

def _administered_status() -> str:

    return _status_value(

        "ADMINISTERED",

        "GIVEN",

        fallback="administered",

    )

def _held_status() -> str:

    return _status_value(

        "HELD",

        "HOLD",

        fallback="held",

    )

def _not_given_status() -> str:

    """

    Prefer a general not-given/omitted state.

    Refused should only be used as the fallback if the current

    model has no broader not-given state.

    """

    return _status_value(

        "NOT_GIVEN",

        "OMITTED",

        "MISSED",

        "REFUSED",

        fallback="refused",

    )

def _order_dose_text(

    order: MedicationOrder,

) -> str:

    dose = str(

        order.dose or ""

    ).strip()

    dose_unit = str(

        order.dose_unit or ""

    ).strip()

    if dose and dose_unit:

        return f"{dose} {dose_unit}"

    return dose or dose_unit

def _order_route_text(

    order: MedicationOrder,

) -> str:

    route = str(

        order.route or ""

    ).strip()

    if route:

        return route

    medication_route = str(

        getattr(

            order.medication,

            "route",

            "",

        )

        or ""

    ).strip()

    return medication_route

def _create_mar_event(

    *,

    request: HttpRequest,

    encounter: Encounter,

    patient: Patient,

    order: MedicationOrder,

    status: str,

    reason: str = "",
    notes: str = "",

) -> MedicationAdministration:

    """

    Create an auditable MAR event.

    The event time always comes from the Django server.

    For an administered medication:

    - administered_at is the exact Give time.

    - dose and route are copied from the provider order.

    For held/not-given:

    - the same timestamp records when the MAR exception

      was documented.

    """

    now = timezone.now()

    administration = MedicationAdministration(

        patient=patient,

        encounter=encounter,

        medication_order=order,

        medication=order.medication,

        dose_administered=_order_dose_text(

            order

        ),

        route=_order_route_text(

            order

        ),

        status=status,

        administered_at=now,

        administered_by=request.user,

        reason=reason.strip(),
        notes=notes.strip(),

    )

    # If the model supports scheduled_at and the order has a

    # calculated next_due_at attribute, preserve the scheduled

    # medication time separately from the actual Give time.

    next_due_at = getattr(

        order,

        "next_due_at",

        None,

    )

    if next_due_at is not None:

        administration.scheduled_at = (

            next_due_at

        )

    administration.full_clean()

    administration.save()

    if (
        status == _administered_status()
        and _normalized_frequency(order)
        in {
            MedicationOrder.Frequency.ONCE,
            MedicationOrder.Frequency.STAT,
        }
        and order.status == MedicationOrder.Status.ACTIVE
    ):
        order.status = MedicationOrder.Status.COMPLETED
        order.save(update_fields=["status", "updated_at"])

    return administration


def _attach_next_due_times(
    *,
    medication_orders: list[MedicationOrder],
    administrations: list[MedicationAdministration],
) -> None:
    """Attach the next scheduled dose time used by both the MAR UI and saves."""
    latest_by_order: dict[object, MedicationAdministration] = {}
    administered_status = _administered_status()

    for administration in administrations:
        if administration.status != administered_status:
            continue
        if (
            administration.medication_order_id
            and administration.medication_order_id not in latest_by_order
        ):
            latest_by_order[administration.medication_order_id] = administration

    for order in medication_orders:
        order.next_due_at = None
        order.is_prn = _order_is_prn(order)
        if order.is_prn:
            continue

        latest = latest_by_order.get(order.pk)
        frequency = _normalized_frequency(order)
        interval = MAR_FREQUENCY_INTERVALS.get(frequency)

        if latest and interval:
            # A completed administration starts a fresh medication cycle.
            # Anchor recurrence to the actual bedside administration time,
            # not the old scheduled slot, so the row cannot remain red/due
            # immediately after it has been recorded.
            next_due_at = latest.administered_at + interval

            if order.stop_date and next_due_at.date() > order.stop_date:
                order.next_due_at = None
            else:
                order.next_due_at = next_due_at
        elif latest and frequency in {
            MedicationOrder.Frequency.ONCE,
            MedicationOrder.Frequency.STAT,
        }:
            order.next_due_at = None
        else:
            order.next_due_at = order.start_datetime or order.ordered_at


def _mar_timing_status(order: MedicationOrder, now) -> str:
    if _order_is_prn(order):
        return "prn"
    if not order.next_due_at:
        return "scheduled"

    difference = order.next_due_at - now
    if difference < -MAR_DUE_WINDOW:
        return "overdue"
    if difference <= MAR_DUE_WINDOW:
        return "due"
    return "scheduled"


def _order_is_administerable(order: MedicationOrder, now) -> bool:
    return order.status == MedicationOrder.Status.ACTIVE and (
        _order_is_prn(order)
        or order.next_due_at is not None
    )


def _order_requires_timing_reason(order: MedicationOrder, now) -> bool:
    if _order_is_prn(order):
        return False
    if not order.next_due_at:
        return True
    difference = order.next_due_at - now
    return difference > MAR_DUE_WINDOW or abs(difference) > MAR_REASON_WINDOW

def _attach_last_administrations(

    *,

    medication_orders,

    administrations,

) -> None:

    """

    Attach the latest successfully administered event to each

    MedicationOrder as order.last_administration.

    This powers the MAR "Last Given" column.

    """

    administered_status = (

        _administered_status()

    )

    latest_by_order: dict[

        object,

        MedicationAdministration,

    ] = {}

    for administration in administrations:

        if (

            administration.status

            != administered_status

        ):

            continue

        order_id = (

            administration

            .medication_order_id

        )

        if not order_id:

            continue

        if order_id not in latest_by_order:

            latest_by_order[

                order_id

            ] = administration

    for order in medication_orders:

        order.last_administration = (

            latest_by_order.get(

                order.pk

            )

        )


def _compact_administration_history(

    administrations: list[MedicationAdministration],

) -> list[MedicationAdministration]:

    """Return one alphabetical row per medicine with its complete history."""

    grouped: dict[object, list[MedicationAdministration]] = {}

    for administration in administrations:

        medication_id = (

            administration.medication_id

            or getattr(

                administration.medication_order,

                "medication_id",

                None,

            )

            or administration.pk

        )

        grouped.setdefault(

            medication_id,

            [],

        ).append(administration)

    compact_history: list[MedicationAdministration] = []

    for medication_events in grouped.values():

        first_event = medication_events[0]

        first_event.history_events = medication_events

        first_event.history_event_count = len(medication_events)

        compact_history.append(first_event)

    compact_history.sort(

        key=lambda event: (
            (
                getattr(event.medication, "display_name", "")
                or getattr(
                    getattr(event.medication_order, "medication", None),
                    "display_name",
                    "",
                )
                or "Medication unavailable"
            ).casefold(),
            str(event.pk),
        ),

    )

    return compact_history

# ============================================================

# DASHBOARD

# ============================================================

@login_required

def dashboard(

    request: HttpRequest,

) -> HttpResponse:

    return redirect(

        "medications:list"

    )

# ============================================================

# GLOBAL MEDICATION ACTIVITY

# ============================================================

@login_required

def medication_list(

    request: HttpRequest,

) -> HttpResponse:

    # Medication records are patient-specific clinical data. Require the
    # clinician to establish patient context through the shared search bar
    # instead of exposing a cross-patient activity list from Clinical.
    messages.info(
        request,
        "Search for and select a patient before opening Medications.",
    )
    return redirect("patients:list")

    # Retained below temporarily for reference while downstream reporting is
    # moved to a permissioned analytics workflow.

    query = (

        request.GET.get("q")

        or ""

    ).strip()

    medication_orders = (

        medication_order_queryset()

    )

    administrations = (

        administration_queryset()

    )

    if query:

        medication_orders = (

            medication_orders.filter(

                Q(

                    medication__generic_name__icontains=query

                )

                |

                Q(

                    medication__brand_name__icontains=query

                )

                |

                Q(

                    medication__code__icontains=query

                )

                |

                Q(

                    patient__mrn__icontains=query

                )

            )

        )

        administrations = (

            administrations.filter(

                Q(

                    medication__generic_name__icontains=query

                )

                |

                Q(

                    medication__brand_name__icontains=query

                )

                |

                Q(

                    medication__code__icontains=query

                )

                |

                Q(

                    medication_order__medication__generic_name__icontains=query

                )

                |

                Q(

                    medication_order__medication__brand_name__icontains=query

                )

                |

                Q(

                    patient__mrn__icontains=query

                )

            )

        )

    medication_orders = (

        medication_orders

        .order_by(

            "-ordered_at"

        )[:GLOBAL_LIST_LIMIT]

    )

    administrations = (

        administrations

        .order_by(

            "-administered_at",

            "-pk",

        )[:GLOBAL_LIST_LIMIT]

    )

    context = medication_context(

        section="list"

    )

    context.update(

        {

            "medication_orders":

                medication_orders,

            "administrations":

                administrations,

            "search_query":

                query,

        }

    )

    return render(

        request,

        "medications/medication_list.html",

        context,

    )

# ============================================================

# PATIENT MEDICATION RECORD

# ============================================================

@login_required

def patient_medication_list(

    request: HttpRequest,

    patient_id,

) -> HttpResponse:

    patient = get_object_or_404(

        Patient,

        pk=patient_id,

    )

    active_encounter = (

        get_active_patient_encounter(

            patient

        )

    )

    medication_orders = (

        medication_order_queryset()

        .filter(

            patient=patient,

        )

        .order_by(

            "-ordered_at"

        )

    )

    administrations = (

        administration_queryset()

        .filter(

            patient=patient,

        )

        .order_by(

            "-administered_at",

            "-pk",

        )

    )

    context = medication_context(

        section="list",

        selected_patient=patient,

        active_encounter=active_encounter,

    )

    context.update(

        {

            "medication_orders":

                medication_orders,

            "administrations":

                administrations,

        }

    )

    return render(

        request,

        "medications/medication_list.html",

        context,

    )

# ============================================================

# MAR

# ============================================================

@login_required

def medication_administration_record(

    request: HttpRequest,

    encounter_id,

) -> HttpResponse:

    """

    Interactive Medication Administration Record.

    Supported MAR actions:

    give_selected

        Atomically creates ADMINISTERED events for every staged
        active medication order.

    give

        Immediately creates an ADMINISTERED event using

        timezone.now().

    not_given

        Creates a non-administration event and requires

        documentation of the reason.

    hold

        Creates a HELD MAR event and requires a hold reason.

    The medication, patient, encounter, dose, and route are

    derived from the provider's MedicationOrder rather than

    trusted from browser-submitted values.

    """

    encounter = get_object_or_404(

        Encounter.objects

        .select_related(

            "patient",

        ),

        pk=encounter_id,

    )

    patient = encounter.patient

    # ========================================================

    # CLOSED ENCOUNTER

    # ========================================================

    if not encounter.is_open:

        messages.error(

            request,

            (

                "Medication administrations "

                "can only be recorded for "

                "an open encounter."

            ),

        )

        return redirect(

            "medications:patient-list",

            patient_id=patient.pk,

        )

    # ========================================================

    # MEDICATION ORDERS

    # ========================================================

    medication_orders = list(

        medication_order_queryset()

        .filter(

            encounter=encounter,

            patient=patient,

            status__in=(
                MedicationOrder.Status.ACTIVE,
                MedicationOrder.Status.ON_HOLD,
            ),

        )

        .order_by(

            "ordered_at",

            "pk",

        )

    )

    administrations = list(
        administration_queryset()
        .filter(encounter=encounter)
        .order_by("-administered_at", "-pk")
    )

    _attach_next_due_times(
        medication_orders=medication_orders,
        administrations=administrations,
    )

    now = timezone.now()
    status_priority = {"overdue": 0, "due": 1, "scheduled": 2, "prn": 3}
    medication_orders.sort(
        key=lambda order: (
            status_priority.get(_mar_timing_status(order, now), 4),
            order.next_due_at or order.ordered_at,
            str(order.pk),
        )
    )

    # ========================================================

    # MAR ACTION POST

    # ========================================================

    if request.method == "POST":

        mar_action = (

            request.POST.get(

                "mar_action"

            )

            or ""

        ).strip().lower()

        # ----------------------------------------------------

        # NEW COMPACT MAR ACTIONS

        # ----------------------------------------------------

        if mar_action in {"resume_order", "discontinue_order"}:
            order = get_object_or_404(
                medication_order_queryset(),
                pk=request.POST.get("medication_order"),
                encounter=encounter,
                patient=patient,
            )
            if (
                mar_action == "resume_order"
                and order.status == MedicationOrder.Status.ON_HOLD
            ):
                order.status = MedicationOrder.Status.ACTIVE
                message = "Medication order resumed."
            elif (
                mar_action == "discontinue_order"
                and order.status
                in {MedicationOrder.Status.ACTIVE, MedicationOrder.Status.ON_HOLD}
            ):
                provider_id = request.POST.get("discontinuation_ordered_by")
                method = request.POST.get("discontinuation_order_method", "")
                reason = request.POST.get("discontinuation_reason", "").strip()
                valid_methods = {
                    value for value, _ in MedicationOrder.OrderMethod.choices
                }
                if not provider_id or method not in valid_methods or not reason:
                    messages.error(
                        request,
                        "Provider, order medium, and reason are required.",
                    )
                    return redirect("medications:mar", encounter_id=encounter.pk)
                provider = get_object_or_404(
                    get_user_model(), pk=provider_id, is_active=True
                )
                order.status = MedicationOrder.Status.DISCONTINUED
                order.discontinued_at = timezone.now()
                order.discontinued_by = request.user
                order.discontinuation_ordered_by = provider
                order.discontinuation_order_method = method
                order.discontinuation_received_by = (
                    request.user if method in {"verbal", "telephone"} else None
                )
                order.discontinuation_reason = reason
                order.save()
                messages.success(
                    request, "Medication discontinuation order recorded."
                )
                return redirect("medications:mar", encounter_id=encounter.pk)
            else:
                messages.error(
                    request, "That medication order status change is not allowed."
                )
                return redirect("medications:mar", encounter_id=encounter.pk)

            order.save(update_fields=["status", "updated_at"])
            messages.success(request, message)
            return redirect("medications:mar", encounter_id=encounter.pk)

        if mar_action == "give_selected":

            try:
                timing_reasons = json.loads(
                    request.POST.get("timing_reasons") or "{}"
                )
            except (TypeError, ValueError):
                timing_reasons = {}

            if not isinstance(timing_reasons, dict):
                timing_reasons = {}

            medication_order_ids = list(

                dict.fromkeys(

                    request.POST.getlist(

                        "medication_orders"

                    )

                )

            )

            if not medication_order_ids:

                messages.error(

                    request,

                    "Select at least one medication to record.",

                )

            else:

                try:

                    with transaction.atomic():

                        selected_orders = list(

                            medication_order_queryset()

                            .select_for_update()

                            .filter(

                                pk__in=medication_order_ids,

                                encounter=encounter,

                                patient=patient,

                                status=MedicationOrder.Status.ACTIVE,

                            )

                        )

                        if (

                            len(selected_orders)

                            != len(medication_order_ids)

                        ):

                            raise ValueError(

                                "One or more selected medication orders "

                                "are invalid or no longer active."

                            )

                        _attach_next_due_times(
                            medication_orders=selected_orders,
                            administrations=administrations,
                        )

                        missing_timing_reasons = [
                            order.medication.display_name
                            for order in selected_orders
                            if _order_requires_timing_reason(
                                order, timezone.now()
                            )
                            and not str(
                                timing_reasons.get(str(order.pk), "")
                            ).strip()
                        ]

                        if missing_timing_reasons:
                            raise ValueError(
                                "Document the early or delayed administration "
                                "reason for: "
                                + ", ".join(missing_timing_reasons)
                            )

                        for order in selected_orders:

                            _create_mar_event(

                                request=request,

                                encounter=encounter,

                                patient=patient,

                                order=order,

                                status=_administered_status(),

                                notes=str(
                                    timing_reasons.get(str(order.pk), "")
                                ).strip(),

                            )

                except (ValidationError, ValueError) as error:

                    messages.error(

                        request,

                        str(error),

                    )

                else:

                    messages.success(

                        request,

                        (

                            f"{len(selected_orders)} medication "

                            f"record{'s' if len(selected_orders) != 1 else ''} "

                            "created successfully."

                        ),

                    )

            return redirect(

                reverse(

                    "medications:mar",

                    kwargs={

                        "encounter_id": encounter.pk,

                    },

                )

            )

        if mar_action in {

            "give",

            "not_given",

            "hold",

        }:

            medication_order_id = (

                request.POST.get(

                    "medication_order"

                )

            )

            order = get_object_or_404(

                medication_order_queryset(),

                pk=medication_order_id,

                encounter=encounter,

                patient=patient,

                status=MedicationOrder.Status.ACTIVE,

            )

            reason = (

                request.POST.get(

                    "reason"

                )

                or ""

            ).strip()

            # ------------------------------------------------

            # GIVE

            # ------------------------------------------------

            if mar_action == "give":

                _attach_next_due_times(
                    medication_orders=[order],
                    administrations=administrations,
                )

                timing_reason = (
                    request.POST.get("timing_reason") or ""
                ).strip()

                if not _order_is_administerable(order, timezone.now()):
                    messages.error(
                        request,
                        f"{order.medication.display_name} cannot be administered.",
                    )
                    return redirect(
                        reverse(
                            "medications:mar",
                            kwargs={"encounter_id": encounter.pk},
                        )
                    )

                if (
                    _order_requires_timing_reason(order, timezone.now())
                    and not timing_reason
                ):
                    messages.error(
                        request,
                        "Document the reason for the early or delayed administration.",
                    )
                    return redirect(
                        reverse(
                            "medications:mar",
                            kwargs={"encounter_id": encounter.pk},
                        )
                    )
                with transaction.atomic():

                    _create_mar_event(

                        request=request,

                        encounter=encounter,

                        patient=patient,

                        order=order,

                        status=(

                            _administered_status()

                        ),

                        notes=timing_reason,

                    )

                messages.success(

                    request,

                    (

                        f"{order.medication.display_name} "

                        "recorded as administered."

                    ),

                )

            # ------------------------------------------------

            # NOT GIVEN

            # ------------------------------------------------

            elif (

                mar_action

                == "not_given"

            ):

                if _mar_timing_status(order, timezone.now()) not in {
                    "due",
                    "overdue",
                }:
                    messages.error(
                        request,
                        (
                            "Not Given can only be recorded when a scheduled "
                            "medication is due or overdue."
                        ),
                    )
                    return redirect(
                        "medications:mar",
                        encounter_id=encounter.pk,
                    )

                if not reason:

                    messages.error(

                        request,

                        (

                            "A reason is required "

                            "when a medication is "

                            "not given."

                        ),

                    )

                else:

                    with transaction.atomic():

                        _create_mar_event(

                            request=request,

                            encounter=encounter,

                            patient=patient,

                            order=order,

                            status=(

                                _not_given_status()

                            ),

                            reason=reason,

                        )

                    messages.success(

                        request,

                        (

                            "Medication documented "

                            "as not given."

                        ),

                    )

            # ------------------------------------------------

            # HOLD

            # ------------------------------------------------

            elif mar_action == "hold":

                if (
                    request.POST.get("hold_source") != "details"
                    and _mar_timing_status(order, timezone.now())
                    not in {"due", "overdue"}
                ):
                    messages.error(
                        request,
                        (
                            "A medication that is not due can only be placed "
                            "on hold from its details section."
                        ),
                    )
                    return redirect(
                        "medications:mar",
                        encounter_id=encounter.pk,
                    )

                if not reason:

                    messages.error(

                        request,

                        (

                            "A reason is required "

                            "to hold a medication."

                        ),

                    )

                else:

                    with transaction.atomic():

                        _create_mar_event(

                            request=request,

                            encounter=encounter,

                            patient=patient,

                            order=order,

                            status=(

                                _held_status()

                            ),

                            reason=reason,

                        )

                        order.status = MedicationOrder.Status.ON_HOLD
                        order.save(update_fields=["status", "updated_at"])

                    messages.success(

                        request,

                        (

                            "Medication hold "

                            "documented."

                        ),

                    )

            return redirect(

                reverse(

                    "medications:mar",

                    kwargs={

                        "encounter_id":

                            encounter.pk,

                    },

                )

            )

        # ----------------------------------------------------

        # LEGACY / FULL ADMINISTRATION FORM

        # ----------------------------------------------------

        form = MedicationAdministrationForm(

            request.POST,

            encounter=encounter,

        )

        if form.is_valid():

            with transaction.atomic():

                administration = (

                    form.save(

                        commit=False

                    )

                )

                order = (

                    form.cleaned_data[

                        "medication_order"

                    ]

                )

                administration.patient = (

                    patient

                )

                administration.encounter = (

                    encounter

                )

                administration.medication_order = (

                    order

                )

                administration.medication = (

                    order.medication

                )

                administration.administered_by = (

                    request.user

                )

                # The server controls the actual Give timestamp.

                if (

                    administration.status

                    == _administered_status()

                ):

                    administration.administered_at = (

                        timezone.now()

                    )

                administration.full_clean()

                administration.save()

            messages.success(

                request,

                (

                    "Medication administration "

                    "recorded successfully."

                ),

            )

            return redirect(

                reverse(

                    "medications:mar",

                    kwargs={

                        "encounter_id":

                            encounter.pk,

                    },

                )

            )

    else:

        form = MedicationAdministrationForm(

            encounter=encounter,

        )

    # ========================================================

    # HISTORY

    # ========================================================

    # ========================================================

    # LAST GIVEN

    # ========================================================

    _attach_last_administrations(

        medication_orders=medication_orders,

        administrations=administrations,

    )

    history_administrations = (

        _compact_administration_history(

            administrations

        )

    )

    # ========================================================

    # EXCEPTIONS

    # ========================================================

    administered_status = (

        _administered_status()

    )

    administration_exceptions = [

        administration

        for administration

        in administrations

        if administration.status

        != administered_status

    ]

    # ========================================================

    # CONTEXT

    # ========================================================

    context = medication_context(

        section="mar",

        selected_patient=patient,

        active_encounter=encounter,

    )

    context.update(

        {

            "form":

                form,

            "medication_orders":

                medication_orders,

            "administrations":

                administrations,

            "history_administrations":

                history_administrations,

            "administration_exceptions":

                administration_exceptions,

            "current_time":

                timezone.now(),

            "ordering_providers": get_user_model().objects.filter(
                is_active=True
            ).order_by("last_name", "first_name", "username"),

            "order_methods": MedicationOrder.OrderMethod.choices,

        }

    )

    return render(

        request,

        "medications/mar.html",

        context,

    )

# ============================================================

# MEDICATION RECONCILIATION

# ============================================================

@login_required

def reconciliation(

    request: HttpRequest,

    patient_id,

) -> HttpResponse:

    patient = get_object_or_404(

        Patient,

        pk=patient_id,

    )

    active_encounter = (

        get_active_patient_encounter(

            patient

        )

    )

    medication_orders = (

        medication_order_queryset()

        .filter(

            patient=patient,

        )

        .order_by(

            "-ordered_at"

        )

    )

    administrations = (

        administration_queryset()

        .filter(

            patient=patient,

        )

        .order_by(

            "-administered_at",

            "-pk",

        )

    )

    context = medication_context(

        section="reconciliation",

        selected_patient=patient,

        active_encounter=active_encounter,

    )

    context.update(

        {

            "medication_orders":

                medication_orders,

            "administrations":

                administrations,

        }

    )

    return render(

        request,

        "medications/reconciliation.html",

        context,

    )
