from collections import defaultdict

from django.db import transaction
from django.utils import timezone

from apps.accounts.models import UserProfile

from .models import CareTeamMember, PatientCareTeamAssignment, PatientStaffAssignment

MANAGER_ROLES = {UserProfile.Role.SYSTEM_ADMIN, UserProfile.Role.FACILITY_ADMIN}
ASSIGNABLE_ROLES = {UserProfile.Role.NURSE, UserProfile.Role.PATIENT_CARE_AIDE}


@transaction.atomic
def add_staff_to_care_team(*, care_team, staff, actor):
    profile = UserProfile.objects.filter(user=staff).first()
    if not profile or not profile.is_active_staff or not profile.is_clinical_staff:
        raise ValueError("Only active clinical staff can join a care team.")
    membership, _ = CareTeamMember.objects.get_or_create(
        care_team=care_team, staff=staff, defaults={"added_by": actor}
    )
    membership.full_clean()
    return membership


@transaction.atomic
def assign_patient_to_care_team(*, care_team, patient, actor):
    current = PatientCareTeamAssignment.objects.filter(
        patient=patient, status=PatientCareTeamAssignment.Status.ACTIVE
    ).first()
    if current and current.care_team_id != care_team.pk:
        raise ValueError(f"{patient} already belongs to {current.care_team.name}.")
    assignment, _ = PatientCareTeamAssignment.objects.get_or_create(
        patient=patient,
        status=PatientCareTeamAssignment.Status.ACTIVE,
        defaults={"care_team": care_team, "assigned_by": actor},
    )
    return assignment


def profile_role(user):
    return (
        UserProfile.objects.filter(user_id=user.pk)
        .values_list("role", flat=True)
        .first()
    )


def can_manage_staffing(user):
    return bool(
        user.is_superuser
        or user.is_staff
        or user.has_perm("care_management.manage_staffing")
        or profile_role(user) in MANAGER_ROLES
    )


def can_self_assign(user):
    return bool(user.is_active and profile_role(user) in ASSIGNABLE_ROLES)


def assignment_role_for(user):
    profile = UserProfile.objects.filter(user_id=user.pk).first()
    if not profile or not profile.is_active_staff or not profile.is_clinical_staff:
        raise ValueError("Only active clinical staff can receive patients.")
    role = profile.role
    if role == UserProfile.Role.NURSE:
        return PatientStaffAssignment.AssignmentRole.NURSE
    if role == UserProfile.Role.PATIENT_CARE_AIDE:
        return PatientStaffAssignment.AssignmentRole.PATIENT_CARE_AIDE
    raise ValueError("Only nurses and patient care aides can receive patients.")


@transaction.atomic
def assign_patients(*, shift, staff, patients, actor):
    patients = list(patients)
    if shift.ends_at <= timezone.now():
        raise ValueError("Patients cannot be added to an ended shift.")
    if not can_manage_staffing(actor) and actor.pk != staff.pk:
        raise PermissionError("You may assign patients only to yourself.")
    if actor.pk == staff.pk and not can_self_assign(actor):
        raise PermissionError("Your role cannot self-assign patients.")
    if shift.facility_id:
        staff_facility_id = (
            UserProfile.objects.filter(user_id=staff.pk)
            .values_list("facility_id", flat=True)
            .first()
        )
        if staff_facility_id != shift.facility_id:
            raise ValueError("Staff and shift must belong to the same facility.")
        if any(
            patient.registration_facility_id != shift.facility_id
            for patient in patients
        ):
            raise ValueError("Every patient must belong to the shift facility.")
    role = assignment_role_for(staff)
    created = []
    for patient in patients:
        assignment, was_created = PatientStaffAssignment.objects.get_or_create(
            shift=shift,
            patient=patient,
            staff=staff,
            status=PatientStaffAssignment.Status.ASSIGNED,
            defaults={"assignment_role": role, "assigned_by": actor},
        )
        if was_created:
            assignment.full_clean()
            created.append(assignment)
    return created


def record_staff_logout(user, at=None):
    """Record the logout condition; completion still also requires shift expiry."""
    at = at or timezone.now()
    PatientStaffAssignment.objects.filter(
        staff=user,
        status=PatientStaffAssignment.Status.ASSIGNED,
        staff_logged_out_at__isnull=True,
    ).update(staff_logged_out_at=at)
    reconcile_assignments(at=at, staff=user)


def reconcile_assignments(*, at=None, staff=None):
    """Complete assignments only after both end time and logout are present."""
    at = at or timezone.now()
    assignments = PatientStaffAssignment.objects.filter(
        status=PatientStaffAssignment.Status.ASSIGNED,
        shift__ends_at__lte=at,
        staff_logged_out_at__isnull=False,
    )
    if staff is not None:
        assignments = assignments.filter(staff=staff)
    return assignments.update(
        status=PatientStaffAssignment.Status.COMPLETED, released_at=at
    )


@transaction.atomic
def release_assignment(*, assignment, actor, reason=""):
    if not can_manage_staffing(actor) and assignment.staff_id != actor.pk:
        raise PermissionError("You cannot release this assignment.")
    if assignment.status == PatientStaffAssignment.Status.ASSIGNED:
        assignment.status = PatientStaffAssignment.Status.RELEASED
        assignment.released_at = timezone.now()
        assignment.released_by = actor
        assignment.release_reason = reason.strip()
        assignment.save(
            update_fields=["status", "released_at", "released_by", "release_reason"]
        )
    return assignment


def build_staff_loads(assignments, staff_users):
    by_staff = defaultdict(list)
    for assignment in assignments:
        by_staff[assignment.staff_id].append(assignment)
    return [
        {
            "staff": staff,
            "assignments": by_staff[staff.pk],
            "count": len(by_staff[staff.pk]),
        }
        for staff in staff_users
    ]


def calculate_ratios(assignments):
    patient_ids = {item.patient_id for item in assignments}
    nurse_ids = {
        item.staff_id
        for item in assignments
        if item.assignment_role == PatientStaffAssignment.AssignmentRole.NURSE
    }
    aide_ids = {
        item.staff_id
        for item in assignments
        if item.assignment_role
        == PatientStaffAssignment.AssignmentRole.PATIENT_CARE_AIDE
    }
    patient_count = len(patient_ids)
    nurse_count = len(nurse_ids)
    aide_count = len(aide_ids)
    return {
        "patients": patient_count,
        "nurses": nurse_count,
        "aides": aide_count,
        "patients_per_nurse": round(patient_count / nurse_count, 1)
        if nurse_count
        else None,
        "aides_per_nurse": round(aide_count / nurse_count, 1) if nurse_count else None,
    }
