from django.contrib import admin

from .models import (
    IntakeOutputRecord,
    NursingAssessment,
    NursingHandoff,
    NursingTask,
)

admin.site.register(NursingAssessment)
admin.site.register(NursingTask)
admin.site.register(IntakeOutputRecord)
admin.site.register(NursingHandoff)
