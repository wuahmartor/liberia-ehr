from datetime import date
from django.db import migrations

SOURCE = "https://www.ncbi.nlm.nih.gov/books/NBK613071/"
TESTS = {
    "magnesium": ("Magnesium", "Magnesium", "19123-9", "mg/dL", 1.7, 2.4),
    "phosphate": ("Phosphate", "Phosphate", "2777-1", "mg/dL", 2.5, 4.5),
    "iron": ("Serum iron", "Iron", "2498-4", "ug/dL", 60, 170),
    "ferritin": ("Ferritin", "Ferritin", "2276-4", "ng/mL", 12, 300),
    "tibc": ("Total iron binding capacity", "TIBC", "2500-7", "ug/dL", 250, 450),
    "troponin": ("Troponin I", "Troponin", "10839-9", "ng/mL", 0, 0.04),
    "crp": ("C-reactive protein", "CRP", "1988-5", "mg/L", 0, 10),
    "esr": ("Erythrocyte sedimentation rate", "ESR", "4537-7", "mm/hr", 0, 20),
    "lipase": ("Lipase", "Lipase", "3040-3", "U/L", 0, 160),
    "amylase": ("Amylase", "Amylase", "1798-8", "U/L", 30, 125),
    "lactate": ("Lactate", "Lactate", "2524-7", "mmol/L", 0.5, 2.2),
    "uric-acid": ("Uric acid", "Uric acid", "3084-1", "mg/dL", 3.5, 7.2),
}
PANELS = {
    "electrolytes": ("Electrolyte Panel", "55231-5", ["sodium", "potassium", "chloride", "co2", "magnesium", "phosphate"]),
    "renal": ("Renal Function Panel", "24362-6", ["sodium", "potassium", "chloride", "co2", "bun", "creatinine", "calcium", "phosphate", "albumin"]),
    "hepatic": ("Hepatic Function Panel", "24325-3", ["protein", "albumin", "bilirubin", "alp", "ast", "alt"]),
    "iron-studies": ("Iron Studies", "", ["iron", "ferritin", "tibc"]),
    "cardiac-markers": ("Cardiac Marker Panel", "", ["troponin"]),
    "inflammatory": ("Inflammatory Markers", "", ["crp", "esr"]),
    "pancreatic": ("Pancreatic Enzymes", "", ["lipase", "amylase"]),
}

def expand(apps, schema_editor):
    Test = apps.get_model("laboratories", "LabTestDefinition")
    Range = apps.get_model("laboratories", "LabReferenceRange")
    Panel = apps.get_model("laboratories", "LabPanel")
    PanelTest = apps.get_model("laboratories", "LabPanelTest")
    for code, (name, short, loinc, unit, low, high) in TESTS.items():
        test, _ = Test.objects.update_or_create(code=code, defaults={"name": name, "short_name": short, "loinc_code": loinc, "default_unit": unit, "specimen_type": "Serum or plasma", "is_active": True})
        Range.objects.update_or_create(test=test, label="Seed adult interval — local validation required", sex="any", age_min_years=18, defaults={"lower_bound": low, "upper_bound": high, "unit": unit, "source_title": "NIH/NCBI adult reference interval starter data", "source_url": SOURCE, "source_version": "Accessed 2026-08-16", "effective_date": date(2026, 8, 16), "is_locally_validated": False})
    tests = {test.code: test for test in Test.objects.filter(is_active=True)}
    for code, (name, loinc, members) in PANELS.items():
        panel, _ = Panel.objects.update_or_create(code=code, defaults={"name": name, "loinc_code": loinc, "description": "Starter panel; performing laboratory controls final membership.", "is_active": True})
        for order, member in enumerate(members, 1):
            if member in tests:
                PanelTest.objects.update_or_create(panel=panel, test=tests[member], defaults={"display_order": order, "is_required": True})

class Migration(migrations.Migration):
    dependencies = [("laboratories", "0004_laborder_indication_diagnosis")]
    operations = [migrations.RunPython(expand, migrations.RunPython.noop)]
