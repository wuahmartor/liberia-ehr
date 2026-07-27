from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.views.generic import CreateView, DeleteView, UpdateView

from apps.core.htmx import is_htmx

from .forms import (
    BedForm,
    ClinicalUnitForm,
    DepartmentForm,
    FacilityForm,
    FacilityOperatingHourForm,
    FacilityServiceForm,
    RoomForm,
)
from .models import (
    Bed,
    ClinicalUnit,
    Department,
    Facility,
    FacilityOperatingHour,
    FacilityService,
    Room,
)


FACILITY_PAGE_SIZE = 25


def facility_queryset():
    return (
        Facility.objects.select_related("parent_facility")
        .annotate(
            department_count=Count("departments", distinct=True),
            unit_count=Count("clinical_units", distinct=True),
            bed_count=Count("beds", distinct=True),
        )
        .prefetch_related(
            "departments",
            "clinical_units",
            "rooms",
            "beds",
            "services",
            "operating_hours",
        )
    )


@login_required
def facility_list(request: HttpRequest) -> HttpResponse:
    query = request.GET.get("q", "").strip()
    facility_type = request.GET.get("facility_type", "").strip()
    status = request.GET.get("status", "active").strip()
    county = request.GET.get("county", "").strip()

    facilities = facility_queryset()

    if query:
        facilities = facilities.filter(
            Q(name__icontains=query)
            | Q(short_name__icontains=query)
            | Q(code__icontains=query)
            | Q(community_or_city__icontains=query)
            | Q(district__icontains=query)
            | Q(county_or_state__icontains=query)
        )

    if facility_type:
        facilities = facilities.filter(facility_type=facility_type)

    if county:
        facilities = facilities.filter(county_or_state__iexact=county)

    if status == "active":
        facilities = facilities.filter(is_active=True)
    elif status == "inactive":
        facilities = facilities.filter(is_active=False)
    elif status:
        facilities = facilities.filter(operational_status=status)

    paginator = Paginator(facilities, FACILITY_PAGE_SIZE)
    page = paginator.get_page(request.GET.get("page"))

    context = {
        "page_obj": page,
        "facilities": page.object_list,
        "query": query,
        "selected_type": facility_type,
        "selected_status": status,
        "selected_county": county,
        "facility_types": Facility.FacilityType.choices,
        "operational_statuses": Facility.OperationalStatus.choices,
        "active_primary_nav": "administration",
        "active_secondary_nav": "facilities",
    }

    template = (
        "facilities/partials/facility_table.html"
        if is_htmx(request)
        else "facilities/facility_list.html"
    )

    return render(request, template, context)


@login_required
def facility_search(request: HttpRequest) -> HttpResponse:
    query = request.GET.get("q", "").strip()
    facilities = Facility.objects.none()

    if len(query) >= 2:
        facilities = Facility.objects.search(query).filter(is_active=True)[:12]

    return render(
        request,
        "facilities/partials/search_results.html",
        {
            "query": query,
            "facilities": facilities,
        },
    )


@login_required
def facility_detail(request: HttpRequest, facility_id) -> HttpResponse:
    facility = get_object_or_404(facility_queryset(), pk=facility_id)

    context = {
        "facility": facility,
        "active_primary_nav": "administration",
        "active_secondary_nav": "facilities",
    }

    template = (
        "facilities/partials/facility_detail.html"
        if is_htmx(request)
        else "facilities/facility_detail.html"
    )

    return render(request, template, context)


class FacilityCreateView(LoginRequiredMixin, CreateView):
    model = Facility
    form_class = FacilityForm
    template_name = "facilities/facility_form.html"

    def get_template_names(self):
        if is_htmx(self.request):
            return ["facilities/partials/facility_form.html"]
        return [self.template_name]

    def form_valid(self, form):
        facility = form.save(commit=False)
        facility.created_by = self.request.user
        facility.updated_by = self.request.user
        facility.save()
        self.object = facility

        if is_htmx(self.request):
            response = HttpResponse(status=204)
            response["HX-Trigger"] = "facilityCreated"
            response["HX-Redirect"] = reverse(
                "facilities:detail",
                kwargs={"facility_id": facility.pk},
            )
            return response

        return redirect("facilities:detail", facility_id=facility.pk)


class FacilityUpdateView(LoginRequiredMixin, UpdateView):
    model = Facility
    form_class = FacilityForm
    pk_url_kwarg = "facility_id"
    template_name = "facilities/facility_form.html"

    def get_template_names(self):
        if is_htmx(self.request):
            return ["facilities/partials/facility_form.html"]
        return [self.template_name]

    def form_valid(self, form):
        facility = form.save(commit=False)
        facility.updated_by = self.request.user
        facility.save()
        self.object = facility

        if is_htmx(self.request):
            response = HttpResponse(status=204)
            response["HX-Trigger"] = "facilityUpdated"
            return response

        return redirect("facilities:detail", facility_id=facility.pk)


class FacilityDeleteView(LoginRequiredMixin, DeleteView):
    model = Facility
    pk_url_kwarg = "facility_id"
    template_name = "facilities/facility_confirm_delete.html"
    success_url = reverse_lazy("facilities:list")

    def get_template_names(self):
        if is_htmx(self.request):
            return ["facilities/partials/facility_confirm_delete.html"]
        return [self.template_name]

    def form_valid(self, form):
        response = super().form_valid(form)

        if is_htmx(self.request):
            htmx_response = HttpResponse(status=204)
            htmx_response["HX-Trigger"] = "facilityDeleted"
            htmx_response["HX-Redirect"] = reverse("facilities:list")
            return htmx_response

        return response


CHILD_CONFIG = {
    "department": (
        Department,
        DepartmentForm,
        "departments",
    ),
    "unit": (
        ClinicalUnit,
        ClinicalUnitForm,
        "clinical_units",
    ),
    "room": (
        Room,
        RoomForm,
        "rooms",
    ),
    "bed": (
        Bed,
        BedForm,
        "beds",
    ),
    "service": (
        FacilityService,
        FacilityServiceForm,
        "services",
    ),
    "hours": (
        FacilityOperatingHour,
        FacilityOperatingHourForm,
        "operating_hours",
    ),
}


def _child_config(kind: str):
    try:
        return CHILD_CONFIG[kind]
    except KeyError as exc:
        raise Http404("Unsupported facility record type.") from exc


@login_required
def facility_child_list(
    request: HttpRequest,
    facility_id,
    kind: str,
) -> HttpResponse:
    facility = get_object_or_404(Facility, pk=facility_id)
    model_class, _, related_name = _child_config(kind)
    records = getattr(facility, related_name).all()

    return render(
        request,
        "facilities/partials/child_list.html",
        {
            "facility": facility,
            "records": records,
            "kind": kind,
            "model_name": model_class._meta.verbose_name,
        },
    )


@login_required
def facility_child_create(
    request: HttpRequest,
    facility_id,
    kind: str,
) -> HttpResponse:
    facility = get_object_or_404(Facility, pk=facility_id)
    model_class, form_class, _ = _child_config(kind)

    initial = {"facility": facility}
    form = form_class(request.POST or None, initial=initial)

    if "facility" in form.fields:
        form.fields["facility"].queryset = Facility.objects.filter(
            pk=facility.pk
        )

    if request.method == "POST" and form.is_valid():
        record = form.save(commit=False)

        if hasattr(record, "facility_id"):
            record.facility = facility
        if hasattr(record, "created_by_id"):
            record.created_by = request.user
        if hasattr(record, "updated_by_id"):
            record.updated_by = request.user

        record.save()

        if is_htmx(request):
            response = HttpResponse(status=204)
            response["HX-Trigger"] = "facilityChildSaved"
            return response

        return redirect("facilities:detail", facility_id=facility.pk)

    template = (
        "facilities/partials/child_form.html"
        if is_htmx(request)
        else "facilities/child_form.html"
    )

    return render(
        request,
        template,
        {
            "facility": facility,
            "form": form,
            "kind": kind,
            "record": None,
        },
    )


@login_required
def facility_child_update(
    request: HttpRequest,
    facility_id,
    kind: str,
    record_id,
) -> HttpResponse:
    facility = get_object_or_404(Facility, pk=facility_id)
    model_class, form_class, _ = _child_config(kind)
    record = get_object_or_404(
        model_class,
        pk=record_id,
        facility=facility,
    )

    form = form_class(request.POST or None, instance=record)

    if "facility" in form.fields:
        form.fields["facility"].queryset = Facility.objects.filter(
            pk=facility.pk
        )

    if request.method == "POST" and form.is_valid():
        record = form.save(commit=False)

        if hasattr(record, "updated_by_id"):
            record.updated_by = request.user

        record.save()

        if is_htmx(request):
            response = HttpResponse(status=204)
            response["HX-Trigger"] = "facilityChildSaved"
            return response

        return redirect("facilities:detail", facility_id=facility.pk)

    template = (
        "facilities/partials/child_form.html"
        if is_htmx(request)
        else "facilities/child_form.html"
    )

    return render(
        request,
        template,
        {
            "facility": facility,
            "form": form,
            "kind": kind,
            "record": record,
        },
    )


@login_required
def facility_child_delete(
    request: HttpRequest,
    facility_id,
    kind: str,
    record_id,
) -> HttpResponse:
    facility = get_object_or_404(Facility, pk=facility_id)
    model_class, _, _ = _child_config(kind)
    record = get_object_or_404(
        model_class,
        pk=record_id,
        facility=facility,
    )

    if request.method == "POST":
        record.delete()

        if is_htmx(request):
            response = HttpResponse(status=204)
            response["HX-Trigger"] = "facilityChildDeleted"
            return response

        return redirect("facilities:detail", facility_id=facility.pk)

    return render(
        request,
        "facilities/partials/child_confirm_delete.html",
        {
            "facility": facility,
            "record": record,
            "kind": kind,
        },
    )


@login_required
def departments_for_facility(
    request: HttpRequest,
    facility_id,
) -> HttpResponse:
    departments = Department.objects.filter(
        facility_id=facility_id,
        is_active=True,
    ).order_by("name")

    return render(
        request,
        "facilities/partials/department_options.html",
        {"departments": departments},
    )


@login_required
def units_for_facility(
    request: HttpRequest,
    facility_id,
) -> HttpResponse:
    units = ClinicalUnit.objects.filter(
        facility_id=facility_id,
        is_active=True,
    ).order_by("name")

    return render(
        request,
        "facilities/partials/unit_options.html",
        {"units": units},
    )


@login_required
def rooms_for_unit(
    request: HttpRequest,
    unit_id,
) -> HttpResponse:
    rooms = Room.objects.filter(
        clinical_unit_id=unit_id,
        is_active=True,
    ).order_by("name")

    return render(
        request,
        "facilities/partials/room_options.html",
        {"rooms": rooms},
    )
