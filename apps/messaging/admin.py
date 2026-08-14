from django.contrib import admin

from .models import Conversation, Message, PatientCareTeamMember


class SuperuserOnlyMessagingAdmin:
    """Keep message contents out of ordinary staff administration."""

    def has_module_permission(self, request):
        return request.user.is_superuser

    def has_view_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_add_permission(self, request):
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


@admin.register(Conversation)
class ConversationAdmin(SuperuserOnlyMessagingAdmin, admin.ModelAdmin):
    list_display = (
        "subject",
        "context_type",
        "subject_category",
        "audience",
        "created_by",
        "created_at",
    )
    list_filter = ("context_type", "subject_category", "audience", "created_at")
    readonly_fields = ("direct_key", "created_at", "updated_at")
    filter_horizontal = ("participants", "patients")


@admin.register(Message)
class MessageAdmin(SuperuserOnlyMessagingAdmin, admin.ModelAdmin):
    list_display = ("id", "conversation", "sender", "created_at")
    search_fields = ("body", "sender__first_name", "sender__last_name")
    readonly_fields = ("created_at",)
    filter_horizontal = ("read_by",)


@admin.register(PatientCareTeamMember)
class PatientCareTeamMemberAdmin(SuperuserOnlyMessagingAdmin, admin.ModelAdmin):
    list_display = ("patient", "user", "role_label", "is_active", "created_at")
    list_filter = ("is_active", "role_label")
    search_fields = (
        "patient__first_name",
        "patient__last_name",
        "patient__mrn",
        "user__first_name",
        "user__last_name",
    )
