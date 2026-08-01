

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    UpdateView,
)

from .forms import EncounterForm
from .models import Encounter


class EncounterNavigationMixin:
    """
    Provide navigation context required by app_shell.html.
    """

    active_primary_nav = "clinical"
    active_clinical_module = "encounters"
    active_encounter_module = ""

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context.update(
            {
                "active_primary_nav": self.active_primary_nav,
                "active_clinical_module": self.active_clinical_module,
                "active_encounter_module": self.active_encounter_module,
            }
        )

        return context


class HTMXTemplateMixin:
    """
    Return a workspace partial for HTMX requests.
    """

    htmx_template_name = None

    def get_template_names(self):
        is_htmx = self.request.headers.get("HX-Request") == "true"

        if is_htmx and self.htmx_template_name:
            return [self.htmx_template_name]

        return [self.template_name]


class EncounterListView(
    LoginRequiredMixin,
    EncounterNavigationMixin,
    HTMXTemplateMixin,
    ListView,
):
    """
    Display and filter encounter records.
    """

    model = Encounter
    template_name = "encounters/encounter_list.html"
    htmx_template_name = "encounters/partials/list_content.html"
    context_object_name = "encounters"
    paginate_by = 25
    active_encounter_module = "list"

    def get_queryset(self):
        queryset = Encounter.objects.select_related(
            "patient",
            "attending_provider",
            "created_by",
        )

        query = self.request.GET.get("q", "").strip()
        status = self.request.GET.get("status", "").strip()
        encounter_type = self.request.GET.get(
            "encounter_type",
            "",
        ).strip()
        priority = self.request.GET.get("priority", "").strip()

        if query:
            queryset = queryset.filter(
                Q(encounter_number__icontains=query)
                | Q(reason_for_visit__icontains=query)
                | Q(patient__first_name__icontains=query)
                | Q(patient__middle_name__icontains=query)
                | Q(patient__last_name__icontains=query)
            )

        if status:
            queryset = queryset.filter(status=status)

        if encounter_type:
            queryset = queryset.filter(
                encounter_type=encounter_type,
            )

        if priority:
            queryset = queryset.filter(priority=priority)

        return queryset.order_by(
            "-start_datetime",
            "-created_at",
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        all_encounters = Encounter.objects.all()

        context.update(
            {
                "page_title": "Encounters",
                "search_query": self.request.GET.get("q", ""),
                "selected_status": self.request.GET.get(
                    "status",
                    "",
                ),
                "selected_encounter_type": self.request.GET.get(
                    "encounter_type",
                    "",
                ),
                "selected_priority": self.request.GET.get(
                    "priority",
                    "",
                ),
                "encounter_status_choices": (
                    Encounter.EncounterStatus.choices
                ),
                "encounter_type_choices": (
                    Encounter.EncounterType.choices
                ),
                "priority_choices": Encounter.Priority.choices,
                "total_encounters": all_encounters.count(),
                "open_encounters": all_encounters.filter(
                    status__in=[
                        Encounter.EncounterStatus.ARRIVED,
                        Encounter.EncounterStatus.TRIAGED,
                        Encounter.EncounterStatus.IN_PROGRESS,
                        Encounter.EncounterStatus.ON_HOLD,
                    ]
                ).count(),
                "completed_encounters": all_encounters.filter(
                    status=Encounter.EncounterStatus.COMPLETED,
                ).count(),
                "today_encounters": all_encounters.filter(
                    start_datetime__date=timezone.localdate(),
                ).count(),
            }
        )

        return context


class EncounterDetailView(
    LoginRequiredMixin,
    EncounterNavigationMixin,
    HTMXTemplateMixin,
    DetailView,
):
    """
    Display one encounter.
    """

    model = Encounter
    template_name = "encounters/encounter_detail.html"
    htmx_template_name = "encounters/partials/detail_content.html"
    context_object_name = "encounter"
    active_encounter_module = "detail"

    def get_queryset(self):
        return Encounter.objects.select_related(
            "patient",
            "attending_provider",
            "created_by",
        ).prefetch_related(
            "diagnoses",
            "diagnoses__concept",
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["selected_patient"] = self.object.patient
        return context


class EncounterCreateView(
    LoginRequiredMixin,
    EncounterNavigationMixin,
    CreateView,
):
    """
    Create an encounter.
    """

    model = Encounter
    form_class = EncounterForm
    template_name = "encounters/form.html"
    active_encounter_module = "create"

    def get_initial(self):
        initial = super().get_initial()

        patient_id = self.request.GET.get("patient")

        if patient_id:
            initial["patient"] = patient_id

        return initial

    def form_valid(self, form):
        form.instance.created_by = self.request.user

        response = super().form_valid(form)

        messages.success(
            self.request,
            f"Encounter {self.object.encounter_number} was created.",
        )

        return response

    def get_success_url(self):
        return reverse(
            "encounters:detail",
            kwargs={"pk": self.object.pk},
        )

    def get_form_kwargs(self):
        """
        Pass the current user to the encounter form.
        """

        kwargs = super().get_form_kwargs()
        kwargs["current_user"] = self.request.user

        return kwargs


class EncounterUpdateView(
    LoginRequiredMixin,
    EncounterNavigationMixin,
    UpdateView,
):
    """
    Update an encounter.
    """

    model = Encounter
    form_class = EncounterForm
    template_name = "encounters/form.html"
    context_object_name = "encounter"
    active_encounter_module = "update"

    def form_valid(self, form):
        response = super().form_valid(form)

        messages.success(
            self.request,
            f"Encounter {self.object.encounter_number} was updated.",
        )

        return response

    def get_success_url(self):
        return reverse(
            "encounters:detail",
            kwargs={"pk": self.object.pk},
        )


    def get_form_kwargs(self):
        """
        Pass the current user to the encounter form.
        """

        kwargs = super().get_form_kwargs()
        kwargs["current_user"] = self.request.user

        return kwargs


class EncounterCompleteView(LoginRequiredMixin, View):
    """
    Complete an encounter.
    """

    def post(self, request, pk):
        encounter = get_object_or_404(
            Encounter,
            pk=pk,
        )

        if encounter.status in {
            Encounter.EncounterStatus.CANCELLED,
            Encounter.EncounterStatus.ENTERED_IN_ERROR,
        }:
            messages.error(
                request,
                "A cancelled encounter cannot be completed.",
            )

            return redirect(
                "encounters:detail",
                pk=encounter.pk,
            )

        encounter.status = Encounter.EncounterStatus.COMPLETED

        if not encounter.end_datetime:
            encounter.end_datetime = timezone.now()

        encounter.save(
            update_fields=[
                "status",
                "end_datetime",
                "updated_at",
            ]
        )

        messages.success(
            request,
            f"Encounter {encounter.encounter_number} was completed.",
        )

        return redirect(
            "encounters:detail",
            pk=encounter.pk,
        )


class EncounterCancelView(LoginRequiredMixin, View):
    """
    Cancel an encounter.
    """

    def post(self, request, pk):
        encounter = get_object_or_404(
            Encounter,
            pk=pk,
        )

        if encounter.status == Encounter.EncounterStatus.COMPLETED:
            messages.error(
                request,
                "A completed encounter cannot be cancelled.",
            )

            return redirect(
                "encounters:detail",
                pk=encounter.pk,
            )

        encounter.status = Encounter.EncounterStatus.CANCELLED
        encounter.is_active = False

        encounter.save(
            update_fields=[
                "status",
                "is_active",
                "updated_at",
            ]
        )

        messages.success(
            request,
            f"Encounter {encounter.encounter_number} was cancelled.",
        )

        return redirect(
            "encounters:detail",
            pk=encounter.pk,
        )


class EncounterDeleteView(
    LoginRequiredMixin,
    EncounterNavigationMixin,
    DeleteView,
):
    """
    Permanently delete an encounter.
    """

    model = Encounter
    template_name = "encounters/confirm_delete.html"
    context_object_name = "encounter"
    success_url = reverse_lazy("encounters:list")
    active_encounter_module = "delete"

    def form_valid(self, form):
        encounter_number = self.object.encounter_number

        response = super().form_valid(form)

        messages.success(
            self.request,
            f"Encounter {encounter_number} was deleted.",
        )

        return response