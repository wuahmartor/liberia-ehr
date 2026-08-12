from django.contrib import admin

from .models import ClinicalAlert, ClinicalRule, RiskAssessment

admin.site.register(ClinicalRule)
admin.site.register(ClinicalAlert)
admin.site.register(RiskAssessment)
