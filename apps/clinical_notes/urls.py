"""
============================================================
CLINICAL NOTES URLS

File:
apps/clinical_notes/urls.py

Purpose:
- Provide patient-centered clinical note routes.
- Support UUID patient identifiers.
- Support UUID clinical note identifiers.
============================================================
"""

from django.urls import path

from .views import (
    ClinicalNoteCreateView,
    ClinicalNoteDetailView,
    ClinicalNoteListView,
    ClinicalNoteSignView,
    ClinicalNoteUpdateView,
)


app_name = "clinical_notes"


urlpatterns = [

    # ========================================================
    # PATIENT CLINICAL NOTE HISTORY
    # ========================================================

    path(
        "patient/<uuid:patient_pk>/",
        ClinicalNoteListView.as_view(),
        name="list",
    ),


    # ========================================================
    # CREATE CLINICAL NOTE
    # ========================================================

    path(
        "patient/<uuid:patient_pk>/new/",
        ClinicalNoteCreateView.as_view(),
        name="create",
    ),


    # ========================================================
    # CLINICAL NOTE DETAIL
    # ========================================================

    path(
        "<uuid:pk>/",
        ClinicalNoteDetailView.as_view(),
        name="detail",
    ),


    # ========================================================
    # UPDATE DRAFT CLINICAL NOTE
    # ========================================================

    path(
        "<uuid:pk>/edit/",
        ClinicalNoteUpdateView.as_view(),
        name="update",
    ),


    # ========================================================
    # SIGN CLINICAL NOTE
    # ========================================================

    path(
        "<uuid:pk>/sign/",
        ClinicalNoteSignView.as_view(),
        name="sign",
    ),

]