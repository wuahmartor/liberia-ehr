import json
from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.encounters.models import Encounter
from apps.medications.models import MedicationAdministration
from apps.medications.views import (
    _attach_next_due_times,
    _compact_administration_history,
    _mar_timing_status,
)
from apps.orders.models import MedicationOrder
from apps.patients.models import Patient
from apps.pharmacy.models import Medication


@override_settings(SECURE_SSL_REDIRECT=False)
class MedicationAdministrationRecordTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="mar-nurse",
            password="test-password",
        )
        self.patient = Patient.objects.create(
            mrn="MAR-0001",
            first_name="Test",
            last_name="Patient",
            date_of_birth=date(1990, 1, 1),
        )
        self.encounter = Encounter.objects.create(
            patient=self.patient,
            status=Encounter.EncounterStatus.IN_PROGRESS,
            created_by=self.user,
        )
        self.medications = [
            Medication.objects.create(
                code=f"MAR-MED-{number}",
                generic_name=f"Medication {number}",
                strength="10 mg",
                dosage_form="Tablet",
                route="Oral",
                unit_of_measure="tablet",
            )
            for number in range(1, 3)
        ]
        self.orders = [
            MedicationOrder.objects.create(
                patient=self.patient,
                encounter=self.encounter,
                medication=medication,
                dose="10",
                dose_unit=MedicationOrder.DoseUnit.MG,
                route=MedicationOrder.Route.ORAL,
                frequency=MedicationOrder.Frequency.DAILY,
                ordered_by=self.user,
            )
            for medication in self.medications
        ]
        self.url = reverse(
            "medications:mar",
            kwargs={"encounter_id": self.encounter.pk},
        )
        self.client.force_login(self.user)

    def test_create_record_saves_all_selected_medications(self):
        response = self.client.post(
            self.url,
            {
                "mar_action": "give_selected",
                "medication_orders": [str(order.pk) for order in self.orders],
            },
        )

        self.assertRedirects(response, self.url)
        administrations = MedicationAdministration.objects.order_by(
            "medication_order_id"
        )
        self.assertEqual(administrations.count(), 2)
        self.assertEqual(
            {event.medication_order_id for event in administrations},
            {order.pk for order in self.orders},
        )
        self.assertTrue(
            all(
                event.status == MedicationAdministration.Status.ADMINISTERED
                for event in administrations
            )
        )

    def test_create_record_is_atomic_when_an_order_is_inactive(self):
        self.orders[1].status = MedicationOrder.Status.DISCONTINUED
        self.orders[1].save(update_fields=["status"])

        response = self.client.post(
            self.url,
            {
                "mar_action": "give_selected",
                "medication_orders": [str(order.pk) for order in self.orders],
            },
        )

        self.assertRedirects(response, self.url)
        self.assertFalse(MedicationAdministration.objects.exists())

    def test_duplicate_selected_order_is_recorded_once(self):
        order_id = str(self.orders[0].pk)

        self.client.post(
            self.url,
            {
                "mar_action": "give_selected",
                "medication_orders": [order_id, order_id],
            },
        )

        self.assertEqual(MedicationAdministration.objects.count(), 1)

    def test_outside_window_requires_a_timing_reason(self):
        self.orders[0].start_datetime = timezone.now() + timedelta(hours=4)
        self.orders[0].save(update_fields=["start_datetime"])

        self.client.post(
            self.url,
            {
                "mar_action": "give_selected",
                "medication_orders": [str(self.orders[0].pk)],
            },
        )

        self.assertFalse(MedicationAdministration.objects.exists())

    def test_future_scheduled_dose_requires_an_early_reason(self):
        self.orders[0].start_datetime = timezone.now() + timedelta(hours=2)
        self.orders[0].save(update_fields=["start_datetime"])

        self.client.post(
            self.url,
            {
                "mar_action": "give_selected",
                "medication_orders": [str(self.orders[0].pk)],
            },
        )

        self.assertFalse(MedicationAdministration.objects.exists())

    def test_outside_window_saves_timing_reason_in_notes(self):
        self.orders[0].start_datetime = timezone.now() - timedelta(hours=4)
        self.orders[0].save(update_fields=["start_datetime"])
        reason = "Delayed because the patient was undergoing imaging"

        self.client.post(
            self.url,
            {
                "mar_action": "give_selected",
                "medication_orders": [str(self.orders[0].pk)],
                "timing_reasons": json.dumps(
                    {str(self.orders[0].pk): reason}
                ),
            },
        )

        administration = MedicationAdministration.objects.get()
        self.assertEqual(administration.notes, reason)

    def test_prn_medication_can_be_given_without_a_due_time(self):
        self.orders[0].frequency = MedicationOrder.Frequency.PRN
        self.orders[0].start_datetime = timezone.now() + timedelta(days=1)
        self.orders[0].save(update_fields=["frequency", "start_datetime"])

        self.client.post(
            self.url,
            {
                "mar_action": "give_selected",
                "medication_orders": [str(self.orders[0].pk)],
            },
        )

        self.assertEqual(MedicationAdministration.objects.count(), 1)

    def test_administered_medication_recycles_to_next_due_time(self):
        now = timezone.now()
        scheduled_at = now - timedelta(hours=13)
        administration = MedicationAdministration.objects.create(
            patient=self.patient,
            encounter=self.encounter,
            medication_order=self.orders[0],
            medication=self.medications[0],
            dose_administered="10 mg",
            route=MedicationOrder.Route.ORAL,
            status=MedicationAdministration.Status.ADMINISTERED,
            scheduled_at=scheduled_at,
            administered_at=now,
            administered_by=self.user,
        )
        self.orders[0].frequency = MedicationOrder.Frequency.Q6H

        _attach_next_due_times(
            medication_orders=[self.orders[0]],
            administrations=[administration],
        )

        self.assertEqual(
            self.orders[0].next_due_at,
            now + timedelta(hours=6),
        )
        self.assertEqual(
            _mar_timing_status(self.orders[0], now),
            "scheduled",
        )

    def test_legacy_uppercase_frequency_recycles(self):
        now = timezone.now()
        administration = MedicationAdministration.objects.create(
            patient=self.patient,
            encounter=self.encounter,
            medication_order=self.orders[0],
            medication=self.medications[0],
            dose_administered="10 mg",
            route=MedicationOrder.Route.ORAL,
            status=MedicationAdministration.Status.ADMINISTERED,
            administered_at=now,
            administered_by=self.user,
        )
        self.orders[0].frequency = "BID"

        _attach_next_due_times(
            medication_orders=[self.orders[0]],
            administrations=[administration],
        )

        self.assertEqual(
            self.orders[0].next_due_at,
            now + timedelta(hours=12),
        )
        self.assertEqual(_mar_timing_status(self.orders[0], now), "scheduled")

    def test_legacy_combined_prn_frequency_remains_prn(self):
        self.orders[0].frequency = "TID PRN"

        _attach_next_due_times(
            medication_orders=[self.orders[0]],
            administrations=[],
        )

        self.assertTrue(self.orders[0].is_prn)
        self.assertIsNone(self.orders[0].next_due_at)

    def test_hold_changes_order_status_and_resume_restores_active(self):
        self.client.post(
            self.url,
            {
                "mar_action": "hold",
                "medication_order": str(self.orders[0].pk),
                "reason": "Temporary clinical hold",
                "hold_source": "details",
            },
        )
        self.orders[0].refresh_from_db()
        self.assertEqual(self.orders[0].status, MedicationOrder.Status.ON_HOLD)

        self.client.post(
            self.url,
            {
                "mar_action": "resume_order",
                "medication_order": str(self.orders[0].pk),
            },
        )
        self.orders[0].refresh_from_db()
        self.assertEqual(self.orders[0].status, MedicationOrder.Status.ACTIVE)

    def test_not_due_hold_is_rejected_outside_details(self):
        self.orders[0].start_datetime = timezone.now() + timedelta(hours=2)
        self.orders[0].save(update_fields=["start_datetime"])

        self.client.post(
            self.url,
            {
                "mar_action": "hold",
                "medication_order": str(self.orders[0].pk),
                "reason": "Attempted row hold",
                "hold_source": "mar_row",
            },
        )

        self.orders[0].refresh_from_db()
        self.assertEqual(self.orders[0].status, MedicationOrder.Status.ACTIVE)
        self.assertFalse(MedicationAdministration.objects.exists())

    def test_discontinue_is_terminal(self):
        self.client.post(
            self.url,
            {
                "mar_action": "discontinue_order",
                "medication_order": str(self.orders[0].pk),
                "discontinuation_ordered_by": str(self.user.pk),
                "discontinuation_order_method": "electronic",
                "discontinuation_reason": "Therapy completed",
            },
        )
        self.orders[0].refresh_from_db()
        self.assertEqual(
            self.orders[0].status,
            MedicationOrder.Status.DISCONTINUED,
        )
        self.assertIsNotNone(self.orders[0].discontinued_at)
        self.assertEqual(self.orders[0].discontinuation_ordered_by, self.user)
        self.assertEqual(self.orders[0].discontinuation_reason, "Therapy completed")

        response = self.client.get(self.url)
        self.assertNotIn(self.orders[0], response.context["medication_orders"])

        self.client.post(
            self.url,
            {
                "mar_action": "resume_order",
                "medication_order": str(self.orders[0].pk),
            },
        )
        self.orders[0].refresh_from_db()
        self.assertEqual(
            self.orders[0].status,
            MedicationOrder.Status.DISCONTINUED,
        )

    def test_not_given_is_rejected_when_scheduled_medication_is_not_due(self):
        self.orders[0].start_datetime = timezone.now() + timedelta(hours=2)
        self.orders[0].save(update_fields=["start_datetime"])

        self.client.post(
            self.url,
            {
                "mar_action": "not_given",
                "medication_order": str(self.orders[0].pk),
                "reason": "Attempted too early",
            },
        )

        self.assertFalse(MedicationAdministration.objects.exists())

    def test_history_displays_each_medication_once(self):
        now = timezone.now()
        events = [
            MedicationAdministration.objects.create(
                patient=self.patient,
                encounter=self.encounter,
                medication_order=self.orders[0],
                medication=self.medications[0],
                dose_administered="10 mg",
                route=MedicationOrder.Route.ORAL,
                status=MedicationAdministration.Status.ADMINISTERED,
                administered_at=now - timedelta(hours=offset),
                administered_by=self.user,
            )
            for offset in range(4)
        ]

        history = _compact_administration_history(events)

        self.assertEqual(len(history), 1)
        self.assertEqual(history[0].history_event_count, 4)
        self.assertEqual(history[0].history_events, events)

    def test_history_is_sorted_alphabetically_by_medication(self):
        now = timezone.now()
        events = [
            MedicationAdministration.objects.create(
                patient=self.patient,
                encounter=self.encounter,
                medication_order=order,
                medication=medication,
                dose_administered="10 mg",
                route=MedicationOrder.Route.ORAL,
                status=MedicationAdministration.Status.ADMINISTERED,
                administered_at=now,
                administered_by=self.user,
            )
            for order, medication in reversed(
                list(zip(self.orders, self.medications, strict=True))
            )
        ]

        history = _compact_administration_history(events)

        self.assertEqual(
            [event.medication.display_name for event in history],
            sorted(
                medication.display_name for medication in self.medications
            ),
        )
