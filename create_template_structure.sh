#!/usr/bin/env bash

set -euo pipefail

PROJECT_ROOT="${1:-$(pwd)}"

if [[ ! -f "$PROJECT_ROOT/manage.py" ]]; then
    echo "Error: manage.py was not found in:"
    echo "$PROJECT_ROOT"
    echo
    echo "Run this script from the Liberia EHR project root."
    exit 1
fi

create_file() {
    local file="$1"
    local content="${2:-}"

    mkdir -p "$(dirname "$file")"

    if [[ -f "$file" ]]; then
        echo "Skipped existing file: ${file#$PROJECT_ROOT/}"
    else
        printf "%s\n" "$content" > "$file"
        echo "Created: ${file#$PROJECT_ROOT/}"
    fi
}

echo "Creating template structure in $PROJECT_ROOT"
echo

# =========================================================
# Project-level shared templates
# =========================================================

mkdir -p \
    "$PROJECT_ROOT/templates/layouts" \
    "$PROJECT_ROOT/templates/components" \
    "$PROJECT_ROOT/templates/includes" \
    "$PROJECT_ROOT/templates/errors" \
    "$PROJECT_ROOT/templates/registration"

create_file "$PROJECT_ROOT/templates/base.html" \
'{% load static %}
<!doctype html>
<html lang="en" class="h-full bg-slate-100">
<head>
    <meta charset="utf-8">

    <meta
        name="viewport"
        content="width=device-width, initial-scale=1"
    >

    <title>
        {% block title %}
            Liberia EHR
        {% endblock %}
    </title>

    <link
        rel="stylesheet"
        href="{% static '\''dist/css/app.css'\'' %}"
    >

    <script
        src="https://unpkg.com/htmx.org@2.0.4"
        defer
    ></script>

    <script
        src="https://unpkg.com/alpinejs@3.x.x/dist/cdn.min.js"
        defer
    ></script>
</head>

<body
    class="h-full bg-slate-100 text-slate-900"
    hx-headers='\''{"X-CSRFToken": "{{ csrf_token }}"}'\''
>
    {% block body %}{% endblock %}

    {% include "components/loading_indicator.html" %}

    <div id="modal-root"></div>
    <div id="toast-root"></div>
</body>
</html>'

create_file "$PROJECT_ROOT/templates/layouts/app_shell.html" \
'{% extends "base.html" %}

{% block body %}
<div class="grid h-screen grid-rows-[auto_auto_minmax(0,1fr)]">

    {% include "components/primary_nav.html" %}

    <div id="secondary-navigation">
        {% include "components/secondary_nav.html" %}
    </div>

    <div class="grid min-h-0 grid-cols-1 lg:grid-cols-[17rem_minmax(0,1fr)]">

        <aside
            id="patient-sidebar"
            class="hidden min-h-0 overflow-y-auto bg-ehr-900 text-white lg:block"
        >
            {% block patient_sidebar %}
                {% include "components/patient_sidebar.html" %}
            {% endblock %}
        </aside>

        <main
            id="workspace"
            class="min-h-0 min-w-0 overflow-y-auto bg-slate-50 p-4 md:p-6"
        >
            {% block workspace %}{% endblock %}
        </main>

    </div>
</div>
{% endblock %}'

create_file "$PROJECT_ROOT/templates/layouts/auth_shell.html" \
'{% extends "base.html" %}

{% block body %}
<main class="grid min-h-screen place-items-center bg-slate-100 p-4">
    <section class="w-full max-w-md rounded-xl border border-slate-200 bg-white p-6 shadow">
        {% block auth_content %}{% endblock %}
    </section>
</main>
{% endblock %}'

create_file "$PROJECT_ROOT/templates/layouts/print_shell.html" \
'{% extends "base.html" %}

{% block body %}
<main class="mx-auto max-w-5xl bg-white p-8">
    {% block print_content %}{% endblock %}
</main>
{% endblock %}'

shared_components=(
    primary_nav.html
    secondary_nav.html
    patient_sidebar.html
    workspace_header.html
    summary_card.html
    stat_card.html
    cds_alert.html
    alert.html
    modal.html
    drawer.html
    pagination.html
    empty_state.html
    form_errors.html
    loading_indicator.html
)

for component in "${shared_components[@]}"; do
    create_file \
        "$PROJECT_ROOT/templates/components/$component" \
        "{# Shared EHR component: $component #}"
done

create_file "$PROJECT_ROOT/templates/components/loading_indicator.html" \
'<div
    id="global-loading"
    class="htmx-indicator fixed bottom-5 right-5 z-50 rounded-lg bg-slate-950 px-4 py-2 text-sm font-medium text-white shadow-xl"
>
    Loading...
</div>'

create_file "$PROJECT_ROOT/templates/includes/messages.html" \
'{% if messages %}
    <div class="space-y-3">
        {% for message in messages %}
            <div class="rounded-lg border border-slate-200 bg-white px-4 py-3 shadow-sm">
                {{ message }}
            </div>
        {% endfor %}
    </div>
{% endif %}'

create_file "$PROJECT_ROOT/templates/registration/login.html" \
'{% extends "layouts/auth_shell.html" %}

{% block title %}
    Login | Liberia EHR
{% endblock %}

{% block auth_content %}
<h1 class="text-2xl font-bold text-ehr-900">
    Staff Login
</h1>

<form method="post" class="mt-6 space-y-4">
    {% csrf_token %}

    {{ form.as_p }}

    <button
        type="submit"
        class="w-full rounded-lg bg-ehr-800 px-4 py-2 font-semibold text-white"
    >
        Login
    </button>
</form>
{% endblock %}'

for code in 400 403 404 500; do
    create_file "$PROJECT_ROOT/templates/errors/$code.html" \
"{% extends \"base.html\" %}

{% block body %}
<main class=\"grid min-h-screen place-items-center p-6\">
    <div class=\"text-center\">
        <h1 class=\"text-5xl font-bold text-ehr-900\">
            $code
        </h1>

        <p class=\"mt-3 text-slate-600\">
            An error occurred while processing your request.
        </p>
    </div>
</main>
{% endblock %}"
done

# =========================================================
# Django apps
# =========================================================

apps=(
    core
    accounts
    facilities
    patients
    encounters
    nursing
    vitals
    diagnoses
    medications
    orders
    laboratories
    imaging
    care_management
    documents
    flowsheets
    analytics
    decision_support
    ai_assistant
    audit
    notifications
)

for app in "${apps[@]}"; do

    template_dir="$PROJECT_ROOT/apps/$app/templates/$app"

    mkdir -p \
        "$template_dir/partials" \
        "$template_dir/components"

    create_file "$template_dir/index.html" \
"{% extends \"layouts/app_shell.html\" %}

{% block title %}
    $app | Liberia EHR
{% endblock %}

{% block workspace %}
<section>
    <h1 class=\"text-2xl font-bold capitalize\">
        $app
    </h1>
</section>
{% endblock %}"

    create_file "$template_dir/list.html" \
"{% extends \"layouts/app_shell.html\" %}

{% block title %}
    $app List | Liberia EHR
{% endblock %}

{% block workspace %}
<section>
    <h1 class=\"text-2xl font-bold capitalize\">
        $app List
    </h1>

    <div id=\"${app}-list\" class=\"mt-5\">
        {% include \"$app/partials/list_content.html\" %}
    </div>
</section>
{% endblock %}"

    create_file "$template_dir/detail.html" \
"{% extends \"layouts/app_shell.html\" %}

{% block title %}
    $app Details | Liberia EHR
{% endblock %}

{% block workspace %}
<section>
    <h1 class=\"text-2xl font-bold capitalize\">
        $app Details
    </h1>

    <div id=\"${app}-detail\" class=\"mt-5\">
        {% include \"$app/partials/detail_content.html\" %}
    </div>
</section>
{% endblock %}"

    create_file "$template_dir/form.html" \
"{% extends \"layouts/app_shell.html\" %}

{% block title %}
    $app Form | Liberia EHR
{% endblock %}

{% block workspace %}
<section class=\"max-w-3xl\">
    <h1 class=\"text-2xl font-bold capitalize\">
        $app Form
    </h1>

    <form method=\"post\" class=\"mt-6 space-y-4\">
        {% csrf_token %}

        {% include \"$app/partials/form_fields.html\" %}

        <button
            type=\"submit\"
            class=\"rounded-lg bg-ehr-800 px-4 py-2 font-semibold text-white\"
        >
            Save
        </button>
    </form>
</section>
{% endblock %}"

    create_file "$template_dir/confirm_delete.html" \
"{% extends \"layouts/app_shell.html\" %}

{% block title %}
    Delete Record | Liberia EHR
{% endblock %}

{% block workspace %}
<section class=\"max-w-xl rounded-xl border border-red-200 bg-white p-6\">
    <h1 class=\"text-xl font-bold text-red-700\">
        Confirm deletion
    </h1>

    <p class=\"mt-3 text-slate-600\">
        Are you sure you want to delete this record?
    </p>

    <form method=\"post\" class=\"mt-5 flex gap-3\">
        {% csrf_token %}

        <button
            type=\"submit\"
            class=\"rounded-lg bg-red-600 px-4 py-2 font-semibold text-white\"
        >
            Delete
        </button>

        <a
            href=\"javascript:history.back()\"
            class=\"rounded-lg border border-slate-300 px-4 py-2\"
        >
            Cancel
        </a>
    </form>
</section>
{% endblock %}"

    create_file "$template_dir/partials/list_content.html" \
"{# HTMX list partial for $app #}

<div class=\"rounded-xl border border-slate-200 bg-white p-5 shadow-sm\">
    <p class=\"text-slate-500\">
        No records available.
    </p>
</div>"

    create_file "$template_dir/partials/detail_content.html" \
"{# HTMX detail partial for $app #}

<div class=\"rounded-xl border border-slate-200 bg-white p-5 shadow-sm\">
    <p class=\"text-slate-500\">
        Record details will appear here.
    </p>
</div>"

    create_file "$template_dir/partials/form_fields.html" \
"{# HTMX form fields partial for $app #}

{{ form.as_p }}"

    create_file "$template_dir/partials/table_rows.html" \
"{# HTMX table rows partial for $app #}"

    create_file "$template_dir/components/card.html" \
"{# Reusable $app card component #}"

done

# =========================================================
# Core templates
# =========================================================

core_templates=(
    dashboard.html
    clinical_overview.html
)

for file in "${core_templates[@]}"; do
    create_file "$PROJECT_ROOT/apps/core/templates/core/$file" \
"{% extends \"layouts/app_shell.html\" %}

{% block title %}
    ${file%.html} | Liberia EHR
{% endblock %}

{% block workspace %}
<section>
    <h1 class=\"text-2xl font-bold\">
        ${file%.html}
    </h1>
</section>
{% endblock %}"
done

# =========================================================
# Patient templates
# =========================================================

patient_templates=(
    patient_list.html
    patient_detail.html
    patient_form.html
    patient_overview.html
    patient_search.html
    patient_merge.html
)

for file in "${patient_templates[@]}"; do
    create_file "$PROJECT_ROOT/apps/patients/templates/patients/$file" \
"{% extends \"layouts/app_shell.html\" %}

{% block title %}
    ${file%.html} | Liberia EHR
{% endblock %}

{% block workspace %}
<section>
    <h1 class=\"text-2xl font-bold\">
        ${file%.html}
    </h1>
</section>
{% endblock %}"
done

patient_partials=(
    search_results.html
    patient_sidebar.html
    patient_table.html
    patient_overview.html
    demographics.html
    allergies.html
    active_problems.html
    emergency_contacts.html
)

for file in "${patient_partials[@]}"; do
    create_file \
        "$PROJECT_ROOT/apps/patients/templates/patients/partials/$file" \
        "{# Patients HTMX partial: $file #}"
done

# =========================================================
# Encounter templates
# =========================================================

encounter_templates=(
    encounter_list.html
    encounter_detail.html
    admission_form.html
    transfer_form.html
    discharge_form.html
    timeline.html
)

for file in "${encounter_templates[@]}"; do
    create_file \
        "$PROJECT_ROOT/apps/encounters/templates/encounters/$file" \
        "{% extends \"layouts/app_shell.html\" %}

{% block workspace %}
<h1 class=\"text-2xl font-bold\">
    ${file%.html}
</h1>
{% endblock %}"
done

# =========================================================
# Nursing templates
# =========================================================

nursing_templates=(
    assessment_list.html
    assessment_form.html
    nursing_notes.html
    care_plan.html
    handoff.html
    task_list.html
    intake_output.html
    pain_assessment.html
    fall_risk_assessment.html
)

for file in "${nursing_templates[@]}"; do
    create_file \
        "$PROJECT_ROOT/apps/nursing/templates/nursing/$file" \
        "{% extends \"layouts/app_shell.html\" %}

{% block workspace %}
<h1 class=\"text-2xl font-bold\">
    ${file%.html}
</h1>
{% endblock %}"
done

nursing_partials=(
    assessment_form.html
    nursing_notes.html
    care_plan.html
    handoff_summary.html
    task_rows.html
    intake_output_table.html
)

for file in "${nursing_partials[@]}"; do
    create_file \
        "$PROJECT_ROOT/apps/nursing/templates/nursing/partials/$file" \
        "{# Nursing HTMX partial: $file #}"
done

# =========================================================
# Vitals templates
# =========================================================

vital_templates=(
    vital_list.html
    vital_form.html
    vital_trends.html
    observation_history.html
)

for file in "${vital_templates[@]}"; do
    create_file \
        "$PROJECT_ROOT/apps/vitals/templates/vitals/$file" \
        "{% extends \"layouts/app_shell.html\" %}

{% block workspace %}
<h1 class=\"text-2xl font-bold\">
    ${file%.html}
</h1>
{% endblock %}"
done

vital_partials=(
    vital_table.html
    vital_chart.html
    recent_vitals.html
    vital_form.html
    abnormal_vitals.html
)

for file in "${vital_partials[@]}"; do
    create_file \
        "$PROJECT_ROOT/apps/vitals/templates/vitals/partials/$file" \
        "{# Vitals HTMX partial: $file #}"
done

# =========================================================
# Medication templates
# =========================================================

medication_templates=(
    medication_list.html
    medication_detail.html
    reconciliation.html
    prescription_form.html
    administration_record.html
    allergy_list.html
    adverse_reactions.html
)

for file in "${medication_templates[@]}"; do
    create_file \
        "$PROJECT_ROOT/apps/medications/templates/medications/$file" \
        "{% extends \"layouts/app_shell.html\" %}

{% block workspace %}
<h1 class=\"text-2xl font-bold\">
    ${file%.html}
</h1>
{% endblock %}"
done

# =========================================================
# Order templates
# =========================================================

order_templates=(
    order_list.html
    order_detail.html
    order_form.html
    order_status.html
    laboratory_order.html
    medication_order.html
    imaging_order.html
    nursing_order.html
)

for file in "${order_templates[@]}"; do
    create_file \
        "$PROJECT_ROOT/apps/orders/templates/orders/$file" \
        "{% extends \"layouts/app_shell.html\" %}

{% block workspace %}
<h1 class=\"text-2xl font-bold\">
    ${file%.html}
</h1>
{% endblock %}"
done

# =========================================================
# Laboratory templates
# =========================================================

laboratory_templates=(
    lab_order_list.html
    specimen_list.html
    specimen_collection.html
    result_entry.html
    result_detail.html
    result_verification.html
    critical_results.html
)

for file in "${laboratory_templates[@]}"; do
    create_file \
        "$PROJECT_ROOT/apps/laboratories/templates/laboratories/$file" \
        "{% extends \"layouts/app_shell.html\" %}

{% block workspace %}
<h1 class=\"text-2xl font-bold\">
    ${file%.html}
</h1>
{% endblock %}"
done

# =========================================================
# Analytics templates
# =========================================================

analytics_templates=(
    clinical_dashboard.html
    nursing_dashboard.html
    quality_dashboard.html
    operations_dashboard.html
    surveillance_dashboard.html
    patient_outcomes.html
)

for file in "${analytics_templates[@]}"; do
    create_file \
        "$PROJECT_ROOT/apps/analytics/templates/analytics/$file" \
        "{% extends \"layouts/app_shell.html\" %}

{% block workspace %}
<h1 class=\"text-2xl font-bold\">
    ${file%.html}
</h1>
{% endblock %}"
done

analytics_partials=(
    summary_cards.html
    trend_chart.html
    quality_indicators.html
    filters.html
    outcome_table.html
)

for file in "${analytics_partials[@]}"; do
    create_file \
        "$PROJECT_ROOT/apps/analytics/templates/analytics/partials/$file" \
        "{# Analytics HTMX partial: $file #}"
done

# =========================================================
# Decision-support templates
# =========================================================

decision_support_templates=(
    alert_list.html
    alert_detail.html
    recommendation_review.html
    override_form.html
    rules_dashboard.html
)

for file in "${decision_support_templates[@]}"; do
    create_file \
        "$PROJECT_ROOT/apps/decision_support/templates/decision_support/$file" \
        "{% extends \"layouts/app_shell.html\" %}

{% block workspace %}
<h1 class=\"text-2xl font-bold\">
    ${file%.html}
</h1>
{% endblock %}"
done

cds_partials=(
    alert_card.html
    recommendation_panel.html
    risk_score.html
    acknowledgment_form.html
    override_form.html
)

for file in "${cds_partials[@]}"; do
    create_file \
        "$PROJECT_ROOT/apps/decision_support/templates/decision_support/partials/$file" \
        "{# Decision-support HTMX partial: $file #}"
done

# =========================================================
# AI assistant templates
# =========================================================

ai_templates=(
    assistant.html
    clinical_summary.html
    natural_language_search.html
    model_result.html
    documentation_assistant.html
)

for file in "${ai_templates[@]}"; do
    create_file \
        "$PROJECT_ROOT/apps/ai_assistant/templates/ai_assistant/$file" \
        "{% extends \"layouts/app_shell.html\" %}

{% block workspace %}
<h1 class=\"text-2xl font-bold\">
    ${file%.html}
</h1>
{% endblock %}"
done

echo
echo "Template structure created successfully."
echo
echo "Shared templates:"
echo "  templates/"
echo
echo "App templates:"
echo "  apps/<app_name>/templates/<app_name>/"
echo
echo "Existing files were not overwritten."