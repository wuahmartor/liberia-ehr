from __future__ import annotations

import random
from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import UserProfile
from apps.care_management.models import (
    CareShift,
    CareTeam,
    CareTeamMember,
    PatientCareTeamAssignment,
)
from apps.clinical_notes.models import ClinicalNote
from apps.diagnoses.models import (
    ClinicalConcept,
    PatientDiagnosis,
    PatientProcedure,
    ProcedureCode,
    TerminologySource,
)
from apps.encounters.models import Encounter
from apps.facilities.models import Bed, ClinicalUnit, Department, Facility, Room
from apps.orders.models import MedicationOrder
from apps.patients.models import Patient
from apps.pharmacy.models import Medication


PASSWORD = "TestPass123!"
RNG = random.Random(20260815)

FIRST_NAMES = [
    "Musu", "Korto", "Hawa", "Fatu", "Miatta", "Satta", "Tenneh", "Yatta",
    "Joseph", "Samuel", "Emmanuel", "Prince", "Abraham", "James", "Daniel",
    "Grace", "Mary", "Esther", "Sarah", "Rebecca",
]
LAST_NAMES = [
    "Johnson", "Kollie", "Kamara", "Doe", "Sherman", "Cooper", "Davis",
    "Mulbah", "Koroma", "Tamba", "Kromah", "Williams", "Brown", "Cole",
    "Dennis", "Sackie", "Jallah", "Tweh", "Wesseh", "Sirleaf",
]

DIAGNOSES = [
    ("I10", "Essential hypertension"),
    ("E11.9", "Type 2 diabetes mellitus"),
    ("J18.9", "Community-acquired pneumonia"),
    ("J45.909", "Asthma"),
    ("B54", "Malaria"),
    ("D64.9", "Anemia"),
    ("K21.9", "Gastroesophageal reflux disease"),
    ("N39.0", "Urinary tract infection"),
]
PROCEDURES = [
    ("SEED-P001", "Routine physical examination"),
    ("SEED-P002", "Peripheral IV insertion"),
    ("SEED-P003", "Wound care and dressing"),
    ("SEED-P004", "Nebulizer treatment"),
    ("SEED-P005", "Blood specimen collection"),
]
MEDICATIONS = [
    ("SEED-AMOX", "Amoxicillin", "500 mg", "Capsule", "Oral"),
    ("SEED-ACET", "Acetaminophen", "500 mg", "Tablet", "Oral"),
    ("SEED-AMLO", "Amlodipine", "5 mg", "Tablet", "Oral"),
    ("SEED-METF", "Metformin", "500 mg", "Tablet", "Oral"),
    ("SEED-ARTL", "Artemether/Lumefantrine", "20/120 mg", "Tablet", "Oral"),
    ("SEED-CEF", "Ceftriaxone", "1 g", "Vial", "Intravenous"),
    ("SEED-SALB", "Salbutamol", "100 mcg", "Inhaler", "Inhalation"),
    ("SEED-OMEP", "Omeprazole", "20 mg", "Capsule", "Oral"),
    ("SEED-FESO", "Ferrous sulfate", "325 mg", "Tablet", "Oral"),
    ("SEED-NS", "Sodium chloride", "0.9%", "IV bag", "Intravenous"),
]


class Command(BaseCommand):
    help = "Create a repeatable, complete Liberia EHR demonstration dataset."

    def add_arguments(self, parser):
        parser.add_argument("--patients", type=int, default=50)

    @transaction.atomic
    def handle(self, *args, **options):
        patient_count = max(1, options["patients"])
        facilities = self._facilities()
        layout = self._facility_layout(facilities)
        staff = self._staff(facilities)
        concepts, procedures = self._terminology()
        medications = self._medications()
        patients = self._patients(patient_count, facilities, staff["providers"])
        self._remove_duplicate_seed_encounters(patients)
        encounters = self._clinical_records(
            patients, staff, concepts, procedures, medications
        )
        self._care_assignments(facilities, staff, encounters)
        self.stdout.write(self.style.SUCCESS(
            f"Seed complete: {len(facilities)} facilities, {len(staff['providers'])} providers, "
            f"{len(staff['nurses'])} nurses, {len(staff['cnas'])} CNAs, "
            f"{len(staff['pharmacists'])} pharmacists, {len(patients)} patients."
        ))
        self.stdout.write(f"Seed staff password: {PASSWORD}")

    def _facilities(self):
        specs = [
            ("SEED-JFK", "JFK Medical Center Demo", "national_hospital", "Monrovia"),
            ("SEED-RH", "Redemption Hospital Demo", "regional_hospital", "New Kru Town"),
        ]
        return [Facility.objects.get_or_create(
            code=code,
            defaults={
                "name": name, "short_name": name.replace(" Demo", ""),
                "facility_type": kind, "community_or_city": city,
                "county_or_state": "Montserrado", "provides_inpatient_services": True,
                "provides_emergency_services": True, "provides_pharmacy_services": True,
                "bed_capacity": 30,
            },
        )[0] for code, name, kind, city in specs]

    def _facility_layout(self, facilities):
        department_specs = [
            ("MED", "Internal Medicine", "clinical"),
            ("PED", "Pediatrics", "clinical"),
            ("EMR", "Emergency Medicine", "clinical"),
            ("NUR", "Nursing", "nursing"),
            ("PHA", "Pharmacy", "pharmacy"),
        ]
        result = {}
        for facility in facilities:
            units = []
            for code, name, kind in department_specs:
                department, _ = Department.objects.get_or_create(
                    facility=facility, code=code,
                    defaults={"name": name, "department_type": kind, "is_clinical": kind != "pharmacy"},
                )
                unit, _ = ClinicalUnit.objects.get_or_create(
                    facility=facility, code=f"{code}-U",
                    defaults={
                        "department": department, "name": f"{name} Unit",
                        "unit_type": "pharmacy" if kind == "pharmacy" else "inpatient",
                        "accepts_admissions": kind != "pharmacy",
                    },
                )
                units.append(unit)
                if kind == "pharmacy":
                    continue
                for room_number in range(1, 4):
                    room, _ = Room.objects.get_or_create(
                        facility=facility, code=f"{code}-R{room_number:02d}",
                        defaults={
                            "clinical_unit": unit, "name": f"{name} Room {room_number}",
                            "room_type": Room.RoomType.PATIENT_ROOM, "capacity": 2,
                        },
                    )
                    for bed_number in range(1, 3):
                        Bed.objects.get_or_create(
                            facility=facility, code=f"{code}-R{room_number:02d}-B{bed_number}",
                            defaults={
                                "clinical_unit": unit, "room": room,
                                "name": f"Bed {bed_number}", "bed_type": Bed.BedType.STANDARD,
                            },
                        )
            result[facility.pk] = units
        return result

    def _make_user(self, username, first, last, role, facility, title):
        user, created = get_user_model().objects.get_or_create(
            username=username,
            defaults={"first_name": first, "last_name": last, "email": f"{username}@example.test"},
        )
        if created:
            user.set_password(PASSWORD)
            user.save(update_fields=["password"])
        profile, _ = UserProfile.objects.get_or_create(user=user)
        profile.role = role
        profile.facility = facility
        profile.job_title = title
        profile.department = "Clinical Services"
        profile.employee_id = username.upper()
        profile.is_active_staff = True
        profile.is_clinical_staff = True
        profile.save()
        return user

    def _staff(self, facilities):
        groups = {"providers": [], "nurses": [], "cnas": [], "pharmacists": []}
        provider_roles = [(UserProfile.Role.PHYSICIAN, "Physician")]*5 + [(UserProfile.Role.NURSE_PRACTITIONER, "Nurse Practitioner")]*5
        for index, (role, title) in enumerate(provider_roles, 1):
            groups["providers"].append(self._make_user(f"seed_provider_{index:02d}", FIRST_NAMES[index], LAST_NAMES[index], role, facilities[index % 2], title))
        for index in range(1, 11):
            groups["nurses"].append(self._make_user(f"seed_nurse_{index:02d}", FIRST_NAMES[index + 3], LAST_NAMES[index + 4], UserProfile.Role.NURSE, facilities[index % 2], "Registered Nurse"))
        for index in range(1, 9):
            groups["cnas"].append(self._make_user(f"seed_cna_{index:02d}", FIRST_NAMES[index + 7], LAST_NAMES[index + 8], UserProfile.Role.PATIENT_CARE_AIDE, facilities[index % 2], "Certified Nursing Assistant"))
        for index in range(1, 5):
            groups["pharmacists"].append(self._make_user(f"seed_pharmacist_{index:02d}", FIRST_NAMES[index + 10], LAST_NAMES[index + 11], UserProfile.Role.PHARMACIST, facilities[index % 2], "Pharmacist"))
        return groups

    def _terminology(self):
        source, _ = TerminologySource.objects.get_or_create(
            name="Liberia EHR Seed ICD-10", defaults={"source_type": TerminologySource.SourceType.ICD_10, "organization": "WHO", "release_version": "Demo 2026"}
        )
        procedure_source, _ = TerminologySource.objects.get_or_create(
            name="Liberia EHR Seed Procedures", defaults={"source_type": TerminologySource.SourceType.LOCAL, "organization": "Liberia EHR"}
        )
        concepts = [ClinicalConcept.objects.get_or_create(source=source, code=code, defaults={"title": title, "is_leaf": True, "is_billable": True})[0] for code, title in DIAGNOSES]
        procedures = [ProcedureCode.objects.get_or_create(source=procedure_source, code=code, defaults={"code_system": "LOCAL", "title": title, "category": "Clinical"})[0] for code, title in PROCEDURES]
        return concepts, procedures

    def _medications(self):
        return [Medication.objects.get_or_create(
            code=code,
            defaults={"generic_name": name, "strength": strength, "dosage_form": form, "route": route, "unit_of_measure": form.lower(), "quantity_on_hand": 500, "reorder_level": 50},
        )[0] for code, name, strength, form, route in MEDICATIONS]

    def _patients(self, count, facilities, providers):
        patients = []
        for index in range(1, count + 1):
            patient, _ = Patient.objects.get_or_create(
                mrn=f"SEED-{index:05d}",
                defaults={
                    "first_name": FIRST_NAMES[(index * 3) % len(FIRST_NAMES)],
                    "last_name": LAST_NAMES[(index * 7) % len(LAST_NAMES)],
                    "date_of_birth": date(1945 + index % 60, (index % 12) + 1, (index % 27) + 1),
                    "sex_at_birth": Patient.SexAtBirth.FEMALE if index % 2 else Patient.SexAtBirth.MALE,
                    "blood_type": ["O+", "A+", "B+", "AB+"][index % 4],
                    "nationality": "Liberian", "registration_facility": facilities[index % 2],
                    "created_by": providers[index % len(providers)], "updated_by": providers[index % len(providers)],
                },
            )
            patients.append(patient)
        return patients

    def _remove_duplicate_seed_encounters(self, patients):
        reason = "Seeded comprehensive clinical evaluation"
        for patient in patients:
            encounters = list(
                Encounter.objects.filter(patient=patient, reason_for_visit=reason)
                .order_by("created_at", "pk")
            )
            for duplicate in encounters[1:]:
                ClinicalNote.objects.filter(encounter=duplicate).delete()
                PatientProcedure.objects.filter(encounter=duplicate).delete()
                PatientDiagnosis.objects.filter(encounter=duplicate).delete()
                MedicationOrder.objects.filter(encounter=duplicate).delete()
                duplicate.delete()

    def _clinical_records(self, patients, staff, concepts, procedures, medications):
        now = timezone.now()
        encounters = []
        for index, patient in enumerate(patients):
            provider = staff["providers"][index % len(staff["providers"])]
            active = index < 35
            encounter_start = now - timedelta(hours=6) if active else now - timedelta(days=2)
            encounter, _ = Encounter.objects.get_or_create(
                patient=patient, reason_for_visit="Seeded comprehensive clinical evaluation",
                defaults={
                    "encounter_type": Encounter.EncounterType.INPATIENT if active else Encounter.EncounterType.OUTPATIENT,
                    "start_datetime": encounter_start,
                    "status": Encounter.EncounterStatus.IN_PROGRESS if active else Encounter.EncounterStatus.COMPLETED,
                    "priority": Encounter.Priority.URGENT if index % 7 == 0 else Encounter.Priority.ROUTINE,
                    "registration_completed": True, "registered_at": encounter_start,
                    "arrived_at": encounter_start + timedelta(minutes=30),
                    "triaged_at": encounter_start + timedelta(minutes=45),
                    "attending_provider": provider, "created_by": provider,
                    "clinical_start_at": encounter_start + timedelta(hours=1), "clinical_started_by": provider,
                    "completed_at": None if active else now - timedelta(days=1),
                    "completed_by": None if active else provider, "is_active": active,
                    "end_datetime": None if active else now - timedelta(days=1),
                },
            )
            encounters.append(encounter)
            diagnosis_records = []
            for offset in range(2):
                concept = concepts[(index + offset) % len(concepts)]
                diagnosis, _ = PatientDiagnosis.objects.get_or_create(
                    patient=patient, encounter=encounter, concept=concept,
                    defaults={
                        "diagnosis_type": PatientDiagnosis.DiagnosisType.PRIMARY if offset == 0 else PatientDiagnosis.DiagnosisType.COMORBIDITY,
                        "clinical_status": PatientDiagnosis.DiagnosisStatus.ACTIVE,
                        "verification_status": PatientDiagnosis.VerificationStatus.CONFIRMED,
                        "severity": PatientDiagnosis.Severity.MODERATE,
                        "display_snapshot": concept.title, "code_snapshot": concept.code,
                        "source_snapshot": concept.source.name, "recorded_by": provider, "confirmed_by": provider,
                    },
                )
                diagnosis_records.append(diagnosis)
            procedure_code = procedures[index % len(procedures)]
            procedure, _ = PatientProcedure.objects.get_or_create(
                patient=patient, encounter=encounter, procedure_code=procedure_code,
                defaults={
                    "status": PatientProcedure.Status.COMPLETED,
                    "performed_on": now - timedelta(hours=(index % 12) + 1),
                    "performed_by": provider, "recorded_by": provider,
                    "notes": "Seeded procedure record for workflow testing.",
                },
            )
            note, _ = ClinicalNote.objects.get_or_create(
                patient=patient, encounter=encounter, title="Seeded comprehensive progress note",
                defaults={
                    "note_type": ClinicalNote.NoteType.SOAP, "status": ClinicalNote.Status.SIGNED,
                    "chief_complaint": "Follow-up of active medical concerns",
                    "subjective": "Patient reports interval improvement with persistent mild symptoms.",
                    "objective": "Alert, oriented, stable vital signs, and no acute distress.",
                    "assessment": "; ".join(item.display_snapshot for item in diagnosis_records),
                    "plan": "Continue medications, monitor response, provide education, and reassess.",
                    "content": "Complete seeded documentation for demonstration and testing.",
                    "author": provider, "signed_by": provider, "signed_at": now - timedelta(minutes=index),
                    "created_by": provider, "updated_by": provider,
                },
            )
            note.diagnoses.set(diagnosis_records)
            note.procedures.set([procedure])
            if active:
                for med_offset in range(2):
                    medication = medications[(index + med_offset) % len(medications)]
                    MedicationOrder.objects.get_or_create(
                        patient=patient, encounter=encounter, medication=medication,
                        defaults={
                            "dose": "1", "dose_unit": MedicationOrder.DoseUnit.TABLET,
                            "route": MedicationOrder.Route.ORAL,
                            "frequency": [MedicationOrder.Frequency.DAILY, MedicationOrder.Frequency.BID, MedicationOrder.Frequency.Q6H][(index + med_offset) % 3],
                            "start_datetime": now + timedelta(minutes=((index * 17 + med_offset * 31) % 420) - 90),
                            "stop_date": timezone.localdate() + timedelta(days=5),
                            "instructions": "Administer according to the MAR schedule.",
                            "clinical_indication": diagnosis_records[0].display_snapshot,
                            "ordered_by": provider,
                        },
                    )
        return encounters

    def _care_assignments(self, facilities, staff, encounters):
        now = timezone.now()
        for facility in facilities:
            shift, _ = CareShift.objects.get_or_create(
                name="Seed Day Shift", facility=facility,
                starts_at__date=timezone.localdate(),
                defaults={"starts_at": now - timedelta(hours=1), "ends_at": now + timedelta(hours=7), "created_by": staff["nurses"][0]},
            )
            facility_encounters = [item for item in encounters if item.is_active and item.patient.registration_facility_id == facility.pk]
            facility_staff = [user for user in staff["nurses"] + staff["cnas"] if user.profile.facility_id == facility.pk]
            for team_index in range(3):
                team, _ = CareTeam.objects.get_or_create(shift=shift, name=f"Care Team {team_index + 1}", defaults={"created_by": staff["nurses"][0]})
                for user in facility_staff[team_index * 2:team_index * 2 + 2]:
                    CareTeamMember.objects.get_or_create(care_team=team, staff=user, defaults={"added_by": staff["nurses"][0]})
                for encounter in facility_encounters[team_index::3]:
                    PatientCareTeamAssignment.objects.get_or_create(patient=encounter.patient, status=PatientCareTeamAssignment.Status.ACTIVE, defaults={"care_team": team, "assigned_by": staff["nurses"][0]})
