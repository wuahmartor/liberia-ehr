"""
============================================================
CLINICAL NOTES APP CONFIGURATION

File:
apps/clinical_notes/apps.py

Purpose:
- Configure the Clinical Notes Django application.
============================================================
"""

from django.apps import AppConfig


class ClinicalNotesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.clinical_notes"
    verbose_name = "Clinical Notes"
