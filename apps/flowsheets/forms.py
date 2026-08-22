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

    def __init__(self, *args, definition, require_correction_reason=False, previous_entry=None, **kwargs):
        self.definition = definition
        self.require_correction_reason = require_correction_reason
        self.previous_entry = previous_entry
        self.previous_values = {
            value.field_id: value for value in previous_entry.values.all()
        } if previous_entry else {}
        self.deviation_alerts = []
        super().__init__(*args, **kwargs)
        self.fields["acknowledge_deviation"] = forms.TypedChoiceField(
            required=False,
            label="I reviewed the deviation against the previous recording and confirm this value is accurate.",
            choices=(("", "Select"), ("true", "Yes — reviewed and confirmed")),
            coerce=lambda value: value == "true",
            empty_value=False,
            widget=forms.Select(attrs={"class": INPUT_CLASS}),
        )
        if require_correction_reason:
            self.fields["correction_reason"] = forms.CharField(
                min_length=5,
                max_length=500,
                label="Correction reason",
                widget=forms.Textarea(attrs={"rows": 2, "class": INPUT_CLASS, "placeholder": "Explain why this correction is required"}),
            )
        for field in definition.fields.filter(is_active=True):
            name = f"value_{field.pk}"
            common = {"label": field.label, "required": False, "help_text": field.help_text}
            attrs = {"class": INPUT_CLASS, "data-flow-key": field.key, "x-model": f"values['{field.key}']"}
            if field.data_type == FlowSheetFieldDefinition.DataType.NUMBER:
                self.fields[name] = forms.DecimalField(**common, widget=forms.NumberInput(attrs={**attrs, "step": "any", "placeholder": field.unit or "Value"}))
                if field.key == "gcs-total":
                    self.fields[name].required = False
                    self.fields[name].widget.attrs["readonly"] = "readonly"
            elif field.data_type == FlowSheetFieldDefinition.DataType.BOOLEAN:
                self.fields[name] = forms.TypedChoiceField(**common, coerce=lambda value: value == "true", empty_value=None, choices=(("", "Not assessed"), ("true", "Yes"), ("false", "No")), widget=forms.Select(attrs=attrs))
            elif field.data_type == FlowSheetFieldDefinition.DataType.CHOICE:
                self.fields[name] = forms.ChoiceField(**common, choices=[("", "Not assessed"), *[(choice, choice) for choice in field.choices]], widget=forms.Select(attrs=attrs))
            elif field.data_type == FlowSheetFieldDefinition.DataType.MULTI_CHOICE:
                self.fields[name] = forms.MultipleChoiceField(
                    **common,
                    choices=[(choice, choice) for choice in field.choices],
                    widget=forms.SelectMultiple(
                        attrs={
                            **attrs,
                            "class": "hidden",
                            "aria-hidden": "true",
                            "tabindex": "-1",
                            "x-ref": "stored",
                        }
                    ),
                )
            else:
                self.fields[name] = forms.CharField(**common, widget=forms.TextInput(attrs=attrs))

            previous_value = self.previous_values.get(field.pk)
            if previous_value:
                self.fields[name].widget.attrs["data-previous-value"] = (
                    str(previous_value.value_number)
                    if previous_value.value_number is not None
                    else previous_value.display_value
                )

    def organized_sections(self):
        sections = []
        by_name = {}
        for definition_field in self.definition.fields.filter(is_active=True):
            section_name = definition_field.section or "General"
            if section_name not in by_name:
                section = {"name": section_name, "primary": [], "subsections": [], "subsection_map": {}}
                sections.append(section)
                by_name[section_name] = section
            section = by_name[section_name]
            item = {
                "definition": definition_field,
                "bound": self[f"value_{definition_field.pk}"],
                "previous": self.previous_values.get(definition_field.pk),
                "previous_is_abnormal": self._previous_is_abnormal(
                    definition_field, self.previous_values.get(definition_field.pk)
                ),
            }
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

    @staticmethod
    def _previous_is_abnormal(field, value):
        if not value:
            return False
        if value.value_number is not None:
            return (
                (field.normal_min is not None and value.value_number < field.normal_min)
                or (field.normal_max is not None and value.value_number > field.normal_max)
            )
        text = value.display_value.strip().lower()
        normal_values = {"wnl", "normal", "none", "no", "clear / vesicular", "intact"}
        if text in normal_values:
            return False
        return bool(field.show_when_field_key or field.key.endswith("-status") or text)

    def clean(self):
        cleaned = super().clean()
        fields_by_key = {field.key: field for field in self.definition.fields.filter(is_active=True)}
        for field in self.definition.fields.filter(is_active=True):
            if not field.show_when_field_key:
                continue
            controller = fields_by_key.get(field.show_when_field_key)
            controller_value = cleaned.get(f"value_{controller.pk}") if controller else None
            matches = (
                controller_value not in (None, "", [])
                if field.show_when_value == "*"
                else (
                    field.show_when_value in controller_value
                    if isinstance(controller_value, (list, tuple))
                    else str(controller_value) == field.show_when_value
                )
            )
            if not matches:
                cleaned[f"value_{field.pk}"] = None
        if not any(cleaned.get(f"value_{field.pk}") not in (None, "", []) for field in self.definition.fields.filter(is_active=True)):
            raise ValidationError("Record at least one flowsheet value.")

        fields_by_key = {field.key: field for field in self.definition.fields.filter(is_active=True)}
        gcs_components = []
        for key in ("gcs-eye", "gcs-verbal", "gcs-motor"):
            field = fields_by_key.get(key)
            raw = cleaned.get(f"value_{field.pk}") if field else None
            if not raw or str(raw).startswith("NT"):
                gcs_components = []
                break
            try:
                gcs_components.append(int(str(raw).split()[0]))
            except (TypeError, ValueError):
                gcs_components = []
                break
        total_field = fields_by_key.get("gcs-total")
        if total_field and len(gcs_components) == 3:
            cleaned[f"value_{total_field.pk}"] = Decimal(sum(gcs_components))

        for field in self.definition.fields.filter(is_active=True):
            if field.data_type != FlowSheetFieldDefinition.DataType.NUMBER:
                continue
            current = cleaned.get(f"value_{field.pk}")
            previous = self.previous_values.get(field.pk)
            if current in (None, "") or not previous or previous.value_number is None:
                continue
            current = Decimal(current)
            prior = previous.value_number
            if prior == 0:
                percent_change = Decimal("100") if current != 0 else Decimal("0")
            else:
                percent_change = abs((current - prior) / prior) * Decimal("100")
            if percent_change > Decimal("10"):
                self.deviation_alerts.append(
                    {
                        "field": field,
                        "previous": prior,
                        "current": current,
                        "percent": percent_change.quantize(Decimal("0.1")),
                    }
                )

        for key in (
            "neuro-lue-findings", "neuro-rue-findings",
            "neuro-lle-findings", "neuro-rle-findings",
        ):
            field = fields_by_key.get(key)
            selected = (cleaned.get(f"value_{field.pk}") or []) if field else []
            if "WNL" in selected and len(selected) > 1:
                self.add_error(
                    f"value_{field.pk}",
                    "WNL cannot be combined with an abnormal finding.",
                )

        if self.deviation_alerts and not cleaned.get("acknowledge_deviation"):
            self.add_error(
                "acknowledge_deviation",
                "Review and acknowledge the deviations before signing this entry.",
            )
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
        for field in self.definition.fields.filter(is_active=True):
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
