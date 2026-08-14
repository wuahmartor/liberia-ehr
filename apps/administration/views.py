"""
============================================================
ADMINISTRATION VIEWS

File:
apps/administration/views.py

Purpose:
- Render full Administration pages.
- Return workspace-only partials for HTMX requests.
- Maintain Administration sidebar active state.
- Provide appointment scheduling workflows.
============================================================
"""

from __future__ import annotations

import calendar
from datetime import datetime, time, timedelta

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import (
    LoginRequiredMixin,
    UserPassesTestMixin,
)
from django.contrib.auth.models import Group
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.http import (
    Http404,
    HttpResponse,
)
from django.shortcuts import (
    get_object_or_404,
    redirect,
    render,
)
from django.utils import timezone
from django.views import View
from django.views.generic import TemplateView

from apps.accounts.models import UserProfile
from apps.facilities.models import (
    Bed,
    ClinicalUnit,
    Department,
    Facility,
    Room,
)

from .forms import (
    AdministrationUserForm,
    AppointmentCancelForm,
    AppointmentForm,
    ClinicalDictionaryEntryForm,
    IntegrationConfigurationForm,
    RoleGroupForm,
    SystemSettingForm,
    TemporaryPasswordForm,
)
from .models import (
    Appointment,
    ClinicalDictionaryEntry,
    IntegrationConfiguration,
    SystemSetting,
)

User = get_user_model()

APPOINTMENT_PAGE_SIZE = 25


# ============================================================
# SHARED HTMX HELPER
# ============================================================


def is_htmx(request):
    return request.headers.get("HX-Request") == "true"


# ============================================================
# ADMINISTRATION ACCESS
# ============================================================


class AdministrationAccessMixin(
    LoginRequiredMixin,
    UserPassesTestMixin,
):
    """
    Restrict Administration pages to staff and superusers.
    """

    raise_exception = True

    def test_func(self):
        user = self.request.user

        return bool(user.is_authenticated and (user.is_staff or user.is_superuser))


# ============================================================
# ADMINISTRATION NAVIGATION
# ============================================================


class AdministrationNavigationMixin:
    """
    Provide consistent Administration navigation context and
    select the full-page or HTMX content template.
    """

    active_admin_module = ""
    page_title = "Administration"
    page_description = ""

    full_template_name = ""
    partial_template_name = ""

    def is_htmx_request(self):
        return is_htmx(self.request)

    def get_template_names(self):
        if self.is_htmx_request() and self.partial_template_name:
            return [self.partial_template_name]

        return [self.full_template_name]

    def get_context_data(self, **kwargs):
        parent = super()
        context = (
            parent.get_context_data(**kwargs)
            if hasattr(parent, "get_context_data")
            else dict(kwargs)
        )

        context["active_primary_nav"] = "administration"
        context["active_admin_module"] = self.active_admin_module
        context["page_title"] = self.page_title
        context["page_description"] = self.page_description

        return context


# ============================================================
# BASE ADMINISTRATION VIEW
# ============================================================


class AdministrationTemplateView(
    AdministrationAccessMixin,
    AdministrationNavigationMixin,
    TemplateView,
):
    """
    Shared base view for Administration modules.
    """


# ============================================================
# DASHBOARD
# ============================================================


class AdministrationDashboardView(
    AdministrationTemplateView,
):
    active_admin_module = "dashboard"

    page_title = "Administration Dashboard"
    page_description = (
        "Review administrative activity, system status, "
        "organizational configuration, and access controls."
    )

    full_template_name = "administration/dashboard.html"
    partial_template_name = "administration/partials/dashboard_content.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "active_user_count": User.objects.filter(is_active=True).count(),
                "facility_count": Facility.objects.filter(is_active=True).count(),
                "department_count": Department.objects.filter(is_active=True).count(),
                "appointment_count": Appointment.objects.filter(is_active=True).count(),
            }
        )
        return context


# ============================================================
# SCHEDULING QUERYSET
# ============================================================


def appointment_queryset():
    return Appointment.objects.select_related(
        "patient",
        "facility",
        "department",
        "clinical_unit",
        "room",
        "provider",
        "created_by",
        "updated_by",
    )


# ============================================================
# SCHEDULING FILTER HELPERS
# ============================================================


def parse_date(value, fallback):
    try:
        return datetime.strptime(
            value,
            "%Y-%m-%d",
        ).date()
    except (TypeError, ValueError):
        return fallback


def scheduling_filter_context(request):
    today = timezone.localdate()

    default_start = today
    default_end = today + timedelta(days=30)

    start_date = parse_date(
        request.GET.get("start_date"),
        default_start,
    )

    end_date = parse_date(
        request.GET.get("end_date"),
        default_end,
    )

    if end_date < start_date:
        end_date = start_date

    query = request.GET.get("q", "").strip()
    status = request.GET.get("status", "").strip()
    priority = request.GET.get("priority", "").strip()
    facility_id = request.GET.get(
        "facility",
        "",
    ).strip()
    provider_id = request.GET.get(
        "provider",
        "",
    ).strip()

    start_datetime = timezone.make_aware(
        datetime.combine(
            start_date,
            time.min,
        ),
        timezone.get_current_timezone(),
    )

    end_datetime = timezone.make_aware(
        datetime.combine(
            end_date + timedelta(days=1),
            time.min,
        ),
        timezone.get_current_timezone(),
    )

    return {
        "query": query,
        "selected_status": status,
        "selected_priority": priority,
        "selected_facility": facility_id,
        "selected_provider": provider_id,
        "start_date": start_date,
        "end_date": end_date,
        "start_datetime": start_datetime,
        "end_datetime": end_datetime,
    }


# ============================================================
# SCHEDULING LIST
# ============================================================


class SchedulingListView(
    AdministrationTemplateView,
):
    active_admin_module = "scheduling"

    page_title = "Scheduling"
    page_description = (
        "Manage appointments, provider availability, "
        "patient visits, and scheduling workflows."
    )

    full_template_name = "administration/scheduling/index.html"

    partial_template_name = "administration/scheduling/partials/list_content.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        month_value = self.request.GET.get(
            "month", timezone.localdate().strftime("%Y-%m")
        )
        try:
            month_start = datetime.strptime(month_value, "%Y-%m").date().replace(day=1)
        except ValueError:
            month_start = timezone.localdate().replace(day=1)
        next_month = (month_start.replace(day=28) + timedelta(days=4)).replace(day=1)
        month_end = next_month - timedelta(days=1)
        query_data = self.request.GET.copy()
        if "start_date" not in query_data:
            query_data["start_date"] = month_start.isoformat()
        if "end_date" not in query_data:
            query_data["end_date"] = month_end.isoformat()
        original_get = self.request.GET
        self.request.GET = query_data
        filters = scheduling_filter_context(self.request)
        self.request.GET = original_get

        appointments = appointment_queryset().filter(
            start_datetime__gte=(filters["start_datetime"]),
            start_datetime__lt=(filters["end_datetime"]),
        )

        if filters["query"]:
            appointments = appointments.search(
                filters["query"],
            )

        if filters["selected_status"]:
            appointments = appointments.filter(
                status=filters["selected_status"],
            )

        if filters["selected_priority"]:
            appointments = appointments.filter(
                priority=filters["selected_priority"],
            )

        if filters["selected_facility"]:
            appointments = appointments.filter(
                facility_id=filters["selected_facility"],
            )

        if filters["selected_provider"]:
            appointments = appointments.filter(
                provider_id=filters["selected_provider"],
            )

        appointments = appointments.order_by(
            "start_datetime",
            "appointment_number",
        )
        calendar_appointments = list(appointments)
        by_day = {}
        for appointment in calendar_appointments:
            day_key = timezone.localtime(appointment.start_datetime).date()
            by_day.setdefault(day_key, []).append(appointment)
        calendar_weeks = []
        for week in calendar.Calendar(firstweekday=6).monthdatescalendar(
            month_start.year, month_start.month
        ):
            calendar_weeks.append(
                [
                    {
                        "date": day,
                        "in_month": day.month == month_start.month,
                        "is_today": day == timezone.localdate(),
                        "appointments": by_day.get(day, []),
                    }
                    for day in week
                ]
            )

        paginator = Paginator(
            appointments,
            APPOINTMENT_PAGE_SIZE,
        )

        page_obj = paginator.get_page(
            self.request.GET.get("page"),
        )

        today = timezone.localdate()

        today_start = timezone.make_aware(
            datetime.combine(
                today,
                time.min,
            ),
            timezone.get_current_timezone(),
        )

        tomorrow_start = today_start + timedelta(
            days=1,
        )

        context.update(
            {
                "page_obj": page_obj,
                "appointments": (page_obj.object_list),
                "filters": filters,
                "facilities": (
                    Facility.objects.filter(is_active=True).order_by("name")
                ),
                "providers": (
                    User.objects.filter(
                        is_active=True,
                        is_staff=True,
                    ).order_by(
                        "last_name",
                        "first_name",
                        "username",
                    )
                ),
                "appointment_statuses": (Appointment.Status.choices),
                "appointment_priorities": (Appointment.Priority.choices),
                "today_count": (
                    Appointment.objects.filter(
                        is_active=True,
                        start_datetime__gte=(today_start),
                        start_datetime__lt=(tomorrow_start),
                    )
                    .exclude(
                        status__in=[
                            Appointment.Status.CANCELLED,
                            Appointment.Status.ENTERED_IN_ERROR,
                        ],
                    )
                    .count()
                ),
                "upcoming_count": (
                    Appointment.objects.upcoming()
                    .exclude(
                        status__in=[
                            Appointment.Status.CANCELLED,
                            Appointment.Status.COMPLETED,
                            Appointment.Status.ENTERED_IN_ERROR,
                        ],
                    )
                    .count()
                ),
                "confirmed_count": (
                    Appointment.objects.filter(
                        status=(Appointment.Status.CONFIRMED),
                        start_datetime__gte=(filters["start_datetime"]),
                        start_datetime__lt=(filters["end_datetime"]),
                    ).count()
                ),
                "cancelled_count": (
                    Appointment.objects.filter(
                        status=(Appointment.Status.CANCELLED),
                        start_datetime__gte=(filters["start_datetime"]),
                        start_datetime__lt=(filters["end_datetime"]),
                    ).count()
                ),
                "calendar_weeks": calendar_weeks,
                "calendar_weekdays": ("Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"),
                "calendar_month": month_start,
                "previous_month": (month_start - timedelta(days=1)).strftime("%Y-%m"),
                "next_month": next_month.strftime("%Y-%m"),
            }
        )

        return context


# ============================================================
# SCHEDULING DETAIL
# ============================================================


class SchedulingDetailView(
    AdministrationTemplateView,
):
    active_admin_module = "scheduling"

    page_title = "Appointment Details"
    page_description = "Review the complete appointment and scheduling record."

    full_template_name = "administration/scheduling/detail.html"

    partial_template_name = "administration/scheduling/partials/detail_content.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["appointment"] = get_object_or_404(
            appointment_queryset(),
            pk=self.kwargs["appointment_id"],
        )

        return context


# ============================================================
# SHARED SCHEDULING FORM VIEW
# ============================================================


class SchedulingFormMixin(
    AdministrationAccessMixin,
):
    form_template = "administration/scheduling/form.html"

    form_partial_template = "administration/scheduling/partials/form_content.html"

    appointment = None
    form_mode = "create"

    def get_appointment(self):
        return self.appointment

    def get_form(self):
        return AppointmentForm(
            self.request.POST or None,
            instance=self.get_appointment(),
            current_user=self.request.user,
            initial=self.get_initial(),
        )

    def get_initial(self):
        initial = {}

        patient_id = self.request.GET.get(
            "patient",
        )

        facility_id = self.request.GET.get(
            "facility",
        )

        provider_id = self.request.GET.get(
            "provider",
        )

        if patient_id:
            initial["patient"] = patient_id

        if facility_id:
            initial["facility"] = facility_id

        if provider_id:
            initial["provider"] = provider_id

        return initial

    def get_context(self, form):
        is_update = self.form_mode == "update"

        return {
            "form": form,
            "appointment": self.get_appointment(),
            "form_mode": self.form_mode,
            "page_title": (
                "Update Appointment" if is_update else "Schedule Appointment"
            ),
            "page_description": (
                "Modify the appointment schedule and administrative details."
                if is_update
                else "Create a new patient appointment."
            ),
            "submit_label": ("Save Changes" if is_update else "Schedule Appointment"),
            "active_primary_nav": "administration",
            "active_admin_module": "scheduling",
        }

    def render_form(self, form, status=200):
        template_name = (
            self.form_partial_template if is_htmx(self.request) else self.form_template
        )

        response = render(
            self.request,
            template_name,
            self.get_context(form),
            status=status,
        )

        response["Vary"] = "HX-Request"

        return response


# ============================================================
# CREATE APPOINTMENT
# ============================================================


class SchedulingCreateView(
    SchedulingFormMixin,
    View,
):
    form_mode = "create"

    def get(self, request):
        return self.render_form(
            self.get_form(),
        )

    @transaction.atomic
    def post(self, request):
        form = self.get_form()

        if not form.is_valid():
            return self.render_form(
                form,
                status=200,
            )

        appointment = form.save(
            commit=False,
        )

        appointment.created_by = request.user
        appointment.updated_by = request.user

        appointment.full_clean()
        appointment.save()

        if is_htmx(request):
            response = HttpResponse(status=204)
            response["HX-Trigger"] = "appointmentCreated"
            response["HX-Redirect"] = appointment.get_absolute_url()
            return response

        return redirect(
            appointment.get_absolute_url(),
        )


# ============================================================
# UPDATE APPOINTMENT
# ============================================================


class SchedulingUpdateView(
    SchedulingFormMixin,
    View,
):
    form_mode = "update"

    def dispatch(
        self,
        request,
        *args,
        **kwargs,
    ):
        self.appointment = get_object_or_404(
            Appointment,
            pk=kwargs["appointment_id"],
        )

        return super().dispatch(
            request,
            *args,
            **kwargs,
        )

    def get(self, request, appointment_id):
        return self.render_form(
            self.get_form(),
        )

    @transaction.atomic
    def post(
        self,
        request,
        appointment_id,
    ):
        form = self.get_form()

        if not form.is_valid():
            return self.render_form(
                form,
                status=200,
            )

        appointment = form.save(
            commit=False,
        )

        appointment.updated_by = request.user

        appointment.full_clean()
        appointment.save()

        if is_htmx(request):
            response = HttpResponse(status=204)
            response["HX-Trigger"] = "appointmentUpdated"
            response["HX-Redirect"] = appointment.get_absolute_url()
            return response

        return redirect(
            appointment.get_absolute_url(),
        )


# ============================================================
# CANCEL APPOINTMENT
# ============================================================


class SchedulingCancelView(
    AdministrationAccessMixin,
    View,
):
    template_name = "administration/scheduling/confirm_cancel.html"

    partial_template_name = "administration/scheduling/partials/cancel_content.html"

    def get_appointment(self, appointment_id):
        return get_object_or_404(
            appointment_queryset(),
            pk=appointment_id,
        )

    def get(
        self,
        request,
        appointment_id,
    ):
        appointment = self.get_appointment(
            appointment_id,
        )

        form = AppointmentCancelForm()

        template_name = (
            self.partial_template_name if is_htmx(request) else self.template_name
        )

        return render(
            request,
            template_name,
            {
                "appointment": appointment,
                "form": form,
                "active_primary_nav": ("administration"),
                "active_admin_module": ("scheduling"),
                "page_title": ("Cancel Appointment"),
            },
        )

    @transaction.atomic
    def post(
        self,
        request,
        appointment_id,
    ):
        appointment = self.get_appointment(
            appointment_id,
        )

        form = AppointmentCancelForm(
            request.POST,
        )

        if not form.is_valid():
            template_name = (
                self.partial_template_name if is_htmx(request) else self.template_name
            )

            return render(
                request,
                template_name,
                {
                    "appointment": appointment,
                    "form": form,
                    "active_primary_nav": ("administration"),
                    "active_admin_module": ("scheduling"),
                    "page_title": ("Cancel Appointment"),
                },
                status=422,
            )

        if not appointment.can_be_cancelled:
            raise Http404("This appointment cannot be cancelled.")

        appointment.status = Appointment.Status.CANCELLED
        appointment.cancellation_reason = form.cleaned_data["cancellation_reason"]
        appointment.cancelled_at = timezone.now()
        appointment.updated_by = request.user
        appointment.save(
            update_fields=[
                "status",
                "cancellation_reason",
                "cancelled_at",
                "updated_by",
                "updated_at",
            ],
        )

        if is_htmx(request):
            response = HttpResponse(status=204)
            response["HX-Trigger"] = "appointmentCancelled"
            response["HX-Redirect"] = appointment.get_absolute_url()
            return response

        return redirect(
            appointment.get_absolute_url(),
        )


# ============================================================
# RESTORE CANCELLED APPOINTMENT
# ============================================================


class SchedulingRestoreView(
    AdministrationAccessMixin,
    View,
):
    @transaction.atomic
    def post(
        self,
        request,
        appointment_id,
    ):
        appointment = get_object_or_404(
            Appointment,
            pk=appointment_id,
        )

        if not appointment.can_be_restored:
            raise Http404("Only cancelled appointments can be restored.")

        appointment.status = Appointment.Status.SCHEDULED
        appointment.cancellation_reason = ""
        appointment.cancelled_at = None
        appointment.updated_by = request.user

        appointment.full_clean()

        appointment.save(
            update_fields=[
                "status",
                "cancellation_reason",
                "cancelled_at",
                "updated_by",
                "updated_at",
            ],
        )

        if is_htmx(request):
            response = HttpResponse(status=204)
            response["HX-Trigger"] = "appointmentRestored"
            response["HX-Redirect"] = appointment.get_absolute_url()
            return response

        return redirect(
            appointment.get_absolute_url(),
        )


# ============================================================
# DEPENDENT ORGANIZATION OPTIONS
# ============================================================


class SchedulingDepartmentOptionsView(
    AdministrationAccessMixin,
    View,
):
    def get(self, request):
        facility_id = request.GET.get(
            "facility",
        )

        departments = Department.objects.none()

        if facility_id:
            departments = Department.objects.filter(
                facility_id=facility_id,
                is_active=True,
            ).order_by("name")

        return render(
            request,
            ("administration/scheduling/partials/department_options.html"),
            {
                "departments": departments,
            },
        )


class SchedulingUnitOptionsView(
    AdministrationAccessMixin,
    View,
):
    def get(self, request):
        facility_id = request.GET.get(
            "facility",
        )

        department_id = request.GET.get(
            "department",
        )

        units = ClinicalUnit.objects.none()

        if department_id:
            units = ClinicalUnit.objects.filter(
                department_id=department_id,
                is_active=True,
            ).order_by("name")
        elif facility_id:
            units = ClinicalUnit.objects.filter(
                facility_id=facility_id,
                is_active=True,
            ).order_by("name")

        return render(
            request,
            ("administration/scheduling/partials/unit_options.html"),
            {
                "clinical_units": units,
            },
        )


class SchedulingRoomOptionsView(
    AdministrationAccessMixin,
    View,
):
    def get(self, request):
        facility_id = request.GET.get(
            "facility",
        )

        clinical_unit_id = request.GET.get(
            "clinical_unit",
        )

        rooms = Room.objects.none()

        if clinical_unit_id:
            rooms = Room.objects.filter(
                clinical_unit_id=(clinical_unit_id),
                is_active=True,
            ).order_by("name")
        elif facility_id:
            rooms = Room.objects.filter(
                facility_id=facility_id,
                is_active=True,
            ).order_by("name")

        return render(
            request,
            ("administration/scheduling/partials/room_options.html"),
            {
                "rooms": rooms,
            },
        )


# ============================================================
# USER ACCOUNTS
# ============================================================


class UserAccountListView(
    AdministrationTemplateView,
):
    active_admin_module = "users"

    page_title = "User Accounts"
    page_description = "Manage user identities, access status, and staff accounts."

    full_template_name = "administration/users.html"
    partial_template_name = "administration/partials/users_content.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        users = User.objects.select_related("profile").prefetch_related("groups")
        query = self.request.GET.get("q", "").strip()
        if query:
            users = users.filter(
                Q(username__icontains=query)
                | Q(first_name__icontains=query)
                | Q(last_name__icontains=query)
                | Q(email__icontains=query)
            )
        context["users"] = users.order_by(
            "last_name",
            "first_name",
            "username",
        )[:100]

        context["user_count"] = User.objects.count()
        context["active_user_count"] = User.objects.filter(
            is_active=True,
        ).count()
        context["staff_user_count"] = User.objects.filter(
            is_staff=True,
        ).count()

        return context


class UserAccountFormView(
    AdministrationAccessMixin, AdministrationNavigationMixin, View
):
    active_admin_module = "users"

    def get_user(self, user_id):
        return (
            get_object_or_404(User.objects.select_related("profile"), pk=user_id)
            if user_id
            else None
        )

    def render_form(self, request, user=None, form=None):
        form = form or AdministrationUserForm(instance=user, editing=bool(user))
        return render(
            request,
            "administration/user_form.html",
            {**self.get_context_data(), "form": form, "managed_user": user},
        )

    def get(self, request, user_id=None):
        return self.render_form(request, self.get_user(user_id))

    def post(self, request, user_id=None):
        user = self.get_user(user_id)
        form = AdministrationUserForm(request.POST, instance=user, editing=bool(user))
        if form.is_valid():
            saved = form.save()
            messages.success(request, f"User {saved.username} saved.")
            return redirect("administration:users")
        return self.render_form(request, user, form)


class UserAccountToggleView(AdministrationAccessMixin, View):
    def post(self, request, user_id):
        user = get_object_or_404(User, pk=user_id)
        if user == request.user:
            messages.error(request, "You cannot deactivate your own account.")
        else:
            user.is_active = not user.is_active
            user.save(update_fields=["is_active"])
            messages.success(
                request,
                f"{user.username} is now {'active' if user.is_active else 'inactive'}.",
            )
        return redirect("administration:users")


class UserPasswordResetView(
    AdministrationAccessMixin, AdministrationNavigationMixin, View
):
    active_admin_module = "users"

    def get(self, request, user_id):
        return render(
            request,
            "administration/user_password.html",
            {
                **self.get_context_data(),
                "managed_user": get_object_or_404(User, pk=user_id),
                "form": TemporaryPasswordForm(),
            },
        )

    def post(self, request, user_id):
        user = get_object_or_404(User, pk=user_id)
        form = TemporaryPasswordForm(request.POST)
        if form.is_valid():
            user.set_password(form.cleaned_data["password1"])
            user.save(update_fields=["password"])
            profile, _ = UserProfile.objects.get_or_create(user=user)
            profile.must_change_password = form.cleaned_data["require_change"]
            profile.save(update_fields=["must_change_password", "updated_at"])
            messages.success(request, "Temporary password set.")
            return redirect("administration:users")
        return render(
            request,
            "administration/user_password.html",
            {**self.get_context_data(), "managed_user": user, "form": form},
        )


# ============================================================
# ROLES AND PERMISSIONS
# ============================================================


class RolePermissionListView(
    AdministrationTemplateView,
):
    active_admin_module = "roles"

    page_title = "Groups and Permissions"
    page_description = "Create access groups and assign the permissions their members receive."

    full_template_name = "administration/roles.html"
    partial_template_name = "administration/partials/roles_content.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["role_groups"] = Group.objects.prefetch_related(
            "permissions", "user_set"
        ).order_by("name")

        context["role_count"] = Group.objects.count()

        return context


class RolePermissionFormView(
    AdministrationAccessMixin, AdministrationNavigationMixin, View
):
    active_admin_module = "roles"

    def form_context(self, group, form):
        return {
            **self.get_context_data(),
            "page_title": "Edit Group" if group else "Add Group",
            "page_description": (
                "Choose the permissions inherited by every member of this group."
            ),
            "form": form,
            "role_group": group,
        }

    def get(self, request, group_id=None):
        group = get_object_or_404(Group, pk=group_id) if group_id else None
        return render(
            request,
            "administration/role_form.html",
            self.form_context(group, RoleGroupForm(instance=group)),
        )

    def post(self, request, group_id=None):
        group = get_object_or_404(Group, pk=group_id) if group_id else None
        form = RoleGroupForm(request.POST, instance=group)
        if form.is_valid():
            saved = form.save()
            messages.success(
                request,
                (
                    f"Group {saved.name} saved with "
                    f"{saved.permissions.count()} permissions."
                ),
            )
            return redirect("administration:roles")
        return render(
            request,
            "administration/role_form.html",
            self.form_context(group, form),
        )


# ============================================================
# FACILITIES
# ============================================================


class FacilityAdministrationView(
    AdministrationTemplateView,
):
    active_admin_module = "facilities"

    page_title = "Facilities"
    page_description = "Manage healthcare facilities and organizational locations."

    full_template_name = "administration/facilities.html"
    partial_template_name = "administration/partials/facilities_content.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["facilities"] = Facility.objects.order_by("name")[:100]

        context["facility_count"] = Facility.objects.count()

        return context


# ============================================================
# DEPARTMENTS AND UNITS
# ============================================================


class DepartmentAdministrationView(
    AdministrationTemplateView,
):
    active_admin_module = "departments"

    page_title = "Departments and Units"
    page_description = "Manage departments and clinical units within facilities."

    full_template_name = "administration/departments.html"
    partial_template_name = "administration/partials/department_contents.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["departments"] = Department.objects.select_related("facility").order_by(
            "facility__name",
            "name",
        )[:100]

        context["clinical_units"] = ClinicalUnit.objects.select_related(
            "department"
        ).order_by(
            "department__name",
            "name",
        )[:100]

        context["department_count"] = Department.objects.count()

        context["clinical_unit_count"] = ClinicalUnit.objects.count()

        return context


# ============================================================
# ROOMS AND BEDS
# ============================================================


class RoomBedAdministrationView(
    AdministrationTemplateView,
):
    active_admin_module = "rooms"

    page_title = "Rooms and Beds"
    page_description = "Manage room records, bed inventory, and availability."

    full_template_name = "administration/rooms.html"
    partial_template_name = "administration/partials/rooms_content.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["rooms"] = Room.objects.all()[:100]

        context["beds"] = Bed.objects.select_related("room")[:100]

        context["room_count"] = Room.objects.count()
        context["bed_count"] = Bed.objects.count()

        return context


# ============================================================
# SYSTEM SETTINGS
# ============================================================


class SystemSettingsView(
    AdministrationTemplateView,
):
    active_admin_module = "system_settings"

    page_title = "System Settings"
    page_description = "Review and manage core EHR system configuration."

    full_template_name = "administration/system_settings.html"

    partial_template_name = "administration/partials/system_settings_content.html"

    def get_context_data(self, **kwargs):
        return super().get_context_data(**kwargs) | {
            "settings_records": SystemSetting.objects.all()
        }


# ============================================================
# CLINICAL DICTIONARIES
# ============================================================


class ClinicalDictionaryView(
    AdministrationTemplateView,
):
    active_admin_module = "clinical_dictionaries"

    page_title = "Clinical Dictionaries"
    page_description = (
        "Manage clinical terminology, reference values, and controlled configuration."
    )

    full_template_name = "administration/clinical_dictionaries.html"

    partial_template_name = "administration/partials/clinical_dictionaries_content.html"

    def get_context_data(self, **kwargs):
        return super().get_context_data(**kwargs) | {
            "dictionary_entries": ClinicalDictionaryEntry.objects.all()[:200]
        }


# ============================================================
# EXTERNAL INTEGRATIONS
# ============================================================


class IntegrationListView(
    AdministrationTemplateView,
):
    active_admin_module = "integrations"

    page_title = "External Integrations"
    page_description = "Manage external APIs, interfaces, and data connections."

    full_template_name = "administration/integrations.html"

    partial_template_name = "administration/partials/integrations_content.html"

    def get_context_data(self, **kwargs):
        return super().get_context_data(**kwargs) | {
            "integrations": IntegrationConfiguration.objects.all()
        }


class ConfigurationFormView(
    AdministrationAccessMixin, AdministrationNavigationMixin, View
):
    options = {
        "setting": (SystemSetting, SystemSettingForm, "system_settings"),
        "dictionary": (
            ClinicalDictionaryEntry,
            ClinicalDictionaryEntryForm,
            "clinical_dictionaries",
        ),
        "integration": (
            IntegrationConfiguration,
            IntegrationConfigurationForm,
            "integrations",
        ),
    }

    def dispatch(self, request, kind, object_id=None, *args, **kwargs):
        if kind not in self.options:
            raise Http404
        self.kind, self.object_id = kind, object_id
        self.model, self.form_class, self.active_admin_module = self.options[kind]
        return super().dispatch(request, *args, **kwargs)

    def item(self):
        return (
            get_object_or_404(self.model, pk=self.object_id) if self.object_id else None
        )

    def get(self, request, **kwargs):
        return render(
            request,
            "administration/configuration_form.html",
            {
                **self.get_context_data(),
                "form": self.form_class(instance=self.item()),
                "kind": self.kind,
            },
        )

    def post(self, request, **kwargs):
        form = self.form_class(request.POST, instance=self.item())
        if form.is_valid():
            item = form.save(commit=False)
            item.updated_by = request.user
            item.save()
            messages.success(request, "Configuration saved.")
            return redirect(f"administration:{self.active_admin_module}")
        return render(
            request,
            "administration/configuration_form.html",
            {**self.get_context_data(), "form": form, "kind": self.kind},
        )


# ============================================================
# AUDIT LOGS
# ============================================================


class AuditLogListView(
    AdministrationTemplateView,
):
    active_admin_module = "audit_logs"

    page_title = "Audit Logs"
    page_description = "Review administrative and clinical system activity."

    full_template_name = "administration/audit_logs.html"

    partial_template_name = "administration/partials/audit_logs_content.html"


# ============================================================
# SYSTEM HEALTH
# ============================================================


class SystemHealthView(
    AdministrationTemplateView,
):
    active_admin_module = "system_health"

    page_title = "System Health"
    page_description = "Review application, database, and service availability."

    full_template_name = "administration/system_health.html"

    partial_template_name = "administration/partials/system_health_content.html"

    def get_context_data(self, **kwargs):
        from django.db import connection
        from django.utils import timezone

        context = super().get_context_data(**kwargs)
        database_ok = True
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
        except Exception:
            database_ok = False
        context.update(
            {
                "database_ok": database_ok,
                "checked_at": timezone.now(),
                "database_vendor": connection.vendor,
            }
        )
        return context
