"""
============================================================
CLINICAL NOTES ADMIN

File:
apps/clinical_notes/admin.py
============================================================
"""

from django.contrib import admin

from .models import ClinicalNote


@admin.register(ClinicalNote)
class ClinicalNoteAdmin(admin.ModelAdmin):

    list_display = (
        "patient",
        "note_type",
        "status",
        "author",
        "encounter",
        "created_at",
        "signed_at",
    )

    list_filter = (
        "note_type",
        "status",
        "created_at",
        "signed_at",
    )

    search_fields = (
        "patient__first_name",
        "patient__middle_name",
        "patient__last_name",
        "title",
        "subjective",
        "objective",
        "assessment",
        "plan",
        "content",
    )

    readonly_fields = (
        "id",
        "created_at",
        "updated_at",
        "signed_at",
        "amended_at",
        "voided_at",
    )

    autocomplete_fields = (
        "patient",
        "encounter",
        "author",
        "signed_by",
        "created_by",
        "updated_by",
        "amended_by",
        "voided_by",
    )

    ordering = (
        "-created_at",
    )

    fieldsets = (

        (
            "Clinical Note",
            {
                "fields": (
                    "id",
                    "patient",
                    "encounter",
                    "note_type",
                    "status",
                    "title",
                )
            },
        ),

        (
            "Clinical Documentation",
            {
                "fields": (
                    "subjective",
                    "objective",
                    "assessment",
                    "plan",
                    "content",
                )
            },
        ),

        (
            "Authorship",
            {
                "fields": (
                    "author",
                    "signed_by",
                    "signed_at",
                )
            },
        ),

        (
            "Amendment",
            {
                "classes": (
                    "collapse",
                ),
                "fields": (
                    "amended_by",
                    "amended_at",
                    "amendment_reason",
                ),
            },
        ),

        (
            "Void Information",
            {
                "classes": (
                    "collapse",
                ),
                "fields": (
                    "voided_by",
                    "voided_at",
                    "void_reason",
                ),
            },
        ),

        (
            "Audit",
            {
                "classes": (
                    "collapse",
                ),
                "fields": (
                    "created_by",
                    "created_at",
                    "updated_by",
                    "updated_at",
                ),
            },
        ),
    )
