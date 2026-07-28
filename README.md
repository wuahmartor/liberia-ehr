Below is the upgraded README.md, aligned with your selected Design Option 4: Analytics-Focused EHR layout, Django architecture, HTMX interactions, and Tailwind CSS styling.

Liberia EHR

Liberia EHR is a modular, analytics-enabled Electronic Health Record platform designed to support clinical care, nursing informatics, healthcare data analytics, and responsibly governed clinical decision support.

The platform is being developed for healthcare environments where affordability, usability, reliability, interoperability, and limited infrastructure must all be considered—including hospitals, clinics, community health centers, and public-health programs in Liberia.

Project status: Active development.
This software is not yet certified or approved for production clinical use.

⸻

Table of Contents

* Project Vision⁠￼
* Core Objectives⁠￼
* Key Features⁠￼
* User Roles⁠￼
* Technology Stack⁠￼
* System Architecture⁠￼
* Design Option 4: Analytics-Focused Layout⁠￼
* Project Structure⁠￼
* Template Architecture⁠￼
* Django Application Responsibilities⁠￼
* Recommended Internal App Pattern⁠￼
* Database Strategy⁠￼
* HTMX Strategy⁠￼
* Alpine.js Responsibilities⁠￼
* Tailwind CSS Design System⁠￼
* Clinical Decision Support⁠￼
* Artificial Intelligence Governance⁠￼
* Analytics and Nursing Informatics⁠￼
* Security and Clinical Safety⁠￼
* Audit Logging⁠￼
* Local Development Setup⁠￼
* PostgreSQL Setup⁠￼
* Docker Setup⁠￼
* Testing⁠￼
* Development Standards⁠￼
* Suggested Implementation Order⁠￼
* Initial Milestone⁠￼
* Future Roadmap⁠￼
* Contributing⁠￼
* License⁠￼
* Clinical Disclaimer⁠￼

⸻

Project Vision

Liberia EHR aims to provide a practical healthcare information platform that combines:

* Patient registration and longitudinal health records
* Clinical documentation
* Nursing workflows
* Medication and order management
* Laboratory and imaging workflows
* Public-health and facility analytics
* Nursing informatics
* Rule-based clinical decision support
* Carefully governed artificial intelligence
* Role-based and facility-based access control
* Complete patient-record audit trails

The long-term goal is to support safer clinical care and better healthcare decision-making while remaining adaptable to the infrastructure and operational realities of Liberia.

⸻

Core Objectives

The project is designed around the following objectives:

1. Improve continuity of care
    Maintain a longitudinal patient record across encounters, departments, and healthcare facilities.
2. Support nursing practice
    Provide structured nursing assessments, care plans, flowsheets, handoff documentation, and task management.
3. Improve clinical visibility
    Present vital signs, laboratory results, medications, diagnoses, allergies, orders, notes, and care plans in one coordinated workspace.
4. Enable healthcare analytics
    Support clinical, operational, quality, nursing, and public-health dashboards.
5. Strengthen patient safety
    Introduce allergy warnings, abnormal-result alerts, medication checks, deterioration rules, and clinical reminders.
6. Support resource-limited environments
    Use a server-rendered architecture that minimizes unnecessary browser complexity and can be adapted for constrained networks.
7. Maintain human oversight
    Ensure that clinical decision support and AI outputs remain explainable, reviewable, attributable, and subordinate to clinician judgment.
8. Promote modular development
    Separate major clinical domains into independent Django applications with predictable internal structures.

⸻

Key Features

Patient Management

* Patient registration
* Medical record number generation
* National and facility-specific identifiers
* Demographic information
* Address and contact information
* Emergency contacts
* Next-of-kin information
* Patient photographs or generated initials
* Patient search by name, MRN, phone number, date of birth, or identifier
* Duplicate-patient review
* Patient merge workflow
* Patient status management
* Deceased-patient documentation
* Patient archival without destructive deletion

Encounter Management

* Outpatient visits
* Emergency encounters
* Inpatient admissions
* Transfers
* Discharges
* Encounter timelines
* Assigned clinicians
* Care-team membership
* Encounter status tracking
* Visit-reason documentation
* Admission and discharge diagnoses
* Follow-up instructions

Nursing Informatics

* Nursing intake assessments
* Head-to-toe assessments
* Nursing notes
* Care plans
* Nursing diagnoses
* Patient goals and interventions
* Shift handoff
* Intake and output
* Pain assessment
* Fall-risk assessment
* Pressure-injury risk assessment
* Neurological observations
* Nursing task lists
* Escalation documentation
* Structured flowsheets

Clinical Documentation

* Problems and diagnoses
* Allergies and reactions
* Vital signs
* Clinical notes
* Progress notes
* History and physical examination
* Procedure documentation
* Clinical summaries
* Document uploads
* Encounter and patient timelines

Medication Management

* Medication catalog
* Medication reconciliation
* Prescriptions
* Medication orders
* Medication administration records
* Dose and frequency documentation
* Route of administration
* Start and stop dates
* Allergy checks
* Duplicate-therapy warnings
* Contraindication rules
* Medication status tracking

Orders and Results

* Laboratory orders
* Imaging orders
* Medication orders
* Procedure orders
* Nursing orders
* Order lifecycle tracking
* Specimen collection
* Laboratory result entry
* Result verification
* Reference ranges
* Abnormal-result flags
* Critical-result acknowledgment
* Imaging reports
* Order cancellation and discontinuation

Care Management

* Multidisciplinary care plans
* Referrals
* Follow-up tasks
* Discharge planning
* Social needs documentation
* Care-team coordination
* Patient education
* Appointment and follow-up reminders
* Case-management notes

Analytics

* Clinical dashboards
* Nursing dashboards
* Facility operations dashboards
* Quality-improvement dashboards
* Disease-surveillance dashboards
* Medication-use dashboards
* Laboratory turnaround-time monitoring
* Admission and discharge trends
* Patient-volume analysis
* Staff workload indicators
* Clinical alert monitoring
* Patient outcome indicators

Decision Support

* Abnormal vital-sign alerts
* Critical laboratory alerts
* Allergy warnings
* Medication contraindication checks
* Duplicate medication warnings
* Fall-risk reminders
* Sepsis screening rules
* Deterioration alerts
* Clinical follow-up reminders
* Alert acknowledgment
* Override-reason documentation
* Rule-version tracking

⸻

User Roles

The authorization system should support configurable roles rather than relying only on Django’s default staff and superuser flags.

Suggested roles include:

* System administrator
* Facility administrator
* Department administrator
* Physician
* Physician assistant
* Nurse practitioner
* Registered nurse
* Licensed practical nurse
* Nursing assistant
* Pharmacist
* Pharmacy technician
* Laboratory scientist
* Laboratory technician
* Radiology staff
* Medical records officer
* Registration staff
* Care manager
* Social worker
* Data analyst
* Quality-improvement officer
* Public-health officer
* Auditor

Permissions should be assigned through Django groups, model permissions, custom domain permissions, and object-level authorization.

⸻

Technology Stack

Layer	Technology
Backend framework	Django
Programming language	Python
Dynamic server-rendered UI	HTMX
Lightweight browser interaction	Alpine.js
Styling	Tailwind CSS
Production database	PostgreSQL
Local development database	SQLite
Background jobs	Celery or Django-Q, planned
Task broker and cache	Redis, planned
Testing	Pytest and pytest-django
Application server	Gunicorn
Reverse proxy	Nginx
Containerization	Docker and Docker Compose
Analytics foundation	Python and Django services
Clinical decision support	Versioned rules engine
AI integration	Governed model-service adapters
Version control	Git and GitHub

Database Policy

* SQLite is used for lightweight local development and testing.
* PostgreSQL is the recommended database for staging and production.
* PostgreSQL should be used when developing features that depend on:
    * Full-text search
    * Trigram similarity
    * JSON fields
    * Advanced indexing
    * Concurrent users
    * Production-grade transactional behavior

⸻

System Architecture

Liberia EHR follows a modular Django architecture.

┌────────────────────────────────────────────────────────────────────┐
│                         Browser Interface                           │
│                                                                    │
│             Tailwind CSS + HTMX + Alpine.js                        │
└────────────────────────────────┬───────────────────────────────────┘
                                 │
                                 │ HTTPS requests
                                 ▼
┌────────────────────────────────────────────────────────────────────┐
│                         Django Web Layer                            │
│                                                                    │
│  URL routing → permissions → views → forms → templates/partials   │
└────────────────────────────────┬───────────────────────────────────┘
                                 │
                                 ▼
┌────────────────────────────────────────────────────────────────────┐
│                      Domain Service Layer                           │
│                                                                    │
│  Patients | Encounters | Nursing | Orders | Medications | CDS     │
└────────────────────────────────┬───────────────────────────────────┘
                                 │
                                 ▼
┌────────────────────────────────────────────────────────────────────┐
│                          Data Layer                                 │
│                                                                    │
│        Django ORM → PostgreSQL or SQLite → Audit Records           │
└────────────────────────────────┬───────────────────────────────────┘
                                 │
                                 ▼
┌────────────────────────────────────────────────────────────────────┐
│                 Analytics and Integration Layer                     │
│                                                                    │
│ Dashboards | Reporting | Rules Engine | AI Adapters | APIs         │
└────────────────────────────────────────────────────────────────────┘

Architectural Principles

* Django remains the owner of clinical state.
* HTMX updates server-rendered fragments.
* Alpine.js manages presentation state only.
* Service functions coordinate write operations.
* Selector functions coordinate complex read operations.
* Clinical rules are versioned and testable.
* All sensitive record access is auditable.
* AI features are isolated behind governed service adapters.
* Clinical records should not be permanently deleted through ordinary workflows.

⸻

Design Option 4: Analytics-Focused Layout

Liberia EHR uses the selected Design Option 4: Analytics-Focused application shell.

The interface contains four persistent regions.

1. Primary Navigation

The first navigation row controls the major system domain:

* Clinical
* Nursing
* Analytics
* AI/CDS
* Orders
* Medication
* Care Management
* Administration

2. Contextual Secondary Navigation

The second navigation row changes according to the selected primary module.

For example, under Clinical → Patients, the secondary navigation may contain:

* Patient search
* Patient list
* Recent patients
* Register patient
* Admit
* Transfer
* Discharge
* Clinical alerts
* Additional actions

3. Patient Context Sidebar

When a patient is selected, the left sidebar displays persistent patient context:

* Patient photograph or initials
* Full name
* Medical record number
* Date of birth
* Age
* Sex
* Patient status
* Current location
* Current encounter
* Allergies
* Clinical alerts
* Overview
* Clinical summary
* Vitals and laboratories
* Medications
* Problems
* Care plan
* Notes
* Documents
* Flowsheets

4. Analytics-Focused Workspace

The central workspace supports:

* Clinical overview
* Summary cards
* Vital-sign trends
* Laboratory trends
* Medication status
* Intake and output
* Pain trends
* Encounter timelines
* Nursing documentation
* Clinical forms
* Orders and results
* AI/CDS recommendations
* Risk alerts
* Analytics visualizations
* Drill-down tables
* Time-range filtering

┌──────────────────────────────────────────────────────────────────────────────┐
│ Clinical | Nursing | Analytics | AI/CDS | Orders | Medication | Admin       │
├──────────────────────────────────────────────────────────────────────────────┤
│ Patients | Search | Recent | Register | Admit | Transfer | Discharge        │
├──────────────────────┬───────────────────────────────────────────────────────┤
│ Patient Context      │ Clinical Overview                     Last 24 Hours   │
│                      ├───────────────────────────────────────────────────────┤
│ Identity             │ Vitals | Labs | Medications | I/O | Pain             │
│ Encounter            ├────────────────────────────────┬──────────────────────┤
│ Alerts               │ Clinical Trends                │ AI/CDS Alerts        │
│ Overview             │                                │                      │
│ Clinical Summary     │ Vital-sign charts              │ Recommendations      │
│ Vitals & Labs        │ Laboratory trends              │ Risk notifications   │
│ Medications          │ Encounter timeline             │ Required actions     │
│ Problems             │ Nursing indicators             │ Acknowledgments      │
│ Care Plan            │                                │                      │
│ Notes                │                                │                      │
│ Documents            │                                │                      │
│ Flowsheets           │                                │                      │
└──────────────────────┴────────────────────────────────┴──────────────────────┘

Responsive Behavior

On smaller screens:

* The patient sidebar becomes collapsible.
* The primary menu becomes a mobile navigation panel.
* The secondary navigation becomes horizontally scrollable.
* Summary cards stack vertically.
* Charts and data tables use responsive overflow containers.
* Clinical alerts remain visible and prioritized.
* Important patient identifiers remain available in a compact header.

⸻

Project Structure

liberia_ehr/
├── README.md
├── manage.py
├── .env
├── .env.example
├── .gitignore
├── package.json
├── package-lock.json
├── tailwind.config.js
├── postcss.config.js
├── pytest.ini
├── docker-compose.yml
├── Dockerfile
│
├── requirements/
│   ├── base.txt
│   ├── development.txt
│   ├── production.txt
│   └── test.txt
│
├── config/
│   ├── __init__.py
│   ├── asgi.py
│   ├── urls.py
│   ├── wsgi.py
│   └── settings/
│       ├── __init__.py
│       ├── base.py
│       ├── development.py
│       ├── production.py
│       └── test.py
│
├── apps/
│   ├── __init__.py
│   ├── core/
│   ├── accounts/
│   ├── facilities/
│   ├── patients/
│   ├── encounters/
│   ├── nursing/
│   ├── vitals/
│   ├── diagnoses/
│   ├── allergies/
│   ├── medications/
│   ├── orders/
│   ├── laboratories/
│   ├── imaging/
│   ├── procedures/
│   ├── care_management/
│   ├── documents/
│   ├── flowsheets/
│   ├── appointments/
│   ├── analytics/
│   ├── decision_support/
│   ├── ai_assistant/
│   ├── audit/
│   ├── notifications/
│   └── integrations/
│
├── templates/
│   ├── base.html
│   ├── layouts/
│   │   ├── app_shell.html
│   │   ├── auth_layout.html
│   │   └── printable_layout.html
│   ├── components/
│   │   ├── primary_nav.html
│   │   ├── secondary_nav.html
│   │   ├── patient_sidebar.html
│   │   ├── patient_banner.html
│   │   ├── summary_card.html
│   │   ├── status_badge.html
│   │   ├── cds_alert.html
│   │   ├── modal.html
│   │   ├── toast.html
│   │   ├── pagination.html
│   │   └── loading_indicator.html
│   ├── includes/
│   │   ├── messages.html
│   │   ├── form_errors.html
│   │   └── scripts.html
│   ├── dashboard/
│   │   └── clinical_overview.html
│   ├── partials/
│   │   ├── navigation/
│   │   ├── patients/
│   │   ├── dashboard/
│   │   ├── nursing/
│   │   ├── orders/
│   │   └── decision_support/
│   ├── registration/
│   │   ├── login.html
│   │   ├── logged_out.html
│   │   ├── password_change_form.html
│   │   └── password_change_done.html
│   └── errors/
│       ├── 400.html
│       ├── 403.html
│       ├── 404.html
│       └── 500.html
│
├── static/
│   ├── src/
│   │   ├── css/
│   │   │   └── input.css
│   │   └── js/
│   │       └── app.js
│   └── dist/
│       ├── css/
│       │   └── output.css
│       └── js/
│           └── app.js
│
├── media/
│   ├── patient_photos/
│   ├── clinical_documents/
│   └── temporary/
│
├── tests/
│   ├── conftest.py
│   ├── factories/
│   ├── integration/
│   └── security/
│
├── scripts/
│   ├── create_initial_roles.py
│   ├── load_reference_data.py
│   └── backup_database.sh
│
├── docs/
│   ├── architecture/
│   ├── clinical-workflows/
│   ├── data-dictionary/
│   ├── deployment/
│   ├── security/
│   └── decision-support/
│
└── locale/

⸻

Template Architecture

Global templates belong in the root templates/ directory. Templates that are specific to a domain should remain inside the owning Django application.

liberia_ehr/
├── templates/
│   ├── base.html
│   ├── layouts/
│   ├── components/
│   ├── includes/
│   ├── partials/
│   ├── registration/
│   └── errors/
│
└── apps/
    ├── patients/
    │   └── templates/
    │       └── patients/
    │           ├── patient_list.html
    │           ├── patient_detail.html
    │           ├── patient_form.html
    │           ├── patient_confirm_delete.html
    │           └── partials/
    │               ├── patient_list.html
    │               ├── patient_form.html
    │               ├── patient_search_results.html
    │               ├── patient_sidebar.html
    │               ├── patient_summary.html
    │               └── child_form.html
    │
    ├── nursing/
    │   └── templates/
    │       └── nursing/
    │           ├── assessment_list.html
    │           ├── assessment_form.html
    │           ├── care_plan.html
    │           └── partials/
    │
    ├── vitals/
    │   └── templates/
    │       └── vitals/
    │           ├── vital_form.html
    │           ├── vital_history.html
    │           └── partials/
    │
    ├── analytics/
    │   └── templates/
    │       └── analytics/
    │           ├── clinical_dashboard.html
    │           ├── nursing_dashboard.html
    │           ├── facility_dashboard.html
    │           └── partials/
    │
    └── decision_support/
        └── templates/
            └── decision_support/
                ├── alert_list.html
                ├── alert_detail.html
                └── partials/

Template Rules

* Full pages extend a shared layout.
* HTMX endpoints return partial templates.
* Reusable UI elements belong in templates/components/.
* Domain-specific fragments remain inside the owning application.
* Partial templates should not unnecessarily repeat page-level markup.
* Clinical forms must display validation errors clearly.
* Destructive or high-risk actions must require deliberate confirmation.

⸻

Django Application Responsibilities

core

Provides system-wide functionality:

* Shared base models
* Dashboard routing
* Health checks
* Common context processors
* Shared constants
* Shared validators
* HTMX utilities
* Generic status types
* Common template helpers
* Application-level exception handling

accounts

Responsible for identity and workforce access:

* Authentication
* User profiles
* Staff records
* Professional credentials
* Staff roles
* Django groups and permissions
* Facility assignments
* Department assignments
* Password policies
* Session security
* Account activation and deactivation
* Login history

A custom Django user model should be created before the first production migration.

facilities

Represents the healthcare organization:

* Healthcare facilities
* Hospitals
* Clinics
* Departments
* Units
* Wards
* Rooms
* Beds
* Service locations
* Facility settings
* Facility-specific identifiers
* Facility-level data access

patients

Manages the patient identity domain:

* Registration
* Demographics
* Medical record numbers
* National and facility identifiers
* Contact information
* Addresses
* Emergency contacts
* Next of kin
* Patient photographs
* Patient search
* Duplicate review
* Merge review
* Patient status
* Archival

encounters

Manages episodes of care:

* Outpatient visits
* Emergency visits
* Inpatient admissions
* Transfers
* Discharges
* Encounter types
* Encounter status
* Care teams
* Clinical locations
* Encounter timelines
* Admission and discharge summaries

nursing

Supports nursing workflows:

* Nursing intake
* Nursing assessments
* Nursing notes
* Care plans
* Nursing diagnoses
* Patient goals
* Nursing interventions
* Shift handoff
* Intake and output
* Pain assessment
* Fall-risk assessment
* Pressure-injury risk
* Nursing task lists
* Escalation workflows

vitals

Handles physiological observations:

* Temperature
* Pulse
* Respiratory rate
* Blood pressure
* Oxygen saturation
* Height
* Weight
* Body mass index
* Blood glucose
* Level of consciousness
* Validation
* Abnormal flags
* Trend views
* Observation history

diagnoses

Manages clinical problems and diagnoses:

* Problem lists
* Encounter diagnoses
* Primary diagnoses
* Secondary diagnoses
* Diagnostic status
* Onset dates
* Resolution dates
* Coding-system integration
* Clinical comments

allergies

Manages:

* Drug allergies
* Food allergies
* Environmental allergies
* Intolerances
* Reaction types
* Severity
* Verification status
* Allergy reconciliation

medications

Manages:

* Medication catalog
* Medication reconciliation
* Prescriptions
* Medication orders
* Administration records
* Dose
* Route
* Frequency
* Duration
* Status
* Discontinuation
* Allergy checks
* Safety checks

orders

Coordinates:

* Laboratory orders
* Imaging orders
* Medication orders
* Procedure orders
* Nursing orders
* Order priority
* Order status
* Approval
* Cancellation
* Completion
* Lifecycle history

laboratories

Supports laboratory workflows:

* Test catalog
* Laboratory panels
* Specimens
* Collection
* Accession numbers
* Result entry
* Result verification
* Reference ranges
* Abnormal flags
* Critical-result workflows
* Result acknowledgment
* Turnaround-time analysis

imaging

Supports:

* Imaging orders
* Imaging procedures
* Radiology reports
* Report status
* Result review
* Uploaded images or external imaging references
* Critical finding acknowledgment

procedures

Supports:

* Procedure catalog
* Procedure documentation
* Consent status
* Procedure status
* Clinical personnel
* Complications
* Post-procedure notes

care_management

Supports multidisciplinary coordination:

* Care plans
* Referrals
* Follow-up tasks
* Discharge planning
* Social needs
* Patient education
* Care-team communication
* Case-management notes

documents

Supports:

* Clinical document uploads
* Document categories
* Patient-document association
* Encounter-document association
* Version metadata
* Secure file access
* Document audit trails

flowsheets

Supports structured repeated documentation:

* Vital-sign flowsheets
* Intake and output
* Neurological checks
* Nursing observations
* Pain assessments
* Configurable rows and columns
* Time-series display

appointments

Supports:

* Appointment scheduling
* Appointment status
* Assigned provider
* Facility and department
* Reminder status
* Check-in
* Cancellation
* Missed appointments

analytics

Provides:

* Clinical dashboards
* Nursing dashboards
* Operational dashboards
* Quality measures
* Public-health indicators
* Surveillance reports
* Data extracts
* Time-range comparisons
* Drill-down analysis
* Data-quality monitoring

decision_support

Provides rule-based clinical support:

* Clinical rule definitions
* Rule versions
* Alert generation
* Contraindication checks
* Deterioration detection
* Abnormal-result interpretation
* Recommendation review
* Alert acknowledgment
* Override reasons
* Rule performance monitoring

ai_assistant

Provides future governed AI capabilities:

* Clinical summarization
* Natural-language patient-record search
* Documentation assistance
* Risk prediction
* Coding assistance
* Explainable recommendations
* Model-service integration
* Prompt and output tracking
* Human review workflows

AI output must remain reviewable, attributable, and subordinate to clinician judgment.

audit

Records:

* Authentication activity
* Patient-record access
* Record creation
* Record modification
* Record archival
* Data exports
* Printed records
* Decision-support acknowledgments
* Override actions
* Administrative changes
* Failed access attempts

notifications

Supports:

* In-application notifications
* Clinical reminders
* Task reminders
* Alert escalation
* Email integration
* SMS integration
* Delivery status
* Notification preferences

integrations

Provides controlled interfaces for:

* External APIs
* Laboratory systems
* Pharmacy systems
* Messaging providers
* National health systems
* Interoperability standards
* Data import and export

⸻

Recommended Internal App Pattern

Larger domain applications should use a predictable structure.

apps/patients/
├── __init__.py
├── admin.py
├── apps.py
├── urls.py
├── models/
│   ├── __init__.py
│   ├── patient.py
│   ├── identifier.py
│   ├── contact.py
│   └── relationship.py
├── forms/
│   ├── __init__.py
│   ├── patient.py
│   ├── contact.py
│   └── search.py
├── selectors/
│   ├── __init__.py
│   ├── patients.py
│   └── search.py
├── services/
│   ├── __init__.py
│   ├── registration.py
│   ├── update.py
│   └── merge.py
├── permissions.py
├── validators.py
├── constants.py
├── views/
│   ├── __init__.py
│   ├── pages.py
│   └── partials.py
├── templates/
│   └── patients/
├── migrations/
└── tests/
    ├── test_models.py
    ├── test_forms.py
    ├── test_services.py
    ├── test_permissions.py
    └── test_views.py

Module Responsibilities

* models/: Database entities and model-level invariants
* forms/: Input validation and presentation-aware form behavior
* selectors/: Read-only queries and retrieval logic
* services/: Write operations and business workflows
* permissions.py: Role-based and object-level authorization
* validators.py: Reusable domain validation
* constants.py: Domain constants and choices
* views/pages.py: Full-page responses
* views/partials.py: HTMX fragment responses
* tests/: Unit, integration, and permission tests

Views should remain thin. Complex business workflows should be implemented in services.

⸻

Database Strategy

The database engine is selected through environment variables.

Development with SQLite

DJANGO_SETTINGS_MODULE=config.settings.development
DATABASE_ENGINE=sqlite
SQLITE_NAME=db.sqlite3

Production with PostgreSQL

DJANGO_SETTINGS_MODULE=config.settings.production
DATABASE_ENGINE=postgres
POSTGRES_DB=liberia_ehr
POSTGRES_USER=liberia_ehr
POSTGRES_PASSWORD=replace-with-a-secure-password
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_CONN_MAX_AGE=60

Recommended Database Practices

* Use UUIDs for externally exposed identifiers where appropriate.
* Keep facility-specific MRNs separate from internal database keys.
* Use database constraints for critical invariants.
* Use transactions for multi-record clinical workflows.
* Use PROTECT where deletion would damage historical integrity.
* Use archival or status changes instead of deleting clinical records.
* Record the user and timestamp associated with important changes.
* Add indexes for common patient-search fields.
* Use PostgreSQL trigram search for tolerant patient-name matching.
* Use full-text search only after core data quality is established.
* Test backup restoration regularly.

Recommended Base Model Fields

Many clinical models should inherit common fields such as:

id
created_at
updated_at
created_by
updated_by
is_active
facility

Clinical records may additionally require:

status
recorded_at
recorded_by
verified_at
verified_by
voided_at
voided_by
void_reason

⸻

HTMX Strategy

HTMX should be used for server-owned clinical state and partial page updates.

Recommended HTMX Use Cases

* Patient search suggestions
* Patient-list filtering
* Loading a selected patient into the sidebar
* Replacing secondary navigation
* Loading patient overview panels
* Filtering observations by time range
* Opening forms in a modal
* Saving clinical forms without full-page reloads
* Updating summary cards after documentation
* Acknowledging decision-support alerts
* Paginating tables
* Loading chart data
* Validating order forms
* Updating care-plan tasks
* Refreshing patient timelines

Patient Search Example

<input
    type="search"
    name="q"
    placeholder="Search by name, MRN, date of birth, or phone..."
    hx-get="{% url 'patients:search-results' %}"
    hx-trigger="input changed delay:350ms, search"
    hx-target="#patient-search-results"
    hx-indicator="#patient-search-spinner"
    hx-include="[name='facility']"
    autocomplete="off"
>

Workspace Navigation Example

<a
    href="{% url 'patients:overview' patient.id %}"
    hx-get="{% url 'patients:overview' patient.id %}"
    hx-target="#workspace"
    hx-push-url="true"
    hx-indicator="#workspace-loading"
>
    Overview
</a>

Clinical Form Example

<form
    method="post"
    hx-post="{% url 'vitals:create' patient.id %}"
    hx-target="#vitals-panel"
    hx-swap="innerHTML"
>
    {% csrf_token %}
    {{ form.as_div }}
    <button type="submit">
        Save vital signs
    </button>
</form>

HTMX Response Rules

* Return full pages for ordinary browser navigation.
* Return partials when request.htmx is true.
* Validate permissions for every HTMX endpoint.
* Do not rely on hidden buttons as authorization.
* Return clear validation errors.
* Use HTTP status codes consistently.
* Avoid returning sensitive data outside the selected patient context.
* Refresh dependent panels after successful writes.
* Use hx-push-url only when browser history should reflect the state.
* Provide loading indicators for slower operations.

⸻

Alpine.js Responsibilities

Alpine.js is intended for lightweight presentation behavior.

Recommended uses include:

* Mobile navigation
* Dropdown menus
* Sidebar collapse
* Temporary tabs
* Modal visibility
* Dismissible alerts
* Menu expansion
* Tooltips
* Non-clinical display preferences
* Local chart-control visibility

Do not keep authoritative clinical information only in Alpine.js state.

Clinical data must be validated, persisted, and reloaded from Django.

⸻

Tailwind CSS Design System

Liberia EHR uses Tailwind CSS for all primary styling.

Standalone custom CSS should be minimized and reserved for cases that Tailwind utilities or components cannot reasonably address.

Visual Direction

The analytics-focused interface uses:

* Deep teal primary navigation
* Slightly lighter teal patient sidebar
* White workspace panels
* Slate application background
* Emerald success indicators
* Amber warning indicators
* Red critical alerts
* Blue actions and chart accents
* High-contrast text for clinical readability

Suggested Tailwind Color Tokens

// tailwind.config.js
module.exports = {
  content: [
    "./templates/**/*.html",
    "./apps/**/templates/**/*.html",
    "./static/src/js/**/*.js",
  ],
  theme: {
    extend: {
      colors: {
        ehr: {
          50: "#effcfb",
          100: "#d5f6f2",
          200: "#acece5",
          300: "#75d9d0",
          400: "#3abeb4",
          500: "#0f9f8f",
          600: "#0b8378",
          700: "#087368",
          800: "#075d57",
          900: "#064b47",
          950: "#033c3a",
        },
      },
      boxShadow: {
        panel: "0 1px 3px rgba(15, 23, 42, 0.08)",
      },
    },
  },
  plugins: [
    require("@tailwindcss/forms"),
    require("@tailwindcss/typography"),
  ],
};

Accessibility Expectations

* Maintain adequate color contrast.
* Do not communicate severity through color alone.
* Use visible focus styles.
* Provide labels for every form field.
* Ensure keyboard access to menus and dialogs.
* Provide text alternatives for meaningful images.
* Use semantic HTML.
* Mark invalid fields with accessible error messages.
* Avoid small text for essential clinical information.
* Make critical alerts understandable without icons.

⸻

Clinical Decision Support

Clinical decision support should begin with transparent, deterministic rules.

Initial Rule Categories

* Abnormal vital signs
* Critical laboratory values
* Medication allergies
* Duplicate medication therapy
* Drug contraindications
* Fall-risk reminders
* Sepsis screening
* Patient deterioration
* Required follow-up
* Missing documentation
* Age-specific safety checks

Minimum Rule Metadata

Each rule should include:

* Rule name
* Rule identifier
* Rule version
* Clinical purpose
* Trigger conditions
* Exclusion conditions
* Severity
* Recommendation
* Evidence or policy source
* Effective date
* Expiration or review date
* Owning clinical group
* Activation status

Alert Lifecycle

Trigger detected
      │
      ▼
Alert created
      │
      ▼
Displayed to authorized clinician
      │
      ├── Acknowledged
      ├── Action completed
      ├── Overridden with reason
      └── Escalated

Every acknowledgment, override, and action should be auditable.

⸻

Artificial Intelligence Governance

AI functions must be introduced only after the underlying clinical records and workflows are stable.

Potential AI Capabilities

* Clinical note summarization
* Patient timeline summarization
* Natural-language record search
* Documentation assistance
* Risk prediction
* Coding suggestions
* Missing-information detection
* Patient-education drafts
* Public-health pattern identification

AI Safety Requirements

* AI output must be clearly labeled.
* AI output must not silently modify the clinical record.
* A clinician must review clinical recommendations.
* Model name and version must be recorded.
* Source data used for an output must be traceable.
* Confidence and limitations should be displayed where meaningful.
* Unsupported conclusions must be avoided.
* Protected health information must not be sent to unapproved services.
* AI actions must follow facility-level authorization.
* AI output and clinician action should be auditable.
* Models must be assessed for bias and population suitability.
* Clinical staff must be able to reject or correct an output.

AI must assist clinical judgment, not replace it.

⸻

Analytics and Nursing Informatics

Analytics should be built from validated operational and clinical records rather than independent duplicate data entry.

Clinical Analytics

* Patient census
* Admissions and discharges
* Diagnosis patterns
* Abnormal vital-sign trends
* Medication utilization
* Laboratory result trends
* Readmissions
* Length of stay
* Care-plan completion
* Referral completion

Nursing Informatics

* Nursing documentation completion
* Assessment timeliness
* Care-plan compliance
* Fall-risk documentation
* Pressure-injury risk
* Medication-administration timeliness
* Nursing workload
* Patient acuity
* Shift handoff completion
* Escalation patterns

Operational Analytics

* Facility patient volume
* Department volume
* Appointment completion
* Wait times
* Bed occupancy
* Laboratory turnaround time
* Staff workload
* Supply utilization
* Alert-response time

Public-Health Analytics

* Disease trends
* Geographic distribution
* Maternal and child-health indicators
* Communicable-disease surveillance
* Vaccination activity
* Outbreak signals
* Facility reporting completeness

Analytics Principles

* Define every metric clearly.
* Display the reporting period.
* Document inclusion and exclusion rules.
* Separate preliminary and verified data.
* Show missing-data rates.
* Restrict access to identifiable information.
* Prefer aggregated data where individual records are unnecessary.
* Record report-generation and export activity.

⸻

Security and Clinical Safety

Before production deployment, the project must implement and validate:

* Role-based authorization
* Object-level authorization
* Facility-level data separation
* Department-level access where appropriate
* Secure password policies
* Multi-factor authentication for privileged users
* HTTPS
* CSRF protection
* Secure cookies
* Content Security Policy
* Session expiration
* Automatic screen locking
* Rate limiting
* Login-attempt monitoring
* Sensitive-data masking
* Audit logging
* Encrypted backups
* Tested restoration procedures
* Database encryption strategy
* Secure file storage
* Data-retention policies
* Clinical alert governance
* AI and CDS version tracking
* Clinician acknowledgment
* Override-reason documentation
* Downtime workflows
* Incident-response procedures
* Disaster-recovery procedures

Clinical Record Integrity

Clinical information should not normally be hard-deleted.

Corrections should use:

* Amendments
* Addenda
* Status changes
* Void workflows
* Correction reasons
* Recorded user identity
* Original and corrected timestamps

Facility Separation

Every patient, encounter, order, result, and clinical record should be associated with the appropriate facility or organization context.

Authorization must verify that the signed-in user is permitted to access that facility and patient.

⸻

Audit Logging

Audit logging is a core clinical requirement, not an optional administrative feature.

Events to Audit

* Successful login
* Failed login
* Logout
* Password change
* Patient search
* Patient-record access
* Record creation
* Record update
* Record voiding
* Record archival
* Document download
* Record printing
* Data export
* Permission change
* User activation or deactivation
* CDS acknowledgment
* CDS override
* AI request and response metadata
* Administrative configuration changes

Suggested Audit Fields

id
event_type
event_timestamp
user
facility
patient
encounter
object_type
object_identifier
request_method
request_path
ip_address
user_agent
success
reason
metadata

Audit records should be immutable to ordinary users.

⸻

Local Development Setup

Prerequisites

Install:

* Python 3.12 or later
* Node.js 20 or later
* npm
* Git
* PostgreSQL for production-like development
* A Python virtual-environment tool

1. Clone the Repository

git clone https://github.com/YOUR-GITHUB-USERNAME/liberia-ehr.git
cd liberia-ehr

Replace YOUR-GITHUB-USERNAME with the GitHub account that owns the repository.

2. Create a Virtual Environment

macOS and Linux:

python3 -m venv .venv
source .venv/bin/activate

Windows PowerShell:

python -m venv .venv
.venv\Scripts\Activate.ps1

3. Upgrade Python Packaging Tools

python -m pip install --upgrade pip setuptools wheel

4. Install Python Dependencies

pip install -r requirements/development.txt

5. Install Frontend Dependencies

npm install

6. Create the Environment File

macOS and Linux:

cp .env.example .env

Windows PowerShell:

Copy-Item .env.example .env

7. Configure Development Environment Variables

Example .env:

DJANGO_SETTINGS_MODULE=config.settings.development
DJANGO_SECRET_KEY=replace-this-with-a-development-secret
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=127.0.0.1,localhost
DATABASE_ENGINE=sqlite
SQLITE_NAME=db.sqlite3
DEFAULT_FROM_EMAIL=noreply@example.com
SESSION_COOKIE_SECURE=False
CSRF_COOKIE_SECURE=False

Do not commit .env to Git.

8. Run Django System Checks

python manage.py check

9. Create and Apply Migrations

python manage.py makemigrations
python manage.py migrate

10. Create an Administrator

python manage.py createsuperuser

11. Load Initial Roles and Reference Data

When the scripts are available:

python manage.py setup_roles
python manage.py load_reference_data

12. Compile Tailwind CSS

Development watch mode:

npm run dev

Production build:

npm run build

13. Start Django

In a separate terminal with the virtual environment activated:

python manage.py runserver

Open:

http://127.0.0.1:8000/

14. Access Django Administration

http://127.0.0.1:8000/admin/

⸻

PostgreSQL Setup

Create a PostgreSQL database and user.

CREATE DATABASE liberia_ehr;
CREATE USER liberia_ehr WITH PASSWORD 'replace-with-a-secure-password';
GRANT ALL PRIVILEGES ON DATABASE liberia_ehr TO liberia_ehr;

Configure .env:

DATABASE_ENGINE=postgres
POSTGRES_DB=liberia_ehr
POSTGRES_USER=liberia_ehr
POSTGRES_PASSWORD=replace-with-a-secure-password
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_CONN_MAX_AGE=60

Apply migrations:

python manage.py migrate

Verify the connection:

python manage.py check --database default

⸻

Docker Setup

A future production-style local environment may include:

* Django
* PostgreSQL
* Redis
* Celery worker
* Nginx

Start the services:

docker compose up --build

Run migrations:

docker compose exec web python manage.py migrate

Create an administrator:

docker compose exec web python manage.py createsuperuser

Stop the services:

docker compose down

Remove containers and development volumes only when intentionally resetting the environment:

docker compose down --volumes

⸻

Testing

Run the complete test suite:

pytest

Run tests for one application:

pytest apps/patients/tests/

Run one test module:

pytest apps/patients/tests/test_services.py

Run tests with coverage:

pytest --cov=apps --cov-report=term-missing

Generate an HTML coverage report:

pytest --cov=apps --cov-report=html

Required Test Categories

* Model tests
* Form-validation tests
* Service tests
* Selector tests
* Permission tests
* View tests
* HTMX response tests
* Audit-log tests
* Clinical-rule tests
* Facility-separation tests
* Authentication tests
* Integration tests
* Security regression tests

High-Risk Workflows Requiring Strong Coverage

* Patient registration
* Duplicate-patient detection
* Patient merge
* Medication ordering
* Allergy checking
* Medication administration
* Critical laboratory results
* Admission, transfer, and discharge
* Clinical-record corrections
* Decision-support overrides
* User permission changes
* Data exports

⸻

Development Standards

Python

* Follow PEP 8.
* Use descriptive names.
* Add type hints where they improve clarity.
* Keep views thin.
* Keep business logic in service functions.
* Keep complex reads in selectors.
* Use transactions for multi-step writes.
* Avoid signals for complex clinical workflows.
* Document safety-critical logic.
* Validate at both form and domain levels where appropriate.

Django

* Use named URLs.
* Use application namespaces.
* Use select_related() and prefetch_related() deliberately.
* Use database constraints for important invariants.
* Avoid hard-coded role names throughout views.
* Centralize permission checks.
* Use custom managers or selectors for reusable queries.
* Avoid destructive cascading deletion of clinical records.
* Use timezone-aware datetimes.

Templates

* Use Tailwind CSS classes.
* Keep reusable patterns in components.
* Use partial templates for HTMX responses.
* Display validation errors near the affected fields.
* Keep patient identity visible during documentation.
* Show loading and success states.
* Do not hide safety-critical information behind hover-only UI.

JavaScript

* Prefer HTMX for server interactions.
* Prefer Alpine.js for small presentation states.
* Avoid duplicating authoritative Django state in the browser.
* Keep JavaScript modules small.
* Avoid adding a large frontend framework without a demonstrated need.

Git

Use small, focused commits.

Suggested branch names:

feature/patient-registration
feature/patient-search
feature/vital-sign-entry
fix/login-redirect
fix/facility-permissions
refactor/patient-services
docs/update-readme

Suggested commit format:

feat: add HTMX patient search
fix: enforce facility access in patient detail
refactor: move registration workflow into service
test: add patient permission coverage
docs: expand local setup instructions

⸻

Suggested Implementation Order

Phase 1: Foundation

1. Django project configuration
2. Environment-based settings
3. Custom user model
4. Authentication
5. Tailwind CSS integration
6. HTMX integration
7. Alpine.js integration
8. Shared application shell
9. Error templates
10. Basic audit infrastructure

Phase 2: Organization and Access

1. Facilities
2. Departments
3. Units and wards
4. Staff profiles
5. Roles and groups
6. Facility assignments
7. Permission framework
8. Session security

Phase 3: Patient Identity

1. Patient registration
2. Medical record numbers
3. Patient identifiers
4. Contacts and addresses
5. Emergency contacts
6. HTMX patient search
7. Duplicate detection
8. Patient context sidebar
9. Patient audit logging

Phase 4: Encounters and Nursing

1. Outpatient encounters
2. Admissions
3. Transfers
4. Discharges
5. Vital-sign entry
6. Nursing assessments
7. Nursing notes
8. Care plans
9. Intake and output
10. Flowsheets

Phase 5: Core Clinical Workflows

1. Diagnoses
2. Allergies
3. Medications
4. Orders
5. Laboratory results
6. Imaging reports
7. Procedures
8. Clinical documents

Phase 6: Analytics and Safety

1. Clinical overview dashboard
2. Nursing dashboard
3. Operational dashboard
4. Audit reporting
5. Rule-based clinical alerts
6. Alert acknowledgment
7. Override workflow
8. Data-quality indicators

Phase 7: Advanced Capabilities

1. Public-health analytics
2. Interoperability
3. Notifications
4. Background processing
5. Governed AI services
6. Explainable risk models
7. Natural-language search
8. Documentation assistance

⸻

Initial Milestone

The first functional milestone should support:

* Staff login and logout
* Secure authenticated application shell
* Facility and department assignment
* Patient registration
* HTMX patient search
* Patient-list filtering
* Patient selection
* Persistent patient context sidebar
* Patient overview dashboard
* Encounter creation
* Vital-sign entry
* Recent vital-sign history
* Vital-sign trend display
* Allergy display
* Problem-list display
* Basic rule-based abnormal-vital alert
* Alert acknowledgment
* Audit record for patient access
* Audit record for clinical documentation

Initial Milestone Workflow

Staff login
    │
    ▼
Patient search or registration
    │
    ▼
Patient selection
    │
    ▼
Patient context sidebar loaded
    │
    ▼
Encounter selected or created
    │
    ▼
Vital signs documented
    │
    ▼
Clinical rule evaluated
    │
    ├── No alert
    │
    └── Alert displayed and acknowledged
    │
    ▼
Patient overview and audit trail updated

⸻

Future Roadmap

Near-Term

* Complete patient registration
* Improve HTMX patient search
* Add facility-scoped permissions
* Build persistent patient sidebar
* Add encounter lifecycle
* Add vital-sign entry and history
* Add nursing documentation
* Add audit logging

Medium-Term

* Medication reconciliation
* Medication administration record
* Laboratory ordering and results
* Imaging reports
* Structured nursing flowsheets
* Care-management workflows
* Facility dashboards
* Data-quality dashboards
* Notification system

Long-Term

* Inter-facility patient exchange
* National patient identifiers
* FHIR-compatible APIs
* Offline-tolerant workflows
* Public-health reporting
* Disease-surveillance tools
* Mobile-friendly clinical workflows
* SMS appointment reminders
* Governed AI summarization
* Explainable clinical-risk models
* Natural-language clinical search
* Integration with national health systems

⸻

Contributing

Contributions should preserve the project’s clinical-safety, privacy, and maintainability principles.

Before submitting code:

1. Create a focused branch.
2. Follow the application architecture.
3. Add or update tests.
4. Run Django system checks.
5. Run the test suite.
6. Compile Tailwind successfully.
7. Document new environment variables.
8. Document new clinical rules.
9. Confirm facility and role permissions.
10. Avoid including real patient information.

Example workflow:

git checkout -b feature/vital-sign-entry
git add .
git commit -m "feat: add vital-sign entry workflow"
git push origin feature/vital-sign-entry

Never commit:

* Real patient records
* Passwords
* Secret keys
* API tokens
* Production database exports
* Unencrypted backups
* Protected health information
* Private encryption keys
* .env files

⸻

License

A license should be selected before public production distribution.

Potential options include:

* MIT License
* Apache License 2.0
* GNU Affero General Public License
* A custom healthcare deployment license

The selected license should account for:

* Source-code use
* Commercial deployment
* Modification and redistribution
* Clinical liability
* Data ownership
* Third-party integrations
* Contributions
* AI and model components

Until a license is added, all rights remain reserved by the project owner.

⸻

Clinical Disclaimer

Liberia EHR is currently a software-development project.

It is not yet:

* A certified medical device
* A replacement for professional clinical judgment
* A substitute for emergency medical care
* Approved for storing real patient data
* Validated for production clinical deployment
* Guaranteed to meet every legal or regulatory requirement

Clinical decision-support and AI outputs must be reviewed by qualified healthcare professionals.

Before real-world deployment, the system must undergo:

* Clinical workflow validation
* Security assessment
* Privacy assessment
* Performance testing
* Backup and recovery testing
* Data-quality validation
* User-acceptance testing
* Accessibility review
* Clinical-risk assessment
* Legal and regulatory review
* Staff training
* Controlled pilot implementation

⸻

Project Summary

Liberia EHR combines:

* Django’s secure server-side framework
* HTMX-powered clinical interactions
* Alpine.js for lightweight presentation behavior
* Tailwind CSS for a consistent professional interface
* PostgreSQL for production data management
* Nursing informatics
* Healthcare analytics
* Rule-based clinical decision support
* Carefully governed AI integration

The project’s purpose is to create a practical, modular, and safety-conscious EHR foundation that can grow alongside the needs of healthcare facilities in Liberia.
