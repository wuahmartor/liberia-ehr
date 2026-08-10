from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import Medication


@override_settings(SECURE_SSL_REDIRECT=False)
class MedicationListApiTests(TestCase):
    def setUp(self):
        self.url = reverse("pharmacy:medication-list-api")
        self.user = get_user_model().objects.create_user(
            username="pharmacist",
            password="test-password",
        )

    def create_medication(self, **overrides):
        fields = {
            "code": "AMOX-500-CAP",
            "generic_name": "Amoxicillin",
            "brand_name": "",
            "dosage_form": "Capsule",
            "strength": "500 mg",
            "route": "Oral",
            "unit_of_measure": "capsule",
            "quantity_on_hand": Decimal("25.000"),
        }
        fields.update(overrides)
        return Medication.objects.create(**fields)

    def test_api_requires_authentication(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:login"), response["Location"])

    def test_api_filters_active_medications_by_query_in_order(self):
        self.create_medication(
            code="Z-AMOX",
            generic_name="Amoxicillin",
            brand_name="Amoxil",
        )
        self.create_medication(
            code="A-AMOX",
            generic_name="Amoxicillin",
            brand_name="Moxatag",
        )
        self.create_medication(
            code="CIPRO-500",
            generic_name="Ciprofloxacin",
        )
        self.client.force_login(self.user)

        response = self.client.get(self.url, {"q": "amox"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            [
                {
                    "id": Medication.objects.get(code="A-AMOX").pk,
                    "code": "A-AMOX",
                    "display_name": "Amoxicillin (Moxatag) 500 mg Capsule",
                    "generic_name": "Amoxicillin",
                    "strength": "500 mg",
                    "dosage_form": "Capsule",
                    "route": "Oral",
                    "available_quantity": "25.000",
                },
                {
                    "id": Medication.objects.get(code="Z-AMOX").pk,
                    "code": "Z-AMOX",
                    "display_name": "Amoxicillin (Amoxil) 500 mg Capsule",
                    "generic_name": "Amoxicillin",
                    "strength": "500 mg",
                    "dosage_form": "Capsule",
                    "route": "Oral",
                    "available_quantity": "25.000",
                },
            ],
        )

    def test_api_excludes_inactive_medications(self):
        self.create_medication(
            code="INACTIVE-AMOX",
            generic_name="Amoxicillin",
            is_active=False,
        )
        self.client.force_login(self.user)

        response = self.client.get(self.url, {"q": "amoxicillin"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

    def test_api_limits_results_to_fifty_medications(self):
        Medication.objects.bulk_create(
            [
                Medication(
                    code=f"CAT-{number:03d}",
                    generic_name=f"Catalog medication {number:03d}",
                    dosage_form="Tablet",
                    strength="500 mg",
                    route="Oral",
                    unit_of_measure="tablet",
                )
                for number in range(51)
            ],
        )
        self.client.force_login(self.user)

        response = self.client.get(self.url, {"q": "catalog medication"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 50)
        self.assertEqual(response.json()[0]["code"], "CAT-000")
        self.assertEqual(response.json()[-1]["code"], "CAT-049")


@override_settings(SECURE_SSL_REDIRECT=False)
class MedicationCatalogViewTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="catalog-manager",
            password="test-password",
        )
        self.client.force_login(self.user)

    def payload(self, **overrides):
        data = {
            "code": "PARA-500-TAB",
            "generic_name": "Paracetamol",
            "brand_name": "",
            "dosage_form": "Tablet",
            "strength": "500 mg",
            "route": "Oral",
            "unit_of_measure": "tablet",
            "is_active": "on",
            "requires_prescription": "on",
            "reorder_level": "10",
            "quantity_on_hand": "50",
        }
        data.update(overrides)
        return data

    def test_catalog_create_update_and_delete(self):
        create_url = reverse("pharmacy:medication-catalog-create")
        response = self.client.post(create_url, self.payload())

        self.assertRedirects(
            response,
            reverse("pharmacy:medication-catalog"),
        )
        medication = Medication.objects.get(code="PARA-500-TAB")
        self.assertEqual(
            medication.display_name,
            "Paracetamol 500 mg Tablet",
        )

        response = self.client.post(
            reverse(
                "pharmacy:medication-catalog-update",
                kwargs={"pk": medication.pk},
            ),
            self.payload(quantity_on_hand="35"),
        )
        self.assertRedirects(
            response,
            reverse("pharmacy:medication-catalog"),
        )
        medication.refresh_from_db()
        self.assertEqual(medication.quantity_on_hand, Decimal("35"))

        response = self.client.post(
            reverse(
                "pharmacy:medication-catalog-delete",
                kwargs={"pk": medication.pk},
            ),
        )
        self.assertRedirects(
            response,
            reverse("pharmacy:medication-catalog"),
        )
        self.assertFalse(Medication.objects.filter(pk=medication.pk).exists())
