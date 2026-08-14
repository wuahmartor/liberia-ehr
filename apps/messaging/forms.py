from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist

from apps.patients.models import Patient

from .models import Conversation, Message
from .selectors import eligible_staff

User = get_user_model()


class StaffLabelMixin:
    def label_from_instance(self, user):
        name = user.get_full_name().strip() or user.username
        try:
            profile = user.profile
        except ObjectDoesNotExist:
            profile = None
        title = profile.job_title.strip() if profile and profile.job_title else ""
        if profile and not title:
            title = profile.get_role_display()
        return f"{name} — {title or 'Staff'}"


class StaffChoiceField(StaffLabelMixin, forms.ModelChoiceField):
    pass


class StaffMultipleChoiceField(StaffLabelMixin, forms.ModelMultipleChoiceField):
    pass


class ComposeMessageForm(forms.Form):
    class ContextType:
        GENERAL = "general"
        PATIENT = "patient"

    context_type = forms.ChoiceField(
        label="Message context",
        choices=Conversation.ContextType.choices,
    )
    subject_category = forms.ChoiceField(
        label="Patient subject category",
        choices=(("", "Select a patient-related subject"), *Conversation.SubjectCategory.choices),
        required=False,
    )
    subject = forms.CharField(label="Subject details", max_length=200, required=False)
    patients = forms.ModelMultipleChoiceField(
        queryset=Patient.objects.none(),
        required=False,
        help_text="Select one or more patients related to this message.",
    )
    audience = forms.ChoiceField(
        choices=(
            ("specific", "Specific staff members"),
            ("care_team", "Care teams for selected patients"),
            ("all_staff", "All authorized staff"),
        )
    )
    recipients = StaffMultipleChoiceField(
        queryset=User.objects.none(),
        required=False,
        help_text="Use Command/Ctrl to select multiple staff members.",
    )
    body = forms.CharField(
        label="Message",
        max_length=4000,
        widget=forms.Textarea(attrs={"rows": 5, "placeholder": "Write a secure message…"}),
    )

    def __init__(self, *args, current_user, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["patients"].queryset = Patient.objects.active().order_by(
            "last_name", "first_name"
        )
        self.fields["recipients"].queryset = eligible_staff().exclude(pk=current_user.pk)
        for field in self.fields.values():
            field.widget.attrs["class"] = (
                "w-full rounded-lg border border-slate-300 bg-white px-3 py-2 "
                "text-xs text-slate-900 focus:border-ehr-500 focus:ring-2 focus:ring-ehr-100"
            )
        self.fields["patients"].widget.attrs.update(
            {"x-ref": "patientSelect", "class": "hidden", "aria-hidden": "true"}
        )
        self.fields["recipients"].widget.attrs.update(
            {"x-ref": "recipientSelect", "class": "hidden", "aria-hidden": "true"}
        )

    def clean(self):
        cleaned = super().clean()
        audience = cleaned.get("audience")
        context_type = cleaned.get("context_type")
        patients = cleaned.get("patients")
        recipients = cleaned.get("recipients")
        subject_category = cleaned.get("subject_category")
        subject = (cleaned.get("subject") or "").strip()

        if context_type == self.ContextType.PATIENT and not patients:
            self.add_error("patients", "Select at least one patient.")
        if audience == "care_team" and not patients:
            self.add_error("patients", "Care-team broadcasts require at least one patient.")
        if audience == "specific" and not recipients:
            self.add_error("recipients", "Select at least one staff recipient.")

        if context_type == self.ContextType.PATIENT:
            if not subject_category:
                self.add_error(
                    "subject_category", "Select a patient-related subject category."
                )
            elif not self.errors.get("subject_category"):
                category_label = dict(Conversation.SubjectCategory.choices)[subject_category]
                cleaned["subject"] = (
                    f"{category_label} — {subject}" if subject else category_label
                )
        elif not subject:
            self.add_error("subject", "Enter a subject for this message.")
        else:
            cleaned["subject"] = subject
        return cleaned


class MessageForm(forms.ModelForm):
    class Meta:
        model = Message
        fields = ("body",)
        widgets = {
            "body": forms.Textarea(
                attrs={
                    "rows": 3,
                    "placeholder": "Reply securely…",
                    "class": (
                        "w-full rounded-lg border border-slate-300 bg-white px-3 py-2 "
                        "text-xs focus:border-ehr-500 focus:ring-2 focus:ring-ehr-100"
                    ),
                }
            )
        }
