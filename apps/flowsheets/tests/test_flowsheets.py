from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.encounters.models import Encounter
from apps.patients.models import Patient

from ..models import FlowSheetDefinition, FlowSheetEntry, FlowSheetFieldDefinition, FlowSheetValue


@override_settings(SECURE_SSL_REDIRECT=False)
class FlowSheetWorkflowTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="flowsheet-nurse", password="test-password")
        self.patient = Patient.objects.create(mrn="FLOW-0001", first_name="Flow", last_name="Patient", date_of_birth=date(1980, 1, 1))
        self.encounter = Encounter.objects.create(patient=self.patient, status=Encounter.EncounterStatus.IN_PROGRESS, created_by=self.user)
        self.definition = FlowSheetDefinition.objects.create(name="Focused assessment", slug="focused-test", category=FlowSheetDefinition.Category.NURSING, created_by=self.user)
        self.numeric_field = FlowSheetFieldDefinition.objects.create(
            flowsheet=self.definition,
            key="pain-score",
            label="Pain score",
            data_type=FlowSheetFieldDefinition.DataType.NUMBER,
            unit="/10",
            normal_min=0,
            normal_max=3,
            critical_max=8,
            display_order=1,
        )
        self.choice_field = FlowSheetFieldDefinition.objects.create(
            flowsheet=self.definition,
            key="mobility",
            label="Mobility",
            data_type=FlowSheetFieldDefinition.DataType.CHOICE,
            choices=["Independent", "Assisted"],
            display_order=2,
        )
        self.client.force_login(self.user)

    def test_chart_entry_is_linked_to_patient_encounter_and_flags_critical_value(self):
        response = self.client.post(
            reverse("flowsheets:create", args=[self.patient.pk, self.definition.pk]),
            {"assessment_type": "shift", "encounter": self.encounter.pk, "recorded_at": "2026-08-15T09:00", f"value_{self.numeric_field.pk}": "9", f"value_{self.choice_field.pk}": "Assisted", "notes": "Reassess after intervention."},
        )
        self.assertEqual(response.status_code, 302)
        entry = FlowSheetEntry.objects.get()
        self.assertEqual(entry.patient, self.patient)
        self.assertEqual(entry.encounter, self.encounter)
        value = entry.values.get(field=self.numeric_field)
        self.assertEqual(value.value_number, Decimal("9"))
        self.assertEqual(value.flag, FlowSheetValue.Flag.CRITICAL)

    def test_patient_grid_displays_structured_values(self):
        entry = FlowSheetEntry.objects.create(patient=self.patient, encounter=self.encounter, flowsheet=self.definition, recorded_by=self.user)
        FlowSheetValue.objects.create(entry=entry, field=self.numeric_field, value_number=2)
        response = self.client.get(reverse("flowsheets:patient", args=[self.patient.pk]), {"definition": self.definition.pk})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Pain score")
        self.assertContains(response, "2 /10")

    def test_encounter_scope_rejects_another_patients_encounter(self):
        other_patient = Patient.objects.create(mrn="FLOW-0002", first_name="Other", last_name="Patient", date_of_birth=date(1990, 1, 1))
        other_encounter = Encounter.objects.create(patient=other_patient, status=Encounter.EncounterStatus.IN_PROGRESS, created_by=self.user)
        response = self.client.get(reverse("flowsheets:patient", args=[self.patient.pk]), {"encounter": other_encounter.pk})
        self.assertEqual(response.status_code, 404)

    def test_entry_can_be_marked_entered_in_error_without_deletion(self):
        entry = FlowSheetEntry.objects.create(patient=self.patient, encounter=self.encounter, flowsheet=self.definition, recorded_by=self.user)
        response = self.client.post(reverse("flowsheets:entered-in-error", args=[entry.pk]), {"reason": "Documented on wrong patient."})
        self.assertRedirects(response, entry.get_absolute_url())
        entry.refresh_from_db()
        self.assertEqual(entry.status, FlowSheetEntry.Status.ENTERED_IN_ERROR)
        self.assertEqual(entry.entered_in_error_by, self.user)

    def test_correction_creates_a_linked_replacement_and_retains_original(self):
        original = FlowSheetEntry.objects.create(patient=self.patient, encounter=self.encounter, flowsheet=self.definition, recorded_by=self.user)
        FlowSheetValue.objects.create(entry=original, field=self.numeric_field, value_number=2)
        response = self.client.post(
            reverse("flowsheets:correct", args=[original.pk]),
            {"assessment_type": "reassessment", "recorded_at": "2026-08-15T10:00", "correction_reason": "Pain score entered incorrectly.", f"value_{self.numeric_field.pk}": "5", "notes": "Corrected value."},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(FlowSheetEntry.objects.count(), 2)
        correction = FlowSheetEntry.objects.get(corrected_from=original)
        self.assertEqual(correction.status, FlowSheetEntry.Status.CORRECTED)
        self.assertEqual(correction.values.get().value_number, Decimal("5"))

    def test_login_is_required(self):
        self.client.logout()
        response = self.client.get(reverse("flowsheets:patient", args=[self.patient.pk]))
        self.assertEqual(response.status_code, 302)

    def test_body_system_fields_are_grouped_and_abnormal_details_are_conditional(self):
        status_field = FlowSheetFieldDefinition.objects.create(
            flowsheet=self.definition, key="respiratory-status", label="System assessment",
            data_type=FlowSheetFieldDefinition.DataType.CHOICE, choices=["WNL", "Abnormal"],
            section="Respiratory", display_order=10,
        )
        detail_field = FlowSheetFieldDefinition.objects.create(
            flowsheet=self.definition, key="lung-sounds", label="Lung sounds",
            data_type=FlowSheetFieldDefinition.DataType.TEXT, section="Respiratory",
            subsection="Focused abnormal assessment", show_when_field_key="respiratory-status",
            show_when_value="Abnormal", display_order=11,
        )
        response = self.client.get(reverse("flowsheets:create", args=[self.patient.pk, self.definition.pk]))
        self.assertContains(response, "Respiratory")
        self.assertContains(response, "Focused abnormal assessment")
        self.assertContains(response, "values['respiratory-status'] === 'Abnormal'")

        response = self.client.post(
            reverse("flowsheets:create", args=[self.patient.pk, self.definition.pk]),
            {"assessment_type": "focused", "encounter": self.encounter.pk, "recorded_at": "2026-08-15T11:00", f"value_{status_field.pk}": "WNL", f"value_{detail_field.pk}": "Wheezes"},
        )
        self.assertEqual(response.status_code, 302)
        entry = FlowSheetEntry.objects.get()
        self.assertTrue(entry.values.filter(field=status_field, value_text="WNL").exists())
        self.assertFalse(entry.values.filter(field=detail_field).exists())

    def test_abnormal_required_multiselect_accepts_multiple_findings(self):
        status_field = FlowSheetFieldDefinition.objects.create(
            flowsheet=self.definition, key="edema-status", label="Edema",
            data_type=FlowSheetFieldDefinition.DataType.CHOICE, choices=["None", "Present"],
            section="Cardiovascular", display_order=20,
        )
        locations = FlowSheetFieldDefinition.objects.create(
            flowsheet=self.definition, key="edema-location", label="Edema location",
            data_type=FlowSheetFieldDefinition.DataType.MULTI_CHOICE,
            choices=["Left leg", "Right leg", "Sacral"], section="Cardiovascular",
            subsection="Edema details", show_when_field_key="edema-status",
            show_when_value="Present", is_required=True, display_order=21,
        )
        url = reverse("flowsheets:create", args=[self.patient.pk, self.definition.pk])
        base_data = {"assessment_type": "shift", "recorded_at": "2026-08-15T12:00", f"value_{status_field.pk}": "Present"}
        response = self.client.post(url, base_data)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "This detail is required")

        response = self.client.post(url, {**base_data, f"value_{locations.pk}": ["Left leg", "Right leg"]})
        self.assertEqual(response.status_code, 302)
        value = FlowSheetValue.objects.get(field=locations)
        self.assertEqual(value.display_value, "Left leg, Right leg")

    def test_seeded_musculoskeletal_fields_keep_location_beside_range_of_motion(self):
        fields = list(
            FlowSheetFieldDefinition.objects.filter(
                flowsheet__slug="nursing-systems-assessment",
                section="Musculoskeletal and Mobility",
            ).order_by("display_order")
        )
        keys = [field.key for field in fields]
        range_index = keys.index("range-of-motion")
        self.assertEqual(keys[range_index + 1], "musculoskeletal-location")
        location = fields[range_index + 1]
        self.assertIn("Index finger", location.choices)
        self.assertIn("Great toe", location.choices)

    def test_each_definition_tab_has_a_distinct_route_and_selects_its_definition(self):
        definitions = list(FlowSheetDefinition.objects.filter(is_active=True))
        response = self.client.get(reverse("flowsheets:patient", args=[self.patient.pk]))
        self.assertEqual(response.context["selected_definition"].slug, "nursing-systems-assessment")
        for definition in definitions:
            url = reverse("flowsheets:patient-definition", args=[self.patient.pk, definition.slug])
            self.assertContains(response, url)
            selected_response = self.client.get(url)
            self.assertEqual(selected_response.status_code, 200)
            self.assertEqual(selected_response.context["selected_definition"], definition)

    def test_unknown_definition_route_does_not_fall_back_to_intake_output(self):
        response = self.client.get(reverse("flowsheets:patient-definition", args=[self.patient.pk, "not-a-flowsheet"]))
        self.assertEqual(response.status_code, 404)

    def test_new_assessment_loads_and_saves_inside_flowsheet_panel(self):
        patient_url = reverse("flowsheets:patient-definition", args=[self.patient.pk, self.definition.slug])
        response = self.client.get(patient_url)
        self.assertContains(response, 'id="flowsheet-tabs-workspace"')
        self.assertContains(response, 'hx-target="#flowsheet-panel"')

        create_url = reverse("flowsheets:create", args=[self.patient.pk, self.definition.pk]) + "?inline=1&assessment_type=shift"
        response = self.client.get(create_url, HTTP_HX_REQUEST="true")
        self.assertContains(response, 'id="inline-flow-form"')
        self.assertContains(response, 'hx-target="#flowsheet-panel"')

        response = self.client.post(
            create_url,
            {"assessment_type": "shift", "recorded_at": "2026-08-15T13:00", f"value_{self.numeric_field.pk}": "2"},
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Assessment signed")
        self.assertContains(response, "Return to flowsheet")
