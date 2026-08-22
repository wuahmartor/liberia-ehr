from datetime import date
from django.db import migrations

NCBI = "https://www.ncbi.nlm.nih.gov/books/NBK613071/"
MEDLINE = "https://medlineplus.gov/ency/article/003468.htm"
MAYO_CRITICAL = "https://www.mayocliniclabs.com/-/media/it-mmfiles/Special-Instructions/8/A/6/DLMP_Critical_Values_-_Critical_Results_List"

TESTS = {
    "wbc": ("White blood cell count", "WBC", "6690-2", "10^3/uL", 4, 10, None, None, NCBI),
    "rbc": ("Red blood cell count", "RBC", "789-8", "10^6/uL", 4, 6, None, None, NCBI),
    "hemoglobin": ("Hemoglobin", "Hgb", "718-7", "g/dL", 12, 17, None, None, NCBI),
    "hematocrit": ("Hematocrit", "Hct", "4544-3", "%", 36, 52, None, None, NCBI),
    "platelets": ("Platelet count", "Platelets", "777-3", "10^3/uL", 150, 400, None, None, NCBI),
    "sodium": ("Sodium", "Na", "2951-2", "mmol/L", 135, 145, 120, 160, MEDLINE),
    "potassium": ("Potassium", "K", "2823-3", "mmol/L", 3.7, 5.2, 2.5, 6.0, MEDLINE),
    "chloride": ("Chloride", "Cl", "2075-0", "mmol/L", 96, 106, None, None, MEDLINE),
    "co2": ("Carbon dioxide total", "CO2", "2028-9", "mmol/L", 23, 29, None, None, MEDLINE),
    "glucose": ("Glucose", "Glucose", "2345-7", "mg/dL", 70, 100, 50, 400, MEDLINE),
    "bun": ("Blood urea nitrogen", "BUN", "3094-0", "mg/dL", 6, 20, None, None, MEDLINE),
    "creatinine": ("Creatinine", "Creatinine", "2160-0", "mg/dL", 0.6, 1.3, None, None, MEDLINE),
    "calcium": ("Calcium total", "Calcium", "17861-6", "mg/dL", 8.5, 10.2, 6.5, 13, MEDLINE),
    "protein": ("Total protein", "Protein", "2885-2", "g/dL", 6.0, 8.0, None, None, NCBI),
    "albumin": ("Albumin", "Albumin", "1751-7", "g/dL", 3.4, 5.4, None, None, MEDLINE),
    "bilirubin": ("Bilirubin total", "Bilirubin", "1975-2", "mg/dL", 0.1, 1.2, None, None, MEDLINE),
    "alp": ("Alkaline phosphatase", "ALP", "6768-6", "U/L", 20, 130, None, None, MEDLINE),
    "ast": ("Aspartate aminotransferase", "AST", "1920-8", "U/L", 8, 33, None, None, MEDLINE),
    "alt": ("Alanine aminotransferase", "ALT", "1742-6", "U/L", 4, 36, None, None, MEDLINE),
    "cholesterol": ("Total cholesterol", "Cholesterol", "2093-3", "mg/dL", 0, 199, None, None, NCBI),
    "hdl": ("HDL cholesterol", "HDL", "2085-9", "mg/dL", 40, 80, None, None, NCBI),
    "ldl": ("LDL cholesterol calculated", "LDL", "13457-7", "mg/dL", 0, 99, None, None, NCBI),
    "triglycerides": ("Triglycerides", "Triglycerides", "2571-8", "mg/dL", 50, 150, None, None, NCBI),
    "tsh": ("Thyroid stimulating hormone", "TSH", "3016-3", "mIU/L", 0.5, 5, None, None, NCBI),
    "pt": ("Prothrombin time", "PT", "5902-2", "seconds", 11, 14, None, None, NCBI),
    "inr": ("International normalized ratio", "INR", "6301-6", "ratio", 0.9, 1.2, None, None, NCBI),
    "aptt": ("Activated partial thromboplastin time", "aPTT", "14979-9", "seconds", 20, 40, None, None, NCBI),
    "a1c": ("Hemoglobin A1c", "A1c", "4548-4", "%", 0, 5.6, None, None, "https://www.cdc.gov/diabetes/diabetes-testing/prediabetes-a1c-test.html"),
}

PANELS = {
    "cbc": ("Complete Blood Count", "58410-2", ["wbc", "rbc", "hemoglobin", "hematocrit", "platelets"]),
    "bmp": ("Basic Metabolic Panel", "51990-0", ["sodium", "potassium", "chloride", "co2", "glucose", "bun", "creatinine", "calcium"]),
    "cmp": ("Comprehensive Metabolic Panel", "24323-8", ["sodium", "potassium", "chloride", "co2", "glucose", "bun", "creatinine", "calcium", "protein", "albumin", "bilirubin", "alp", "ast", "alt"]),
    "lipid": ("Lipid Panel", "57698-3", ["cholesterol", "hdl", "ldl", "triglycerides"]),
    "thyroid": ("Thyroid Panel", "24348-5", ["tsh"]),
    "coagulation": ("Coagulation Panel", "34528-0", ["pt", "inr", "aptt"]),
    "diabetes": ("Diabetes Monitoring", "", ["a1c", "glucose"]),
}

def seed(apps, schema_editor):
    Test = apps.get_model("laboratories", "LabTestDefinition")
    Range = apps.get_model("laboratories", "LabReferenceRange")
    Panel = apps.get_model("laboratories", "LabPanel")
    PanelTest = apps.get_model("laboratories", "LabPanelTest")
    tests = {}
    for code, (name, short, loinc, unit, low, high, critical_low, critical_high, source) in TESTS.items():
        test, _ = Test.objects.update_or_create(code=code, defaults={"name": name, "short_name": short, "loinc_code": loinc, "default_unit": unit, "specimen_type": "Whole blood" if code in ("wbc", "rbc", "hemoglobin", "hematocrit", "platelets", "a1c") else "Serum or plasma", "is_active": True})
        Range.objects.update_or_create(test=test, label="Seed adult interval — local validation required", sex="any", age_min_years=18, defaults={"lower_bound": low, "upper_bound": high, "critical_low": critical_low, "critical_high": critical_high, "unit": unit, "source_title": "NCBI/NIH, CDC, or MedlinePlus reference; critical thresholds from Mayo Clinic Laboratories where configured", "source_url": MAYO_CRITICAL if critical_low is not None or critical_high is not None else source, "source_version": "Accessed 2026-08-16", "effective_date": date(2026, 8, 16), "is_locally_validated": False})
        tests[code] = test
    for code, (name, loinc, members) in PANELS.items():
        panel, _ = Panel.objects.update_or_create(code=code, defaults={"name": name, "loinc_code": loinc, "description": "LOINC-aligned starter panel; local laboratory configuration governs final membership.", "is_active": True})
        for position, test_code in enumerate(members, 1):
            PanelTest.objects.update_or_create(panel=panel, test=tests[test_code], defaults={"display_order": position, "is_required": True})

class Migration(migrations.Migration):
    dependencies = [("laboratories", "0001_initial")]
    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
