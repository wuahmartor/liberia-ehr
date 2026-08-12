from django import forms

from .models import ClinicalAlert, ClinicalRule

CONTROL = "w-full rounded-md border border-slate-300 bg-white px-2.5 py-2 text-xs"


class ClinicalRuleForm(forms.ModelForm):
    class Meta:
        model = ClinicalRule
        exclude = ("created_by", "created_at", "updated_at")
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
            "recommendation": forms.Textarea(attrs={"rows": 3}),
            "trigger_definition": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = CONTROL


class AlertActionForm(forms.Form):
    action = forms.ChoiceField(
        choices=(
            ("acknowledged", "Acknowledge"),
            ("resolved", "Resolve"),
            ("overridden", "Override"),
        ),
        widget=forms.Select(attrs={"class": CONTROL}),
    )
    note = forms.CharField(widget=forms.Textarea(attrs={"class": CONTROL, "rows": 3}))

    def clean(self):
        cleaned = super().clean()
        if (
            cleaned.get("action") == ClinicalAlert.Status.OVERRIDDEN
            and not cleaned.get("note", "").strip()
        ):
            self.add_error("note", "An override reason is required.")
        return cleaned
