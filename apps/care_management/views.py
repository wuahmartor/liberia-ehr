from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db.models import Exists, OuterRef, Prefetch, Q
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
    create_care_assignment_batch,
    build_staff_loads,
    calculate_ratios,
    can_manage_staffing,
    can_self_assign,
    reconcile_assignments,
    release_assignment,
    update_care_assignment,
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
    patient_pool = patients
    assignment_form = AssignmentForm(actor=request.user, selected_shift=shift)
    care_teams = []
    if shift:
        care_teams = list(
            CareTeam.objects.filter(shift=shift)
            .prefetch_related(
                "memberships__staff__profile",
                Prefetch(
                    "patient_assignments",
                    queryset=PatientCareTeamAssignment.objects.filter(
                        status=PatientCareTeamAssignment.Status.ACTIVE
                    ).select_related("patient"),
                    to_attr="active_patient_assignments",
                ),
            )
        )
        assigned_patient_ids = list(PatientCareTeamAssignment.objects.filter(
            status=PatientCareTeamAssignment.Status.ACTIVE
        ).values_list("patient_id", flat=True))
        patients = patients.exclude(pk__in=assigned_patient_ids)
    else:
        assigned_patient_ids = []
    staff_team_counts = {}
    for team in care_teams:
        for membership in team.memberships.all():
            staff_team_counts[membership.staff_id] = (
                staff_team_counts.get(membership.staff_id, 0) + 1
            )
    staff_loads = build_staff_loads(assignments, staff)
    for load in staff_loads:
        load["care_team_count"] = staff_team_counts.get(load["staff"].pk, 0)
    assignment_form.fields["patients"].queryset = patients
    return {
        "selected_shift": shift,
        "shifts": _accessible_shifts(request.user).order_by("-starts_at")[:30],
        "staff_loads": staff_loads,
        "available_patients": patients,
        "patient_pool": patient_pool,
        "assigned_patient_ids": assigned_patient_ids,
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
def commit_assignment_batch(request):
    if not can_manage_staffing(request.user) and not can_self_assign(request.user):
        raise Http404
    shift = get_object_or_404(
        _accessible_shifts(request.user), pk=request.POST.get("shift")
    )
    staff_ids = request.POST.getlist("staff")
    patient_ids = request.POST.getlist("patients")
    if not can_manage_staffing(request.user) and staff_ids != [str(request.user.pk)]:
        return JsonResponse(
            {"ok": False, "error": "You may create an assignment only for yourself."},
            status=403,
        )
    staff = get_user_model().objects.filter(pk__in=staff_ids)
    patients = Patient.objects.filter(pk__in=patient_ids)
    try:
        team = create_care_assignment_batch(
            shift=shift, staff_users=staff, patients=patients, actor=request.user
        )
    except ValueError as exc:
        return JsonResponse({"ok": False, "error": str(exc)}, status=422)
    return JsonResponse(
        {
            "ok": True,
            "team": team.name,
            "staff_count": len(staff_ids),
            "patient_count": len(patient_ids),
        }
    )


@login_required
@require_POST
def update_assignment_team(request, team_id):
    if not can_manage_staffing(request.user):
        raise Http404
    team = get_object_or_404(
        CareTeam.objects.select_related("shift").filter(
            shift__in=_accessible_shifts(request.user)
        ),
        pk=team_id,
    )
    staff = get_user_model().objects.filter(
        pk__in=request.POST.getlist("staff"),
        is_active=True,
        profile__is_clinical_staff=True,
        profile__is_active_staff=True,
        profile__role__in=[
            UserProfile.Role.NURSE,
            UserProfile.Role.PATIENT_CARE_AIDE,
        ],
    )
    patients = Patient.objects.filter(pk__in=request.POST.getlist("patients"))
    try:
        update_care_assignment(
            care_team=team,
            staff_users=staff,
            patients=patients,
            actor=request.user,
        )
    except ValueError as exc:
        messages.error(request, str(exc))
    else:
        messages.success(request, f"{team.name} updated.")
    return redirect(
        f"{reverse('care_management:dashboard')}?shift={team.shift_id}"
        f"#care-team-{team.pk}"
    )


@login_required
@require_POST
def release_team_patient(request, assignment_id):
    assignment = get_object_or_404(
        PatientCareTeamAssignment.objects.select_related("care_team__shift").filter(
            care_team__shift__in=_accessible_shifts(request.user),
            status=PatientCareTeamAssignment.Status.ACTIVE,
        ),
        pk=assignment_id,
    )
    if not can_manage_staffing(request.user) and not can_self_assign(request.user):
        raise Http404
    assignment.status = PatientCareTeamAssignment.Status.RELEASED
    assignment.released_at = timezone.now()
    assignment.save(update_fields=["status", "released_at"])
    messages.success(request, "Patient released from the care team.")
    return redirect(
        f"{reverse('care_management:dashboard')}?shift={assignment.care_team.shift_id}"
    )
