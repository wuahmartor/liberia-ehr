from django.db import migrations


SYSTEM_FIELDS = {
    "Neurological": [
        ("level-of-consciousness", "Level of consciousness", "choice", ["Alert", "Lethargic", "Obtunded", "Stuporous", "Unresponsive"], True),
        ("orientation", "Orientation domains", "multi_choice", ["Person", "Place", "Time", "Situation", "Not oriented"], True),
        ("neuro-pupils", "Pupil findings", "multi_choice", ["PERRLA", "Brisk", "Sluggish", "Fixed", "Unequal", "Unable to assess"], True),
        ("neuro-speech", "Speech / communication", "multi_choice", ["Clear", "Slurred", "Expressive aphasia", "Receptive aphasia", "Nonverbal", "Language barrier"], True),
        ("neuro-motor", "Motor findings", "multi_choice", ["Moves all extremities", "Left weakness", "Right weakness", "Upper-extremity weakness", "Lower-extremity weakness", "Flaccid", "Tremor", "Seizure activity"], True),
        ("neuro-sensation", "Sensory findings", "multi_choice", ["Intact", "Numbness", "Tingling", "Decreased sensation", "Absent sensation"], True),
    ],
    "Respiratory": [
        ("respiratory-pattern", "Respiratory pattern / effort", "multi_choice", ["Regular", "Tachypneic", "Bradypneic", "Labored", "Shallow", "Accessory muscle use", "Apneic"], True),
        ("lung-sounds", "Lung sounds", "multi_choice", ["Clear", "Diminished", "Crackles", "Wheezes", "Rhonchi", "Absent"], True),
        ("lung-location", "Affected lung fields", "multi_choice", ["Right upper", "Right middle", "Right lower", "Left upper", "Left lower", "Anterior", "Posterior", "Diffuse"], True),
        ("oxygen-device", "Oxygen / airway support", "multi_choice", ["Room air", "Nasal cannula", "Simple mask", "Venturi mask", "Non-rebreather", "High-flow nasal cannula", "CPAP/BiPAP", "Mechanical ventilation", "Tracheostomy"], True),
        ("oxygen-flow", "Oxygen flow / settings", "text", [], False),
        ("respiratory-secretions", "Cough / sputum / secretions", "multi_choice", ["Dry cough", "Productive cough", "Strong cough", "Weak cough", "Clear", "White", "Yellow", "Green", "Blood-tinged", "Thick", "Thin"], False),
        ("respiratory-symptoms", "Respiratory symptoms", "multi_choice", ["Dyspnea at rest", "Dyspnea on exertion", "Orthopnea", "Pleuritic pain", "Cyanosis"], False),
    ],
    "Cardiovascular": [
        ("cardiac-rhythm", "Rhythm", "multi_choice", ["Regular", "Irregular", "Sinus rhythm", "Atrial fibrillation", "Tachycardia", "Bradycardia", "Paced", "Telemetry monitored"], True),
        ("heart-sounds", "Heart sounds", "multi_choice", ["S1/S2 normal", "Murmur", "Gallop", "Rub", "Distant"], True),
        ("peripheral-pulses", "Peripheral pulses", "multi_choice", ["2+ normal", "Bounding", "Weak", "Absent", "Unequal", "Doppler only"], True),
        ("capillary-refill", "Capillary refill", "choice", ["Less than 2 seconds", "2–3 seconds", "Greater than 3 seconds"], True),
        ("edema", "Edema", "choice", ["None", "Present"], True),
        ("cardiovascular-symptoms", "Cardiovascular symptoms", "multi_choice", ["Chest pain", "Palpitations", "Dizziness", "Syncope", "Fatigue", "Claudication", "None reported"], True),
    ],
    "Gastrointestinal": [
        ("bowel-sounds-ruq", "Bowel sounds — RUQ", "choice", ["Normoactive", "Hypoactive", "Hyperactive", "Absent"], True),
        ("bowel-sounds-luq", "Bowel sounds — LUQ", "choice", ["Normoactive", "Hypoactive", "Hyperactive", "Absent"], True),
        ("bowel-sounds-rlq", "Bowel sounds — RLQ", "choice", ["Normoactive", "Hypoactive", "Hyperactive", "Absent"], True),
        ("bowel-sounds-llq", "Bowel sounds — LLQ", "choice", ["Normoactive", "Hypoactive", "Hyperactive", "Absent"], True),
        ("abdomen", "Abdominal findings", "multi_choice", ["Soft", "Firm", "Flat", "Rounded", "Distended", "Tender", "Rigid", "Guarding", "Rebound tenderness"], True),
        ("abdominal-location", "Affected quadrant / location", "multi_choice", ["RUQ", "LUQ", "RLQ", "LLQ", "Epigastric", "Periumbilical", "Suprapubic", "Diffuse"], True),
        ("gi-symptoms", "GI symptoms", "multi_choice", ["Nausea", "Vomiting", "Diarrhea", "Constipation", "Incontinence", "Blood in stool", "No symptoms reported"], True),
        ("last-bowel-movement", "Last bowel movement", "text", [], True),
        ("nutrition-route", "Nutrition route", "multi_choice", ["Oral", "NPO", "NG/OG tube", "Gastrostomy", "Jejunostomy", "Parenteral nutrition"], True),
    ],
    "Genitourinary": [
        ("urinary-method", "Urinary elimination", "multi_choice", ["Voiding", "Indwelling catheter", "External catheter", "Intermittent catheterization", "Urostomy", "Dialysis", "Anuric"], True),
        ("urine-characteristics", "Urine characteristics", "multi_choice", ["Clear", "Cloudy", "Concentrated", "Sediment", "Hematuria", "Malodorous", "Unable to assess"], True),
        ("gu-symptoms", "GU symptoms", "multi_choice", ["Dysuria", "Urgency", "Frequency", "Retention", "Incontinence", "Flank pain", "No symptoms reported"], True),
    ],
    "Musculoskeletal and Mobility": [
        ("mobility", "Mobility level", "multi_choice", ["Independent", "Standby assist", "One-person assist", "Two-person assist", "Mechanical lift", "Wheelchair", "Bedrest"], True),
        ("musculoskeletal-location", "Affected location", "multi_choice", ["Shoulder", "Arm", "Elbow", "Wrist", "Hand", "Hip", "Thigh", "Knee", "Lower leg", "Ankle", "Foot", "Neck", "Back"], True),
        ("musculoskeletal-laterality", "Laterality", "multi_choice", ["Left", "Right", "Bilateral", "Midline"], True),
        ("musculoskeletal-symptoms", "Symptoms / findings", "multi_choice", ["Pain", "Weakness", "Swelling", "Deformity", "Limited range of motion", "Contracture", "Numbness", "Tingling", "Paralysis"], True),
        ("gait", "Gait / transfer", "multi_choice", ["Steady", "Unsteady", "Shuffling", "Antalgic", "Unable to ambulate", "Unable to assess"], True),
        ("assistive-device", "Assistive device", "multi_choice", ["None", "Cane", "Walker", "Crutches", "Wheelchair", "Prosthesis", "Brace/splint"], True),
    ],
    "Integumentary": [
        ("skin-integrity", "Skin integrity", "multi_choice", ["Intact", "Pressure injury", "Skin tear", "Incision", "Wound", "Rash", "Bruising", "Moisture-associated damage"], True),
        ("skin-location", "Location", "multi_choice", ["Head/neck", "Chest", "Abdomen", "Back", "Sacrum/coccyx", "Left arm", "Right arm", "Left leg", "Right leg", "Left heel", "Right heel", "Perineum"], True),
        ("skin-color", "Color / temperature / moisture", "multi_choice", ["Color appropriate", "Pale", "Cyanotic", "Jaundiced", "Flushed", "Warm", "Cool", "Hot", "Dry", "Diaphoretic", "Clammy"], True),
        ("wound-details", "Wound dimensions, stage, drainage and dressing", "text", [], True),
    ],
    "Pain": [
        ("pain-score", "Pain score", "number", [], True),
        ("pain-location", "Pain location", "multi_choice", ["Head", "Neck", "Chest", "Abdomen", "Back", "Left arm", "Right arm", "Left leg", "Right leg", "Generalized", "Other"], True),
        ("pain-laterality", "Laterality", "multi_choice", ["Left", "Right", "Bilateral", "Midline", "Not applicable"], True),
        ("pain-quality", "Pain quality", "multi_choice", ["Aching", "Burning", "Cramping", "Dull", "Pressure", "Sharp", "Shooting", "Stabbing", "Throbbing"], True),
        ("pain-pattern", "Pattern", "multi_choice", ["Constant", "Intermittent", "With activity", "At rest", "Radiating"], True),
        ("pain-intervention", "Intervention", "multi_choice", ["Medication", "Repositioning", "Heat", "Cold", "Elevation", "Relaxation", "Provider notified", "Declined intervention"], True),
    ],
    "Safety": [
        ("fall-precautions", "Fall precautions in place", "boolean", [], True),
        ("safety-concerns", "Safety risks", "multi_choice", ["Fall risk", "Aspiration risk", "Seizure precautions", "Elopement risk", "Self-harm risk", "Bleeding precautions", "Isolation precautions"], True),
        ("safety-interventions", "Safety interventions", "multi_choice", ["Bed low/locked", "Call light in reach", "Bed alarm", "Chair alarm", "Non-skid footwear", "Sitter", "Frequent rounding", "Side rails per policy"], True),
        ("restraints", "Restraints", "choice", ["None", "In use per order", "Alternatives attempted"], True),
    ],
}


EDEMA_FIELDS = [
    ("edema-location", "Edema location", "multi_choice", ["Face", "Sacral", "Left arm", "Right arm", "Left hand", "Right hand", "Left leg", "Right leg", "Left ankle", "Right ankle", "Left foot", "Right foot", "Generalized"]),
    ("edema-laterality", "Edema laterality", "multi_choice", ["Left", "Right", "Bilateral", "Generalized"]),
    ("edema-grade", "Edema grade", "choice", ["Non-pitting", "1+", "2+", "3+", "4+"]),
]


def expand_dictionary(apps, schema_editor):
    Definition = apps.get_model("flowsheets", "FlowSheetDefinition")
    Field = apps.get_model("flowsheets", "FlowSheetFieldDefinition")
    nursing = Definition.objects.filter(slug="nursing-systems-assessment").first()
    if not nursing:
        return
    order = 0
    for section, fields in SYSTEM_FIELDS.items():
        status_key = {
            "Neurological": "neurological-status", "Respiratory": "respiratory-status", "Cardiovascular": "cardiovascular-status",
            "Gastrointestinal": "gastrointestinal-status", "Genitourinary": "genitourinary-status", "Musculoskeletal and Mobility": "musculoskeletal-status",
            "Integumentary": "integumentary-status", "Pain": "pain-status", "Safety": "safety-status",
        }[section]
        status = Field.objects.get(flowsheet=nursing, key=status_key)
        order += 100
        status.display_order = order
        status.save(update_fields=["display_order"])
        for key, label, data_type, choices, required in fields:
            order += 1
            defaults = {
                "label": label, "data_type": data_type, "choices": choices, "section": section,
                "subsection": "Focused abnormal assessment", "show_when_field_key": status_key,
                "show_when_value": "Abnormal", "display_order": order, "is_required": required,
            }
            if key == "pain-score":
                defaults.update({"unit": "/10", "normal_min": 0, "normal_max": 3, "critical_max": 8})
            Field.objects.update_or_create(flowsheet=nursing, key=key, defaults=defaults)
        if section == "Cardiovascular":
            for key, label, data_type, choices in EDEMA_FIELDS:
                order += 1
                Field.objects.update_or_create(
                    flowsheet=nursing, key=key,
                    defaults={"label": label, "data_type": data_type, "choices": choices, "section": section,
                              "subsection": "Edema details", "show_when_field_key": "edema", "show_when_value": "Present",
                              "display_order": order, "is_required": True},
                )
    legacy_bowel = Field.objects.filter(flowsheet=nursing, key="bowel-sounds").first()
    if legacy_bowel:
        legacy_bowel.label = "Overall bowel sounds summary"
        legacy_bowel.section = "Gastrointestinal"
        legacy_bowel.subsection = "Focused abnormal assessment"
        legacy_bowel.show_when_field_key = "gastrointestinal-status"
        legacy_bowel.show_when_value = "Abnormal"
        legacy_bowel.is_required = False
        legacy_bowel.display_order = 499
        legacy_bowel.save()


class Migration(migrations.Migration):
    dependencies = [("flowsheets", "0005_flowsheetentry_assessment_type_and_more")]
    operations = [migrations.RunPython(expand_dictionary, migrations.RunPython.noop)]
