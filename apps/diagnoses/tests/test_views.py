from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.diagnoses.models import ClinicalConcept, TerminologySource


class ICD10SearchTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="diagnosis-tester", password="test-pass-123"
        )
        self.client.force_login(self.user)
        source = TerminologySource.objects.create(
            name="ICD-10-CM",
            source_type=TerminologySource.SourceType.ICD_10,
            release_version="FY2026",
        )
        self.concept = ClinicalConcept.objects.create(
            source=source,
            code="E11.9",
            title="Type 2 diabetes mellitus without complications",
            is_active=True,
            is_billable=True,
        )

    def test_search_by_code(self):
        response = self.client.get(reverse("diagnoses:icd10-search"), {"q": "E11"})
        self.assertContains(response, "E11.9")

    def test_short_search_returns_no_result(self):
        response = self.client.get(reverse("diagnoses:icd10-search"), {"q": "E"})
        self.assertNotContains(response, "E11.9")
