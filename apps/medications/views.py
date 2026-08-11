from __future__ import annotations

from typing import Any

from django.contrib import messages

from django.contrib.auth.decorators import login_required

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

    return administration

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

        )

        .order_by(

            "ordered_at",

            "pk",

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

                with transaction.atomic():

                    _create_mar_event(

                        request=request,

                        encounter=encounter,

                        patient=patient,

                        order=order,

                        status=(

                            _administered_status()

                        ),

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

    administrations = list(

        administration_queryset()

        .filter(

            encounter=encounter,

        )

        .order_by(

            "-administered_at",

            "-pk",

        )

    )

    # ========================================================

    # LAST GIVEN

    # ========================================================

    _attach_last_administrations(

        medication_orders=medication_orders,

        administrations=administrations,

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

            "administration_exceptions":

                administration_exceptions,

            "current_time":

                timezone.now(),

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