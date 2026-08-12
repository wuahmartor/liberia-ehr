from django.conf import settings
from django.db import models


class EncounterNursingRecord(models.Model):
    patient = models.ForeignKey("patients.Patient", on_delete=models.PROTECT)
    encounter = models.ForeignKey("encounters.Encounter", on_delete=models.PROTECT)
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="nursing_%(class)s_records",
    )
    recorded_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        abstract = True


class NursingAssessment(EncounterNursingRecord):
    class Finding(models.TextChoices):
        NORMAL = "normal", "Within expected limits"
        ABNORMAL = "abnormal", "Abnormal"
        NOT_ASSESSED = "not_assessed", "Not assessed"

    class AssessmentType(models.TextChoices):
        ADMISSION = "admission", "Admission assessment"
        SHIFT = "shift", "Shift assessment"
        FOCUSED = "focused", "Focused assessment"
        TRANSFER = "transfer", "Transfer assessment"
        DISCHARGE = "discharge", "Discharge assessment"
        POST_PROCEDURE = "post_procedure", "Post-procedure assessment"
        CHANGE_IN_CONDITION = "change", "Change-in-condition assessment"

    assessment_type = models.CharField(
        max_length=30,
        choices=AssessmentType.choices,
        default=AssessmentType.SHIFT,
        db_index=True,
    )
    neurological_status = models.CharField(max_length=20, blank=True)
    respiratory_status = models.CharField(max_length=20, blank=True)
    cardiovascular_status = models.CharField(max_length=20, blank=True)
    gastrointestinal_status = models.CharField(max_length=20, blank=True)
    genitourinary_status = models.CharField(max_length=20, blank=True)
    integumentary_status = models.CharField(max_length=20, blank=True)
    musculoskeletal_status = models.CharField(max_length=20, blank=True)
    psychosocial_status = models.CharField(max_length=20, blank=True)
    consciousness = models.CharField(max_length=100, blank=True)
    orientation = models.CharField(max_length=100, blank=True)
    pupils = models.CharField(max_length=100, blank=True)
    speech = models.CharField(max_length=100, blank=True)
    motor_strength = models.CharField(max_length=100, blank=True)
    respiratory = models.CharField(max_length=300, blank=True)
    respiratory_pattern = models.CharField(max_length=100, blank=True)
    respiratory_effort = models.CharField(max_length=100, blank=True)
    breath_sounds = models.CharField(max_length=100, blank=True)
    breath_sound_laterality = models.CharField(max_length=100, blank=True)
    lung_rul = models.CharField("Right upper lobe", max_length=100, blank=True)
    lung_rml = models.CharField("Right middle lobe", max_length=100, blank=True)
    lung_rll = models.CharField("Right lower lobe", max_length=100, blank=True)
    lung_lul = models.CharField("Left upper lobe", max_length=100, blank=True)
    lung_lll = models.CharField("Left lower lobe", max_length=100, blank=True)
    cough = models.CharField(max_length=100, blank=True)
    oxygen_support = models.CharField(max_length=100, blank=True)
    cardiovascular = models.CharField(max_length=300, blank=True)
    cardiac_rhythm = models.CharField(max_length=100, blank=True)
    heart_sounds = models.CharField(max_length=100, blank=True)
    peripheral_pulses = models.CharField(max_length=100, blank=True)
    pulse_laterality = models.CharField(max_length=100, blank=True)
    capillary_refill = models.CharField(max_length=100, blank=True)
    edema_grade = models.CharField(max_length=50, blank=True)
    edema_location = models.CharField(max_length=150, blank=True)
    neurological = models.CharField(max_length=300, blank=True)
    skin = models.CharField(max_length=300, blank=True)
    skin_color = models.CharField(max_length=100, blank=True)
    skin_temperature = models.CharField(max_length=100, blank=True)
    skin_moisture = models.CharField(max_length=100, blank=True)
    skin_integrity = models.CharField(max_length=100, blank=True)
    wound_location = models.CharField(max_length=150, blank=True)
    pressure_injury_stage = models.CharField(max_length=50, blank=True)
    mobility = models.CharField(max_length=300, blank=True)
    gait = models.CharField(max_length=100, blank=True)
    assistive_device = models.CharField(max_length=100, blank=True)
    activity_tolerance = models.CharField(max_length=100, blank=True)
    abdomen = models.CharField(max_length=100, blank=True)
    bowel_sounds = models.CharField(max_length=100, blank=True)
    bowel_sounds_exception_quadrant = models.CharField(
        "Bowel-sound exception quadrant", max_length=20, blank=True
    )
    nausea_vomiting = models.CharField(max_length=100, blank=True)
    last_bowel_movement = models.DateField(null=True, blank=True)
    diet_tolerance = models.CharField(max_length=100, blank=True)
    urinary_pattern = models.CharField(max_length=100, blank=True)
    urine_characteristics = models.CharField(max_length=100, blank=True)
    urinary_device = models.CharField(max_length=100, blank=True)
    mood_affect = models.CharField(max_length=100, blank=True)
    behavior = models.CharField(max_length=100, blank=True)
    communication_needs = models.CharField(max_length=150, blank=True)
    pain_score = models.PositiveSmallIntegerField(default=0)
    fall_risk = models.BooleanField(default=False)
    pressure_injury_risk = models.BooleanField(default=False)
    admission_source = models.CharField(max_length=200, blank=True)
    baseline_function = models.TextField(blank=True)
    focused_system = models.CharField(max_length=100, blank=True)
    focused_findings = models.TextField(blank=True)
    transfer_destination = models.CharField(max_length=200, blank=True)
    discharge_disposition = models.CharField(max_length=200, blank=True)
    education_and_readiness = models.TextField(blank=True)
    procedure_and_recovery = models.TextField(blank=True)
    change_in_condition = models.TextField(blank=True)
    provider_notified = models.BooleanField(default=False)
    narrative = models.TextField(blank=True)

    class Meta:
        ordering = ("-recorded_at",)


class NursingTask(EncounterNursingRecord):
    class Priority(models.TextChoices):
        ROUTINE = "routine", "Routine"
        URGENT = "urgent", "Urgent"
        STAT = "stat", "STAT"

    description = models.CharField(max_length=300)
    priority = models.CharField(max_length=20, choices=Priority.choices)
    due_at = models.DateTimeField(null=True, blank=True, db_index=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    completed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="completed_nursing_tasks",
    )

    class Meta:
        ordering = ("completed_at", "due_at", "-recorded_at")


class IntakeOutputRecord(EncounterNursingRecord):
    class Kind(models.TextChoices):
        INTAKE = "intake", "Intake"
        OUTPUT = "output", "Output"

    kind = models.CharField(max_length=10, choices=Kind.choices)
    source = models.CharField(max_length=100)
    volume_ml = models.PositiveIntegerField()
    occurred_at = models.DateTimeField(db_index=True)
    notes = models.CharField(max_length=300, blank=True)

    class Meta:
        ordering = ("-occurred_at",)


class NursingHandoff(EncounterNursingRecord):
    given_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="nursing_handoffs_given",
        null=True,
        blank=True,
    )
    received_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="nursing_handoffs_received",
        null=True,
        blank=True,
    )
    situation = models.TextField()
    background = models.TextField()
    assessment = models.TextField()
    recommendation = models.TextField()
    safety_concerns = models.TextField(blank=True)

    class Meta:
        ordering = ("-recorded_at",)
