from decimal import Decimal
import json

from django import forms
from django.core.exceptions import ValidationError
from django.db import transaction

from .models import FlowSheetEntry, FlowSheetFieldDefinition, FlowSheetValue


INPUT_CLASS = "w-full rounded-md border border-slate-300 bg-white px-2 py-1.5 text-[10px] focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500"


class FlowSheetEntryForm(forms.Form):
    assessment_type = forms.ChoiceField(choices=FlowSheetEntry.AssessmentType.choices, widget=forms.Select(attrs={"class": INPUT_CLASS}))
    recorded_at = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={"type": "datetime-local", "class": INPUT_CLASS}, format="%Y-%m-%dT%H:%M")
    )
    notes = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 2, "class": INPUT_CLASS, "placeholder": "Optional clinical context"}))

    def __init__(self, *args, definition, require_correction_reason=False, **kwargs):
        self.definition = definition
        self.require_correction_reason = require_correction_reason
        super().__init__(*args, **kwargs)
        if require_correction_reason:
            self.fields["correction_reason"] = forms.CharField(
                min_length=5,
                max_length=500,
                label="Correction reason",
                widget=forms.Textarea(attrs={"rows": 2, "class": INPUT_CLASS, "placeholder": "Explain why this correction is required"}),
            )
        for field in definition.fields.all():
            name = f"value_{field.pk}"
            common = {"label": field.label, "required": field.is_required and not field.show_when_field_key, "help_text": field.help_text}
            attrs = {"class": INPUT_CLASS, "data-flow-key": field.key, "x-model": f"values['{field.key}']"}
            if field.data_type == FlowSheetFieldDefinition.DataType.NUMBER:
                self.fields[name] = forms.DecimalField(**common, widget=forms.NumberInput(attrs={**attrs, "step": "any", "placeholder": field.unit or "Value"}))
            elif field.data_type == FlowSheetFieldDefinition.DataType.BOOLEAN:
                self.fields[name] = forms.TypedChoiceField(**common, coerce=lambda value: value == "true", empty_value=None, choices=(("", "Not assessed"), ("true", "Yes"), ("false", "No")), widget=forms.Select(attrs=attrs))
            elif field.data_type == FlowSheetFieldDefinition.DataType.CHOICE:
                self.fields[name] = forms.ChoiceField(**common, choices=[("", "Not assessed"), *[(choice, choice) for choice in field.choices]], widget=forms.Select(attrs=attrs))
            elif field.data_type == FlowSheetFieldDefinition.DataType.MULTI_CHOICE:
                self.fields[name] = forms.MultipleChoiceField(**common, choices=[(choice, choice) for choice in field.choices], widget=forms.SelectMultiple(attrs={**attrs, "class": f"{INPUT_CLASS} min-h-24", "data-multi-select": "true"}))
            else:
                self.fields[name] = forms.CharField(**common, widget=forms.TextInput(attrs=attrs))

    def organized_sections(self):
        sections = []
        by_name = {}
        for definition_field in self.definition.fields.all():
            section_name = definition_field.section or "General"
            if section_name not in by_name:
                section = {"name": section_name, "primary": [], "subsections": [], "subsection_map": {}}
                sections.append(section)
                by_name[section_name] = section
            section = by_name[section_name]
            item = {"definition": definition_field, "bound": self[f"value_{definition_field.pk}"]}
            if definition_field.subsection:
                subsection = section["subsection_map"].get(definition_field.subsection)
                if subsection is None:
                    subsection = {
                        "name": definition_field.subsection,
                        "fields": [],
                        "show_when_field_key": definition_field.show_when_field_key,
                        "show_when_value": definition_field.show_when_value,
                    }
                    section["subsections"].append(subsection)
                    section["subsection_map"][definition_field.subsection] = subsection
                subsection["fields"].append(item)
            else:
                section["primary"].append(item)
        return sections

    def clean(self):
        cleaned = super().clean()
        fields_by_key = {field.key: field for field in self.definition.fields.all()}
        for field in self.definition.fields.all():
            if not field.show_when_field_key:
                continue
            controller = fields_by_key.get(field.show_when_field_key)
            controller_value = cleaned.get(f"value_{controller.pk}") if controller else None
            if str(controller_value) != field.show_when_value:
                cleaned[f"value_{field.pk}"] = None
            elif field.is_required and cleaned.get(f"value_{field.pk}") in (None, "", []):
                self.add_error(f"value_{field.pk}", "This detail is required for the selected finding.")
        if not any(cleaned.get(f"value_{field.pk}") not in (None, "") for field in self.definition.fields.all()):
            raise ValidationError("Record at least one flowsheet value.")
        return cleaned

    @transaction.atomic
    def save(self, *, patient, encounter, actor, corrected_from=None, correction_reason=""):
        entry = FlowSheetEntry(
            patient=patient,
            encounter=encounter,
            flowsheet=self.definition,
            assessment_type=self.cleaned_data["assessment_type"],
            recorded_at=self.cleaned_data["recorded_at"],
            recorded_by=actor,
            notes=self.cleaned_data.get("notes", ""),
            corrected_from=corrected_from,
            correction_reason=(correction_reason or self.cleaned_data.get("correction_reason", "")).strip(),
            status=FlowSheetEntry.Status.CORRECTED if corrected_from else FlowSheetEntry.Status.FINAL,
        )
        entry.full_clean()
        entry.save()
        for field in self.definition.fields.all():
            raw = self.cleaned_data.get(f"value_{field.pk}")
            if raw in (None, ""):
                continue
            value = FlowSheetValue(entry=entry, field=field)
            if field.data_type == FlowSheetFieldDefinition.DataType.NUMBER:
                value.value_number = Decimal(raw)
                value.flag = field.classify_number(value.value_number)
            elif field.data_type == FlowSheetFieldDefinition.DataType.BOOLEAN:
                value.value_boolean = raw
            elif field.data_type == FlowSheetFieldDefinition.DataType.MULTI_CHOICE:
                value.value_text = json.dumps(raw)
            else:
                value.value_text = str(raw)
            value.full_clean()
            value.save()
        return entry


class EnteredInErrorForm(forms.Form):
    reason = forms.CharField(min_length=5, max_length=500, widget=forms.Textarea(attrs={"rows": 2, "class": INPUT_CLASS}))
