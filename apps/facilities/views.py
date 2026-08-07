from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.http import Http404, HttpResponse
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
def facility_list(request):
    """
    Display the paginated facility list.

    Standard request:
    - Render the complete Facilities page.

    HTMX request:
    - Render only the list workspace content.
    """

    query = request.GET.get("q", "").strip()
    facility_type = request.GET.get(
        "facility_type",
        "",
    ).strip()
    status = request.GET.get(
        "status",
        "active",
    ).strip()
    county = request.GET.get(
        "county",
        "",
    ).strip()

    facilities = facility_queryset()

    # ========================================================
    # SEARCH FILTER
    # ========================================================
    if query:
        facilities = facilities.filter(
            Q(name__icontains=query)
            | Q(short_name__icontains=query)
            | Q(code__icontains=query)
            | Q(community_or_city__icontains=query)
            | Q(district__icontains=query)
            | Q(county_or_state__icontains=query)
        )

    # ========================================================
    # FACILITY TYPE FILTER
    # ========================================================
    if facility_type:
        facilities = facilities.filter(
            facility_type=facility_type,
        )

    # ========================================================
    # COUNTY FILTER
    # ========================================================
    if county:
        facilities = facilities.filter(
            county_or_state__iexact=county,
        )

    # ========================================================
    # STATUS FILTER
    # ========================================================
    if status == "active":
        facilities = facilities.filter(
            is_active=True,
        )
    elif status == "inactive":
        facilities = facilities.filter(
            is_active=False,
        )
    elif status:
        facilities = facilities.filter(
            operational_status=status,
        )

    facilities = facilities.order_by(
        "name",
    )

    paginator = Paginator(
        facilities,
        FACILITY_PAGE_SIZE,
    )

    page_obj = paginator.get_page(
        request.GET.get("page"),
    )

    context = {
        "page_obj": page_obj,
        "facilities": page_obj.object_list,
        "query": query,
        "selected_type": facility_type,
        "selected_status": status,
        "selected_county": county,
        "facility_types": Facility.FacilityType.choices,
        "operational_statuses": (
            Facility.OperationalStatus.choices
        ),

        # Administration navigation state
        "active_primary_nav": "administration",
        "active_admin_module": "facilities",
    }

    template_name = (
        "facilities/partials/list_content.html"
        if is_htmx(request)
        else "facilities/list.html"
    )

    response = render(
        request,
        template_name,
        context,
    )

    response["Vary"] = "HX-Request"

    return response


@login_required
def facility_search(request):
    query = request.GET.get("q", "").strip()

    facilities = Facility.objects.none()

    if len(query) >= 2:
        facilities = (
            Facility.objects.search(query)
            .filter(is_active=True)[:12]
        )

    return render(
        request,
        "facilities/partials/search_results.html",
        {
            "query": query,
            "facilities": facilities,
        },
    )

@login_required
def facility_detail(
    request,
    facility_id,
):
    """
    Display one facility and its organizational records.

    Standard request:
    - Render the complete Facility Detail page.

    HTMX request:
    - Render only the facility detail workspace.
    """

    facility = get_object_or_404(
        facility_queryset(),
        pk=facility_id,
    )

    context = {
        "facility": facility,

        # Administration navigation state
        "active_primary_nav": "administration",
        "active_admin_module": "facilities",
    }

    template_name = (
        "facilities/partials/detail_content.html"
        if is_htmx(request)
        else "facilities/detail.html"
    )

    response = render(
        request,
        template_name,
        context,
    )

    response["Vary"] = "HX-Request"

    return response


class FacilityCreateView(
    LoginRequiredMixin,
    CreateView,
):
    """
    Create a new facility.
    """

    model = Facility
    form_class = FacilityForm
    template_name = "facilities/form.html"

    def get_initial(self):
        initial = super().get_initial()

        parent_facility_id = self.request.GET.get(
            "parent_facility",
        )

        if parent_facility_id:
            initial["parent_facility"] = (
                parent_facility_id
            )

        return initial

    def get_context_data(
        self,
        **kwargs,
    ):
        context = super().get_context_data(
            **kwargs,
        )

        context.update(
            {
                "form_mode": "create",
                "page_title": "Create Facility",
                "submit_label": "Create Facility",
                "active_primary_nav": (
                    "administration"
                ),
                "active_admin_module": (
                    "facilities"
                ),
            }
        )

        return context

    def form_valid(
        self,
        form,
    ):
        facility = form.save(
            commit=False,
        )

        facility.created_by = (
            self.request.user
        )
        facility.updated_by = (
            self.request.user
        )

        facility.save()

        self.object = facility

        if is_htmx(self.request):
            response = HttpResponse(
                status=204,
            )

            response["HX-Trigger"] = (
                "facilityCreated"
            )

            response["HX-Redirect"] = reverse(
                "facilities:detail",
                kwargs={
                    "facility_id": (
                        facility.pk
                    ),
                },
            )

            return response

        return redirect(
            "facilities:detail",
            facility_id=facility.pk,
        )

class FacilityUpdateView(
    LoginRequiredMixin,
    UpdateView,
):
    """
    Update an existing facility.
    """

    model = Facility
    form_class = FacilityForm
    pk_url_kwarg = "facility_id"
    template_name = "facilities/form.html"

    def get_context_data(
        self,
        **kwargs,
    ):
        context = super().get_context_data(
            **kwargs,
        )

        context.update(
            {
                "form_mode": "update",
                "page_title": "Update Facility",
                "submit_label": "Save Changes",
                "active_primary_nav": (
                    "administration"
                ),
                "active_admin_module": (
                    "facilities"
                ),
            }
        )

        return context

    def form_valid(
        self,
        form,
    ):
        facility = form.save(
            commit=False,
        )

        facility.updated_by = (
            self.request.user
        )

        facility.save()

        self.object = facility

        if is_htmx(self.request):
            response = HttpResponse(
                status=204,
            )

            response["HX-Trigger"] = (
                "facilityUpdated"
            )

            response["HX-Redirect"] = reverse(
                "facilities:detail",
                kwargs={
                    "facility_id": (
                        facility.pk
                    ),
                },
            )

            return response

        return redirect(
            "facilities:detail",
            facility_id=facility.pk,
        )

class FacilityDeleteView(
    LoginRequiredMixin,
    DeleteView,
):
    """
    Delete a facility after confirmation.
    """

    model = Facility
    pk_url_kwarg = "facility_id"
    template_name = (
        "facilities/confirm_delete.html"
    )
    success_url = reverse_lazy(
        "facilities:list",
    )

    def get_context_data(
        self,
        **kwargs,
    ):
        context = super().get_context_data(
            **kwargs,
        )

        context.update(
            {
                "active_primary_nav": (
                    "administration"
                ),
                "active_admin_module": (
                    "facilities"
                ),
            }
        )

        return context

    def form_valid(
        self,
        form,
    ):
        response = super().form_valid(
            form,
        )

        if is_htmx(self.request):
            htmx_response = HttpResponse(
                status=204,
            )

            htmx_response["HX-Trigger"] = (
                "facilityDeleted"
            )

            htmx_response["HX-Redirect"] = (
                reverse(
                    "facilities:list",
                )
            )

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


def get_child_config(kind):
    try:
        return CHILD_CONFIG[kind]
    except KeyError as exc:
        raise Http404(
            "Unsupported facility record type."
        ) from exc


@login_required
def facility_child_list(
    request,
    facility_id,
    kind,
):
    facility = get_object_or_404(
        Facility,
        pk=facility_id,
    )

    model_class, _, related_name = get_child_config(
        kind
    )

    records = getattr(
        facility,
        related_name,
    ).all()

    return render(
        request,
        "facilities/partials/child_list.html",
        {
            "facility": facility,
            "records": records,
            "kind": kind,
            "model_name": (
                model_class._meta.verbose_name
            ),
        },
    )


@login_required
def facility_child_create(
    request,
    facility_id,
    kind,
):
    facility = get_object_or_404(
        Facility,
        pk=facility_id,
    )

    _, form_class, _ = get_child_config(kind)

    form = form_class(
        request.POST or None,
        initial={
            "facility": facility,
        },
    )

    if "facility" in form.fields:
        form.fields["facility"].queryset = (
            Facility.objects.filter(
                pk=facility.pk
            )
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
            response["HX-Trigger"] = (
                "facilityChildSaved"
            )
            return response

        return redirect(
            "facilities:detail",
            facility_id=facility.pk,
        )

    template_name = (
        "facilities/partials/child_form.html"
        if is_htmx(request)
        else "facilities/child_form.html"
    )

    return render(
        request,
        template_name,
        {
            "facility": facility,
            "form": form,
            "kind": kind,
            "record": None,
        },
    )


@login_required
def facility_child_update(
    request,
    facility_id,
    kind,
    record_id,
):
    facility = get_object_or_404(
        Facility,
        pk=facility_id,
    )

    model_class, form_class, _ = get_child_config(
        kind
    )

    record = get_object_or_404(
        model_class,
        pk=record_id,
        facility=facility,
    )

    form = form_class(
        request.POST or None,
        instance=record,
    )

    if "facility" in form.fields:
        form.fields["facility"].queryset = (
            Facility.objects.filter(
                pk=facility.pk
            )
        )

    if request.method == "POST" and form.is_valid():
        record = form.save(commit=False)

        if hasattr(record, "updated_by_id"):
            record.updated_by = request.user

        record.save()

        if is_htmx(request):
            response = HttpResponse(status=204)
            response["HX-Trigger"] = (
                "facilityChildSaved"
            )
            return response

        return redirect(
            "facilities:detail",
            facility_id=facility.pk,
        )

    template_name = (
        "facilities/partials/child_form.html"
        if is_htmx(request)
        else "facilities/child_form.html"
    )

    return render(
        request,
        template_name,
        {
            "facility": facility,
            "form": form,
            "kind": kind,
            "record": record,
        },
    )


@login_required
def facility_child_delete(
    request,
    facility_id,
    kind,
    record_id,
):
    facility = get_object_or_404(
        Facility,
        pk=facility_id,
    )

    model_class, _, _ = get_child_config(kind)

    record = get_object_or_404(
        model_class,
        pk=record_id,
        facility=facility,
    )

    if request.method == "POST":
        record.delete()

        if is_htmx(request):
            response = HttpResponse(status=204)
            response["HX-Trigger"] = (
                "facilityChildDeleted"
            )
            return response

        return redirect(
            "facilities:detail",
            facility_id=facility.pk,
        )

    return render(
        request,
        "facilities/partials/"
        "child_confirm_delete.html",
        {
            "facility": facility,
            "record": record,
            "kind": kind,
        },
    )


@login_required
def departments_for_facility(
    request,
    facility_id,
):
    departments = Department.objects.filter(
        facility_id=facility_id,
        is_active=True,
    ).order_by("name")

    return render(
        request,
        "facilities/partials/"
        "department_options.html",
        {
            "departments": departments,
        },
    )


@login_required
def units_for_facility(
    request,
    facility_id,
):
    units = ClinicalUnit.objects.filter(
        facility_id=facility_id,
        is_active=True,
    ).order_by("name")

    return render(
        request,
        "facilities/partials/unit_options.html",
        {
            "units": units,
        },
    )


@login_required
def rooms_for_unit(
    request,
    unit_id,
):
    rooms = Room.objects.filter(
        clinical_unit_id=unit_id,
        is_active=True,
    ).order_by("name")

    return render(
        request,
        "facilities/partials/room_options.html",
        {
            "rooms": rooms,
        },
    )
