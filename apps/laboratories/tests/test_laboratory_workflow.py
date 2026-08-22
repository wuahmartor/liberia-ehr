from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.encounters.models import Encounter
from apps.patients.models import Patient
from apps.diagnoses.models import ClinicalConcept, PatientDiagnosis, TerminologySource

from ..models import LabClinicalRecommendation, LabOrder, LabPanel, LabResult
from ..services import create_panel_order, result_payload, save_numeric_result


@override_settings(SECURE_SSL_REDIRECT=False)
class LaboratoryWorkflowTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="lab-user", password="test-password")
        self.patient = Patient.objects.create(mrn="LAB-PT-1", first_name="Lab", last_name="Patient", date_of_birth=date(1980, 1, 1))
        self.encounter = Encounter.objects.create(patient=self.patient, status=Encounter.EncounterStatus.IN_PROGRESS, created_by=self.user)
        self.panel = LabPanel.objects.get(code="bmp")
        source = TerminologySource.objects.create(name="ICD-10 test", source_type=TerminologySource.SourceType.ICD_10)
        concept = ClinicalConcept.objects.create(source=source, code="E87.5", title="Hyperkalemia")
        self.diagnosis = PatientDiagnosis.objects.create(patient=self.patient, encounter=self.encounter, concept=concept, diagnosis_type=PatientDiagnosis.DiagnosisType.PRIMARY, recorded_by=self.user)
        self.client.force_login(self.user)

    def make_order(self):
        return create_panel_order(patient=self.patient, encounter=self.encounter, panel=self.panel, priority=LabOrder.Priority.STAT, indication="Electrolyte monitoring", actor=self.user)

    def test_panel_order_expands_into_order_items(self):
        order = self.make_order()
        self.assertEqual(order.items.count(), self.panel.tests.count())
        self.assertTrue(order.accession_number.startswith("LAB-"))

    def test_result_uses_patient_range_and_flags_critical_value(self):
        order = self.make_order()
        potassium = order.items.get(test__code="potassium")
        result = save_numeric_result(order_item=potassium, value=Decimal("6.0"), actor=self.user)
        self.assertEqual(result.flag, LabResult.Flag.CRITICAL_HIGH)
        self.assertEqual(result.reference_range_snapshot["high"], "5.2000")
        self.assertFalse(result.reference_range_snapshot["locally_validated"])
        self.assertTrue(LabClinicalRecommendation.objects.filter(result=result, requires_clinician_review=True).exists())

    def test_normal_result_does_not_generate_recommendation(self):
        order = self.make_order()
        sodium = order.items.get(test__code="sodium")
        result = save_numeric_result(order_item=sodium, value=Decimal("140"), actor=self.user)
        self.assertEqual(result.flag, LabResult.Flag.NORMAL)
        self.assertFalse(result.recommendations.exists())

    def test_decision_support_payload_is_structured_and_coded(self):
        order = self.make_order()
        item = order.items.get(test__code="glucose")
        result = save_numeric_result(order_item=item, value=Decimal("450"), actor=self.user)
        payload = result_payload(result)
        self.assertEqual(payload["loinc_code"], "2345-7")
        self.assertEqual(payload["flag"], LabResult.Flag.CRITICAL_HIGH)
        self.assertEqual(payload["accession"], order.accession_number)

    def test_routes_render_and_result_entry_updates_order(self):
        order = self.make_order()
        item = order.items.get(test__code="creatinine")
        self.assertEqual(self.client.get(reverse("laboratories:dashboard")).status_code, 200)
        self.assertEqual(self.client.get(order.get_absolute_url()).status_code, 200)
        response = self.client.post(reverse("laboratories:enter-result", args=[item.pk]), {"numeric_value": "2.1", "notes": "Repeated."})
        self.assertRedirects(response, order.get_absolute_url())
        item.refresh_from_db()
        self.assertEqual(item.result.flag, LabResult.Flag.HIGH)

    def test_order_rejects_mismatched_patient_and_encounter(self):
        other = Patient.objects.create(mrn="LAB-PT-2", first_name="Other", last_name="Patient", date_of_birth=date(1990, 1, 1))
        response = self.client.post(reverse("laboratories:create-order", args=[other.pk, self.encounter.pk]), {"panel": self.panel.pk, "priority": "routine", "clinical_indication": "Test"})
        self.assertEqual(response.status_code, 404)

    def test_critical_result_requires_documented_acknowledgment(self):
        order = self.make_order()
        item = order.items.get(test__code="potassium")
        result = save_numeric_result(order_item=item, value=Decimal("6.2"), actor=self.user)
        url = reverse("laboratories:acknowledge-critical", args=[result.pk])
        self.client.post(url, {"note": ""})
        result.refresh_from_db()
        self.assertIsNone(result.critical_acknowledged_at)
        self.client.post(url, {"note": "Charge nurse and provider notified; repeat specimen ordered."})
        result.refresh_from_db()
        self.assertEqual(result.critical_acknowledged_by, self.user)
        self.assertIsNotNone(result.critical_acknowledged_at)

    def test_patient_results_page_integrates_with_encounter(self):
        self.make_order()
        response = self.client.get(reverse("laboratories:patient-results", args=[self.patient.pk]), {"encounter": self.encounter.pk})
        self.assertContains(response, "Basic Metabolic Panel")
        self.assertContains(response, "+ Order panel")

    def test_order_form_uses_patient_diagnoses_and_accepts_standalone_tests(self):
        url = reverse("laboratories:create-order", args=[self.patient.pk, self.encounter.pk])
        response = self.client.get(url)
        self.assertContains(response, "E87.5")
        self.assertContains(response, "Standalone tests")
        potassium = self.panel.tests.get(code="potassium")
        response = self.client.post(url, {"indication_diagnosis": self.diagnosis.pk, "panel": "", "standalone_tests": [potassium.pk], "priority": "urgent", "clinical_indication": "Repeat potassium"})
        self.assertEqual(response.status_code, 302)
        order = LabOrder.objects.latest("ordered_at")
        self.assertIsNone(order.panel)
        self.assertEqual(order.indication_diagnosis, self.diagnosis)
        self.assertEqual(list(order.items.values_list("test__code", flat=True)), ["potassium"])

    def test_expanded_panel_catalog_is_available(self):
        self.assertTrue(LabPanel.objects.filter(code="renal").exists())
        self.assertTrue(LabPanel.objects.filter(code="hepatic").exists())
        self.assertTrue(LabPanel.objects.filter(code="iron-studies").exists())
        self.assertTrue(LabPanel.objects.filter(code="inflammatory").exists())

    def test_laboratory_ordering_keeps_patient_sidebar_identity(self):
        response = self.client.get(reverse("laboratories:create-order", args=[self.patient.pk, self.encounter.pk]))
        self.assertEqual(response.context["active_primary_nav"], "clinical")
        self.assertEqual(response.context["selected_patient"], self.patient)
        self.assertContains(response, self.patient.mrn)
        self.assertContains(response, ">Orders<")
        self.assertContains(response, ">Medication<")
        self.assertContains(response, ">Laboratory<")
        self.assertContains(response, ">Therapy<")
        self.assertContains(response, "Equipment &amp; Supply")
        self.assertContains(response, ">Other<")

    def test_primary_clinical_menu_has_global_laboratory_management(self):
        response = self.client.get(reverse("laboratories:dashboard"))
        self.assertContains(response, "Laboratory Management")
        self.assertIsNone(response.context["selected_patient"])

    def test_patient_profile_displays_recent_abnormal_labs_and_more_link(self):
        order = self.make_order()
        result = save_numeric_result(order_item=order.items.get(test__code="potassium"), value=Decimal("6.2"), actor=self.user)
        response = self.client.get(reverse("patients:detail", args=[self.patient.pk]))
        self.assertContains(response, "Recent laboratory results")
        self.assertContains(response, result.display_value)
        self.assertContains(response, "Critical high")
        self.assertContains(response, "View more")
