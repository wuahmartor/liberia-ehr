from django.db import migrations


LOCATION_CHOICES = [
    "Neck",
    "Back",
    "Shoulder",
    "Upper arm",
    "Elbow",
    "Forearm",
    "Wrist",
    "Hand",
    "Thumb",
    "Index finger",
    "Middle finger",
    "Ring finger",
    "Little finger",
    "Hip",
    "Thigh",
    "Knee",
    "Lower leg",
    "Ankle",
    "Foot",
    "Great toe",
    "Second toe",
    "Third toe",
    "Fourth toe",
    "Fifth toe",
]


FIELD_UPDATES = {
    "mobility": {"display_order": 610},
    "gait": {"display_order": 620},
    "range-of-motion": {
        "display_order": 630,
        "data_type": "multi_choice",
        "choices": ["Full", "Limited", "Absent", "Passive only", "Pain with movement", "Unable to assess"],
        "is_required": True,
    },
    "musculoskeletal-location": {"display_order": 631, "choices": LOCATION_CHOICES},
    "musculoskeletal-laterality": {"display_order": 632},
    "musculoskeletal-symptoms": {"display_order": 633},
    "assistive-device": {"display_order": 640},
}


def refine_musculoskeletal(apps, schema_editor):
    Definition = apps.get_model("flowsheets", "FlowSheetDefinition")
    Field = apps.get_model("flowsheets", "FlowSheetFieldDefinition")
    nursing = Definition.objects.filter(slug="nursing-systems-assessment").first()
    if not nursing:
        return
    status = Field.objects.filter(flowsheet=nursing, key="musculoskeletal-status").first()
    if status:
        status.display_order = 600
        status.save(update_fields=["display_order"])
    for key, updates in FIELD_UPDATES.items():
        field = Field.objects.filter(flowsheet=nursing, key=key).first()
        if not field:
            continue
        for attribute, value in updates.items():
            setattr(field, attribute, value)
        field.save()


class Migration(migrations.Migration):
    dependencies = [("flowsheets", "0006_expand_nursing_assessment_dictionary")]
    operations = [migrations.RunPython(refine_musculoskeletal, migrations.RunPython.noop)]
