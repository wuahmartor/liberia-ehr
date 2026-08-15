from datetime import timedelta

from django import forms
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.accounts.models import UserProfile
from apps.patients.models import Patient

from .models import CareShift

INPUT_CLASS = "w-full rounded-md border border-slate-300 px-3 py-2 text-xs"


class CareShiftForm(forms.ModelForm):
    class Meta:
        model = CareShift
        fields = ["name", "facility", "starts_at", "ends_at", "notes"]
        widgets = {
            "name": forms.TextInput(attrs={"class": INPUT_CLASS}),
            "facility": forms.Select(attrs={"class": INPUT_CLASS}),
            "starts_at": forms.DateTimeInput(
                attrs={"class": INPUT_CLASS, "type": "datetime-local"},
                format="%Y-%m-%dT%H:%M",
            ),
            "ends_at": forms.DateTimeInput(
                attrs={"class": INPUT_CLASS, "type": "datetime-local"},
                format="%Y-%m-%dT%H:%M",
            ),
            "notes": forms.TextInput(attrs={"class": INPUT_CLASS}),
        }

    def __init__(self, *args, actor=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["starts_at"].input_formats = ["%Y-%m-%dT%H:%M"]
        self.fields["ends_at"].input_formats = ["%Y-%m-%dT%H:%M"]
        profile = getattr(actor, "profile", None) if actor else None
        if profile and profile.role == UserProfile.Role.FACILITY_ADMIN:
            self.fields["facility"].queryset = self.fields["facility"].queryset.filter(
                pk=profile.facility_id
            )
            self.fields["facility"].required = True
            self.initial.setdefault("facility", profile.facility_id)
        if not self.is_bound:
            start = timezone.localtime().replace(second=0, microsecond=0)
            self.initial.setdefault("starts_at", start.strftime("%Y-%m-%dT%H:%M"))
            self.initial.setdefault(
                "ends_at", (start + timedelta(hours=8)).strftime("%Y-%m-%dT%H:%M")
            )


class AssignmentForm(forms.Form):
    shift = forms.ModelChoiceField(
        queryset=CareShift.objects.none(),
        widget=forms.Select(attrs={"class": INPUT_CLASS}),
    )
    staff = forms.ModelChoiceField(
        queryset=get_user_model().objects.none(),
        widget=forms.Select(attrs={"class": INPUT_CLASS}),
    )
    patients = forms.ModelMultipleChoiceField(
        queryset=Patient.objects.none(),
        widget=forms.SelectMultiple(attrs={"class": f"{INPUT_CLASS} min-h-40"}),
    )

    def __init__(self, *args, actor=None, selected_shift=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.actor = actor
        self.fields["shift"].queryset = CareShift.objects.filter(
            ends_at__gte=timezone.now() - timedelta(hours=24)
        )
        staff = (
            get_user_model()
            .objects.filter(
                is_active=True,
                profile__is_clinical_staff=True,
                profile__is_active_staff=True,
                profile__role__in=[
                    UserProfile.Role.NURSE,
                    UserProfile.Role.PATIENT_CARE_AIDE,
                ],
            )
            .select_related("profile")
        )
        if selected_shift and selected_shift.facility_id:
            staff = staff.filter(profile__facility=selected_shift.facility)
        self.fields["staff"].queryset = staff.order_by(
            "last_name", "first_name", "username"
        )
        self.fields["patients"].queryset = Patient.objects.active().order_by(
            "last_name", "first_name"
        )
        if selected_shift and selected_shift.facility_id:
            self.fields["patients"].queryset = self.fields["patients"].queryset.filter(
                registration_facility_id=selected_shift.facility_id
            )
        if selected_shift:
            self.fields["shift"].initial = selected_shift


class SelfAssignmentForm(forms.Form):
    shift = forms.ModelChoiceField(queryset=CareShift.objects.none())
    patients = forms.ModelMultipleChoiceField(queryset=Patient.objects.none())

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["shift"].queryset = CareShift.objects.filter(
            ends_at__gte=timezone.now()
        )
        self.fields["patients"].queryset = Patient.objects.active()
