from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import UserProfile
from apps.patients.models import Patient

from ..models import (
    CareShift,
    CareTeam,
    CareTeamMember,
    PatientCareTeamAssignment,
    PatientStaffAssignment,
)
from ..services import (
    assign_patient_to_care_team,
    assign_patients,
    calculate_ratios,
    reconcile_assignments,
)


class CareAssignmentTests(TestCase):
    def make_staff(self, username, role, *, is_staff=False):
        user = get_user_model().objects.create_user(
            username=username, password="test-password", is_staff=is_staff
        )
        profile, _ = UserProfile.objects.get_or_create(user=user)
        profile.role = role
        profile.is_active_staff = True
        profile.is_clinical_staff = True
        profile.save()
        return user

    def setUp(self):
        self.manager = self.make_staff(
            "manager", UserProfile.Role.FACILITY_ADMIN, is_staff=True
        )
        self.nurse = self.make_staff("nurse", UserProfile.Role.NURSE)
        self.aide = self.make_staff("aide", UserProfile.Role.PATIENT_CARE_AIDE)
        self.patient = Patient.objects.create(
            mrn="CARE-0001",
            first_name="Care",
            last_name="Patient",
            date_of_birth=date(1980, 1, 1),
            created_by=self.manager,
            updated_by=self.manager,
        )
        self.shift = CareShift.objects.create(
            name="Day shift",
            starts_at=timezone.now() - timedelta(hours=1),
            ends_at=timezone.now() + timedelta(hours=7),
            created_by=self.manager,
        )

    def test_manager_assigns_patient_and_ratios_are_calculated(self):
        nurse_assignment = assign_patients(
            shift=self.shift,
            staff=self.nurse,
            patients=[self.patient],
            actor=self.manager,
        )[0]
        aide_assignment = assign_patients(
            shift=self.shift,
            staff=self.aide,
            patients=[self.patient],
            actor=self.manager,
        )[0]
        ratios = calculate_ratios([nurse_assignment, aide_assignment])
        self.assertEqual(ratios["patients_per_nurse"], 1.0)
        self.assertEqual(ratios["aides_per_nurse"], 1.0)

    def test_nurse_can_self_assign_but_not_assign_another_staff_member(self):
        created = assign_patients(
            shift=self.shift,
            staff=self.nurse,
            patients=[self.patient],
            actor=self.nurse,
        )
        self.assertEqual(len(created), 1)
        with self.assertRaises(PermissionError):
            assign_patients(
                shift=self.shift,
                staff=self.aide,
                patients=[self.patient],
                actor=self.nurse,
            )

    def test_shift_end_without_logout_does_not_complete_assignment(self):
        assignment = assign_patients(
            shift=self.shift,
            staff=self.nurse,
            patients=[self.patient],
            actor=self.manager,
        )[0]
        self.shift.ends_at = timezone.now() - timedelta(minutes=1)
        self.shift.save(update_fields=["ends_at"])
        reconcile_assignments()
        assignment.refresh_from_db()
        self.assertEqual(assignment.status, PatientStaffAssignment.Status.ASSIGNED)
        self.assertTrue(assignment.is_effective)

    def test_logout_before_shift_end_waits_then_completes_after_end(self):
        assignment = assign_patients(
            shift=self.shift,
            staff=self.nurse,
            patients=[self.patient],
            actor=self.manager,
        )[0]
        self.client.force_login(self.nurse)
        self.client.post(reverse("accounts:logout"))
        assignment.refresh_from_db()
        self.assertIsNotNone(assignment.staff_logged_out_at)
        self.assertEqual(assignment.status, PatientStaffAssignment.Status.ASSIGNED)
        self.shift.ends_at = timezone.now() - timedelta(minutes=1)
        self.shift.save(update_fields=["ends_at"])
        reconcile_assignments()
        assignment.refresh_from_db()
        self.assertEqual(assignment.status, PatientStaffAssignment.Status.COMPLETED)

    def test_board_has_drag_drop_and_accessible_selection_interface(self):
        self.client.force_login(self.manager)
        response = self.client.get(
            reverse("care_management:dashboard"), {"shift": self.shift.pk}
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'draggable="true"')
        self.assertContains(response, "Assign using dropdown and list selection")
        self.assertContains(response, "Patients per nurse")

    def test_non_care_role_cannot_open_assignment_board(self):
        receptionist = self.make_staff("reception", UserProfile.Role.RECEPTIONIST)
        self.client.force_login(receptionist)
        response = self.client.get(reverse("care_management:dashboard"))
        self.assertEqual(response.status_code, 404)

    def test_patient_can_belong_to_only_one_active_care_team(self):
        first_team = CareTeam.objects.create(
            shift=self.shift, name="Team A", created_by=self.manager
        )
        second_team = CareTeam.objects.create(
            shift=self.shift, name="Team B", created_by=self.manager
        )
        assign_patient_to_care_team(
            care_team=first_team, patient=self.patient, actor=self.manager
        )
        with self.assertRaisesMessage(ValueError, "already belongs to Team A"):
            assign_patient_to_care_team(
                care_team=second_team, patient=self.patient, actor=self.manager
            )

    def test_confirmed_batch_creates_one_team_for_multiple_patients(self):
        second_patient = Patient.objects.create(
            mrn="CARE-0002",
            first_name="Second",
            last_name="Patient",
            date_of_birth=date(1990, 1, 1),
            created_by=self.manager,
            updated_by=self.manager,
        )
        self.client.force_login(self.manager)
        response = self.client.post(
            reverse("care_management:team-commit"),
            {
                "shift": self.shift.pk,
                "staff": [self.nurse.pk, self.aide.pk],
                "patients": [self.patient.pk, second_patient.pk],
            },
        )
        self.assertEqual(response.status_code, 200)
        team = CareTeam.objects.get(shift=self.shift)
        self.assertEqual(CareTeamMember.objects.filter(care_team=team).count(), 2)
        self.assertEqual(
            PatientCareTeamAssignment.objects.filter(care_team=team).count(), 2
        )

    def test_existing_team_can_add_staff_and_patient(self):
        team = CareTeam.objects.create(
            shift=self.shift, name="Care Team 1", created_by=self.manager
        )
        second_patient = Patient.objects.create(
            mrn="CARE-EDIT-2",
            first_name="Added",
            last_name="Patient",
            date_of_birth=date(1991, 2, 2),
            created_by=self.manager,
            updated_by=self.manager,
        )
        self.client.force_login(self.manager)
        board = self.client.get(
            reverse("care_management:dashboard"), {"shift": self.shift.pk}
        )
        self.assertContains(board, "Drop staff or unassigned patients here")
        self.assertContains(board, "stageTeamDrop")
        self.assertContains(board, '@dragenter.prevent="dragOver = true"')
        response = self.client.post(
            reverse("care_management:team-update", args=[team.pk]),
            {"staff": [self.nurse.pk], "patients": [second_patient.pk]},
        )
        self.assertRedirects(
            response,
            f"{reverse('care_management:dashboard')}?shift={self.shift.pk}"
            f"#care-team-{team.pk}",
        )
        self.assertTrue(
            CareTeamMember.objects.filter(care_team=team, staff=self.nurse).exists()
        )
        self.assertTrue(
            PatientCareTeamAssignment.objects.filter(
                care_team=team, patient=second_patient,
                status=PatientCareTeamAssignment.Status.ACTIVE,
            ).exists()
        )
        refreshed_board = self.client.get(
            reverse("care_management:dashboard"), {"shift": self.shift.pk}
        )
        self.assertContains(refreshed_board, "Assigned")
        self.assertContains(refreshed_board, "Unassigned")
