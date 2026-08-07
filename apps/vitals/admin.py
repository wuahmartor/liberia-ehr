from django.contrib import admin


from .models import VitalObservation


@admin.register(VitalObservation)
class VitalObservationAdmin(admin.ModelAdmin):
    list_display = (
        "patient",
        "recorded_at",
        "blood_pressure",
        "heart_rate",
        "respiratory_rate",
        "oxygen_saturation",
        "temperature_celsius",
        "clinical_status_value",
        "status",
        "recorded_by",
    )

    list_filter = (
        "status",
        "position",
        "temperature_site",
        "oxygen_delivery_method",
        "recorded_at",
    )

    search_fields = (
        "patient__mrn",
        "patient__first_name",
        "patient__middle_name",
        "patient__last_name",
        "encounter__encounter_number",
        "recorded_by__username",
        "recorded_by__first_name",
        "recorded_by__last_name",
        "notes",
    )

    readonly_fields = (
        "id",
        "recorded_by",
        "bmi_value",
        "bmi_category_value",
        "mean_arterial_pressure_value",
        "pulse_pressure_value",
        "clinical_status_value",
        "entered_in_error_at",
        "entered_in_error_by",
        "created_at",
        "updated_at",
    )

    autocomplete_fields = (
    "patient",
    "encounter",
    )

    date_hierarchy = "recorded_at"

    ordering = (
        "-recorded_at",
    )

    fieldsets = (
        (
            "Patient and encounter",
            {
                "fields": (
                    "id",
                    "patient",
                    "encounter",
                    "recorded_at",
                    "recorded_by",
                    "position",
                )
            },
        ),
        (
            "Core vital signs",
            {
                "fields": (
                    (
                        "temperature_celsius",
                        "temperature_site",
                    ),
                    (
                        "heart_rate",
                        "respiratory_rate",
                    ),
                    (
                        "oxygen_saturation",
                        "oxygen_delivery_method",
                        "oxygen_flow_lpm",
                    ),
                    "pain_score",
                )
            },
        ),
        (
            "Blood pressure",
            {
                "fields": (
                    (
                        "systolic_blood_pressure",
                        "diastolic_blood_pressure",
                    ),
                    (
                        "mean_arterial_pressure_value",
                        "pulse_pressure_value",
                    ),
                )
            },
        ),
        (
            "Body measurements",
            {
                "fields": (
                    (
                        "height_cm",
                        "weight_kg",
                    ),
                    (
                        "bmi_value",
                        "bmi_category_value",
                    ),
                )
            },
        ),
        (
            "Additional measurements",
            {
                "fields": (
                    "blood_glucose_mg_dl",
                    "notes",
                )
            },
        ),
        (
            "Record status",
            {
                "fields": (
                    "status",
                    "correction_reason",
                    "clinical_status_value",
                    "entered_in_error_reason",
                    "entered_in_error_at",
                    "entered_in_error_by",
                )
            },
        ),
        (
            "Audit",
            {
                "fields": (
                    "created_at",
                    "updated_at",
                )
            },
        ),
    )

    def save_model(
        self,
        request,
        obj,
        form,
        change,
    ):
        obj.save(actor=request.user)

    @admin.display(
        description="Blood pressure",
    )
    def blood_pressure(self, obj):
        return obj.blood_pressure_display

    @admin.display(
        description="BMI",
    )
    def bmi_value(self, obj):
        return obj.bmi or "Not calculated"

    @admin.display(
        description="BMI category",
    )
    def bmi_category_value(self, obj):
        return obj.bmi_category or "Not calculated"

    @admin.display(
        description="Mean arterial pressure",
    )
    def mean_arterial_pressure_value(self, obj):
        value = obj.mean_arterial_pressure

        if value is None:
            return "Not calculated"

        return f"{value} mmHg"

    @admin.display(
        description="Pulse pressure",
    )
    def pulse_pressure_value(self, obj):
        value = obj.pulse_pressure

        if value is None:
            return "Not calculated"

        return f"{value} mmHg"

    @admin.display(
        description="Clinical status",
    )
    def clinical_status_value(self, obj):
        return obj.clinical_status_display