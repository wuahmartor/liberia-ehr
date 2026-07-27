from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import UserProfile


User = get_user_model()


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    extra = 0

    fieldsets = (
        (
            "EHR Access",
            {
                "fields": (
                    "role",
                    "facility",
                    "employee_id",
                    "job_title",
                    "department",
                ),
            },
        ),
        (
            "Professional Information",
            {
                "fields": (
                    "professional_license_number",
                    "phone_number",
                ),
            },
        ),
        (
            "Account Controls",
            {
                "fields": (
                    "is_clinical_staff",
                    "is_active_staff",
                    "must_change_password",
                    "last_activity",
                ),
            },
        ),
    )

    readonly_fields = ("last_activity",)


class EHRUserAdmin(BaseUserAdmin):
    inlines = (UserProfileInline,)

    list_display = (
        "username",
        "get_full_name_display",
        "email",
        "get_role",
        "get_facility",
        "is_active",
        "is_staff",
    )

    list_filter = (
        "is_active",
        "is_staff",
        "is_superuser",
        "profile__role",
        "profile__facility",
        "profile__is_active_staff",
    )

    search_fields = (
        "username",
        "first_name",
        "last_name",
        "email",
        "profile__employee_id",
        "profile__professional_license_number",
    )

    ordering = (
        "last_name",
        "first_name",
               "username",
    )

    @admin.display(description="Full name")
    def get_full_name_display(self, obj):
        return obj.get_full_name().strip() or obj.username

    @admin.display(
        description="EHR role",
        ordering="profile__role",
    )
    def get_role(self, obj):
        profile = getattr(obj, "profile", None)

        if profile:
            return profile.get_role_display()

        return "No profile"

    @admin.display(
        description="Facility",
        ordering="profile__facility",
    )
    def get_facility(self, obj):
        profile = getattr(obj, "profile", None)

        if profile and profile.facility:
            return profile.facility

        return "Not assigned"


admin.site.unregister(User)
admin.site.register(User, EHRUserAdmin)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = (
        "display_name",
        "role",
        "facility",
        "employee_id",
        "department",
        "is_active_staff",
    )

    list_filter = (
        "role",
        "facility",
        "department",
        "is_clinical_staff",
        "is_active_staff",
    )

    search_fields = (
        "user__username",
        "user__first_name",
        "user__last_name",
        "user__email",
        "employee_id",
        "professional_license_number",
    )

    autocomplete_fields = (
        "user",
        "facility",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
        "last_activity",
    )

    fieldsets = (
        (
            "User",
            {
                "fields": (
                    "user",
                    "role",
                    "facility",
                ),
            },
        ),
        (
            "Employment",
            {
                "fields": (
                    "employee_id",
                    "job_title",
                    "department",
                    "professional_license_number",
                    "phone_number",
                ),
            },
        ),
        (
            "Access Controls",
            {
                "fields": (
                    "is_clinical_staff",
                    "is_active_staff",
                    "must_change_password",
                ),
            },
        ),
        (
            "System Information",
            {
                "classes": ("collapse",),
                "fields": (
                    "last_activity",
                    "created_at",
                    "updated_at",
                ),
            },
        ),
    )