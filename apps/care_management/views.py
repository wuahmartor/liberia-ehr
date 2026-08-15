from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db.models import Exists, OuterRef, Q
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from apps.accounts.models import UserProfile
from apps.encounters.models import Encounter
from apps.patients.models import Patient

from .forms import AssignmentForm, CareShiftForm, SelfAssignmentForm
from .models import CareShift, CareTeam, PatientCareTeamAssignment, PatientStaffAssignment
from .services import (
    assign_patients,
    add_staff_to_care_team,
    assign_patient_to_care_team,
    build_staff_loads,
    calculate_ratios,
    can_manage_staffing,
    can_self_assign,
    reconcile_assignments,
    release_assignment,
)


def _shift_from_request(request):
    shift_id = request.GET.get("shift") or request.POST.get("shift")
    if shift_id:
        return get_object_or_404(_accessible_shifts(request.user), pk=shift_id)
    now = timezone.now()
    return (
        _accessible_shifts(request.user)
        .filter(starts_at__lte=now, ends_at__gte=now)
        .order_by("ends_at")
        .first()
        or _accessible_shifts(request.user)
        .filter(ends_at__gte=now)
        .order_by("starts_at")
        .first()
        or _accessible_shifts(request.user).order_by("-starts_at").first()
    )


def _accessible_shifts(user):
    if user.is_superuser or user.is_staff:
        return CareShift.objects.all()
    profile = getattr(user, "profile", None)
    if profile is None:
        return CareShift.objects.none()
    return CareShift.objects.filter(
        Q(facility_id=profile.facility_id) | Q(facility__isnull=True)
    )


def _board_context(request, shift=None):
    if not can_manage_staffing(request.user) and not can_self_assign(request.user):
        raise Http404
    reconcile_assignments()
    shift = shift or _shift_from_request(request)
    assignments = PatientStaffAssignment.objects.none()
    if shift:
        default_team, _ = CareTeam.objects.get_or_create(
            shift=shift,
            name="Care Team 1",
            defaults={"created_by": request.user},
        )
        assignments = list(
            PatientStaffAssignment.objects.effective()
            .filter(shift=shift)
            .select_related("patient", "staff", "staff__profile", "assigned_by")
        )
    staff = (
        get_user_model()
        .objects.filter(
            is_active=True,
            profile__is_clinical_staff=True,
            profile__is_active_staff=True,
            profile__role__in=[
                UserProfile.Role.NURSE,
                UserProfile.Role.PATIENT_CARE_AIDE,
            ],
        )
        .select_related("profile")
    )
    if shift and shift.facility_id:
        staff = staff.filter(profile__facility=shift.facility)
    staff = list(staff.order_by("profile__role", "last_name", "first_name"))
    patient_filter = request.GET.get("patients", "all")
    nurse_id = request.GET.get("nurse", "")
    open_statuses = (
        Encounter.EncounterStatus.PLANNED,
        Encounter.EncounterStatus.SCHEDULED,
        Encounter.EncounterStatus.ARRIVED,
        Encounter.EncounterStatus.TRIAGED,
        Encounter.EncounterStatus.IN_PROGRESS,
        Encounter.EncounterStatus.ON_HOLD,
    )
    patients = Patient.objects.annotate(
        has_open_encounter=Exists(
            Encounter.objects.filter(
                patient_id=OuterRef("pk"), is_active=True, status__in=open_statuses
            )
        ),
        has_completed_encounter=Exists(
            Encounter.objects.filter(
                patient_id=OuterRef("pk"), status=Encounter.EncounterStatus.COMPLETED
            )
        ),
    )
    assignment_scope = Q(staff_assignments__status=PatientStaffAssignment.Status.ASSIGNED)
    if shift:
        assignment_scope &= Q(staff_assignments__shift=shift)
    if patient_filter == "discharged":
        patients = patients.filter(has_open_encounter=False, has_completed_encounter=True)
    elif patient_filter == "mine":
        patients = patients.filter(assignment_scope, staff_assignments__staff=request.user)
    elif patient_filter == "nurse" and nurse_id:
        patients = patients.filter(
            assignment_scope,
            staff_assignments__staff_id=nurse_id,
            staff_assignments__assignment_role=PatientStaffAssignment.AssignmentRole.NURSE,
        )
    elif patient_filter == "active":
        patients = patients.filter(has_open_encounter=True)
    else:
        patient_filter = "all"
        patients = patients.filter(
            is_active=True,
            record_status=Patient.RecordStatus.ACTIVE,
            is_deceased=False,
        )
    patients = patients.distinct().order_by("last_name", "first_name")
    if shift and shift.facility_id:
        patients = patients.filter(registration_facility_id=shift.facility_id)
    assignment_form = AssignmentForm(actor=request.user, selected_shift=shift)
    assignment_form.fields["patients"].queryset = patients
    care_teams = []
    if shift:
        care_teams = list(
            CareTeam.objects.filter(shift=shift)
            .prefetch_related(
                "memberships__staff__profile",
                "patient_assignments__patient",
            )
        )
        assigned_patient_ids = PatientCareTeamAssignment.objects.filter(
            status=PatientCareTeamAssignment.Status.ACTIVE
        ).values_list("patient_id", flat=True)
        patients = patients.exclude(pk__in=assigned_patient_ids)
    return {
        "selected_shift": shift,
        "shifts": _accessible_shifts(request.user).order_by("-starts_at")[:30],
        "staff_loads": build_staff_loads(assignments, staff),
        "available_patients": patients,
        "all_patients": patients,
        "patient_filter": patient_filter,
        "selected_nurse": nurse_id,
        "nurses": [item for item in staff if item.profile.role == UserProfile.Role.NURSE],
        "care_teams": care_teams,
        "ratios": calculate_ratios(assignments),
        "can_manage_staffing": can_manage_staffing(request.user),
        "can_self_assign": can_self_assign(request.user),
        "assignment_form": assignment_form,
        "shift_form": CareShiftForm(actor=request.user),
    }


@login_required
@require_GET
def dashboard(request):
    context = _board_context(request)
    context.update(
        {
            "active_primary_nav": "clinical",
            "active_clinical_module": "care-management",
            "active_clinical_section": "assignments",
        }
    )
    return render(request, "care_management/dashboard.html", context)


@login_required
@require_GET
def board_partial(request):
    return render(
        request,
        "care_management/partials/assignment_board.html",
        _board_context(request),
    )


@login_required
@require_POST
def create_shift(request):
    if not can_manage_staffing(request.user):
        raise Http404
    form = CareShiftForm(request.POST, actor=request.user)
    if form.is_valid():
        shift = form.save(commit=False)
        shift.created_by = request.user
        shift.full_clean()
        shift.save()
        messages.success(request, f"Shift “{shift.name}” created.")
        return redirect(f"{reverse('care_management:dashboard')}?shift={shift.pk}")
    context = _board_context(request)
    context.update(
        {
            "shift_form": form,
            "active_primary_nav": "clinical",
            "active_clinical_module": "care-management",
        }
    )
    return render(request, "care_management/dashboard.html", context, status=422)


@login_required
@require_POST
def create_team(request):
    if not can_manage_staffing(request.user):
        raise Http404
    shift = get_object_or_404(
        _accessible_shifts(request.user), pk=request.POST.get("shift")
    )
    name = request.POST.get("name", "").strip()
    if not name:
        messages.error(request, "Enter a care-team name.")
    elif CareTeam.objects.filter(shift=shift, name__iexact=name).exists():
        messages.error(request, f"A care team named “{name}” already exists.")
    else:
        CareTeam.objects.create(shift=shift, name=name[:120], created_by=request.user)
        messages.success(request, f"Care team “{name[:120]}” created.")
    return redirect(f"{reverse('care_management:dashboard')}?shift={shift.pk}")


@login_required
@require_POST
def assign(request):
    shift = get_object_or_404(
        _accessible_shifts(request.user), pk=request.POST.get("shift")
    )
    if can_manage_staffing(request.user):
        form = AssignmentForm(request.POST, actor=request.user, selected_shift=shift)
        valid = form.is_valid()
        if valid:
            staff = form.cleaned_data["staff"]
            patients = form.cleaned_data["patients"]
    else:
        form = SelfAssignmentForm(request.POST)
        valid = form.is_valid() and can_self_assign(request.user)
        if valid:
            staff = request.user
            patients = form.cleaned_data["patients"]
    if not valid:
        message = "Select a valid shift, staff member, and at least one patient."
        if request.headers.get("Accept") == "application/json":
            return JsonResponse({"ok": False, "error": message}, status=422)
        messages.error(request, message)
        return redirect(f"{reverse('care_management:dashboard')}?shift={shift.pk}")
    try:
        created = assign_patients(
            shift=shift, staff=staff, patients=patients, actor=request.user
        )
    except (ValueError, PermissionError) as exc:
        if request.headers.get("Accept") == "application/json":
            return JsonResponse({"ok": False, "error": str(exc)}, status=422)
        messages.error(request, str(exc))
    else:
        if request.headers.get("Accept") == "application/json":
            return JsonResponse({"ok": True, "created": len(created)})
        messages.success(
            request,
            f"Assigned {len(created)} patient(s) to {staff.get_full_name() or staff.username}.",
        )
    return redirect(f"{reverse('care_management:dashboard')}?shift={shift.pk}")


@login_required
@require_POST
def release(request, assignment_id):
    assignment = get_object_or_404(
        PatientStaffAssignment.objects.select_related("shift", "staff").filter(
            shift__in=_accessible_shifts(request.user)
        ),
        pk=assignment_id,
    )
    try:
        release_assignment(
            assignment=assignment,
            actor=request.user,
            reason=request.POST.get("reason", ""),
        )
    except PermissionError:
        raise Http404
    messages.success(request, "Patient assignment released.")
    return redirect(
        f"{reverse('care_management:dashboard')}?shift={assignment.shift_id}"
    )


@login_required
@require_POST
def team_add_staff(request, team_id):
    team = get_object_or_404(CareTeam.objects.filter(shift__in=_accessible_shifts(request.user)), pk=team_id)
    if not can_manage_staffing(request.user):
        raise Http404
    staff = get_object_or_404(get_user_model(), pk=request.POST.get("staff"))
    try:
        add_staff_to_care_team(care_team=team, staff=staff, actor=request.user)
    except ValueError as exc:
        return JsonResponse({"ok": False, "error": str(exc)}, status=422)
    return JsonResponse({"ok": True})


@login_required
@require_POST
def team_add_patient(request, team_id):
    team = get_object_or_404(CareTeam.objects.filter(shift__in=_accessible_shifts(request.user)), pk=team_id)
    if not can_manage_staffing(request.user) and not can_self_assign(request.user):
        raise Http404
    patient = get_object_or_404(Patient, pk=request.POST.get("patient"))
    try:
        assign_patient_to_care_team(care_team=team, patient=patient, actor=request.user)
    except ValueError as exc:
        return JsonResponse({"ok": False, "error": str(exc)}, status=422)
    return JsonResponse({"ok": True})
