# Liberia EHR

A professional, analytics-enabled Electronic Health Record platform designed for:

- Clinical care and patient documentation
- Nursing informatics
- Healthcare data analytics
- AI-assisted clinical decision support
- Resource-limited healthcare environments, including Liberia

The interface follows **Design Option 2: Professional Dashboard**.

## Technology Stack

| Layer | Technology |
|---|---|
| Backend | Django |
| Dynamic server-rendered UI | HTMX |
| Lightweight browser interaction | Alpine.js |
| Styling | Tailwind CSS |
| Production database | PostgreSQL |
| Development/test database | SQLite |
| Analytics foundation | Python/Django services |
| AI/CDS foundation | Rule engine and model-service adapters |

SQLite is used for local development and testing. PostgreSQL is the recommended production database.

---

## Design Option 2 Layout

The application shell contains four persistent areas:

1. **Primary navigation**
   - Clinical
   - Nursing
   - Analytics
   - AI / CDS
   - Orders
   - Medication
   - Care Management
   - Administration

2. **Contextual secondary navigation**
   - Changes according to the active primary module.
   - Under Clinical > Patients, it contains patient search, patient list, recent patients, admission, transfer, discharge, alerts, and additional actions.

3. **Patient context sidebar**
   - Patient photo or initials
   - Name and medical record number
   - Date of birth, age, and sex
   - Overview
   - Clinical summary
   - Vitals and labs
   - Medications
   - Problems
   - Care plan
   - Notes
   - Documents
   - Flowsheets

4. **Professional dashboard workspace**
   - Clinical overview heading and time-range control
   - Summary cards
   - Clinical trend charts
   - AI clinical decision-support recommendations
   - Risk alerts
   - HTMX-powered forms, tables, timelines, and detail panels

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│ Clinical | Nursing | Analytics | AI/CDS | Orders | Medication | Admin       │
├──────────────────────────────────────────────────────────────────────────────┤
│ Patients | Search | Patient List | Recent | Admit | Transfer | Discharge    │
├──────────────────────┬───────────────────────────────────────────────────────┤
│ Patient Context      │ Clinical Overview                     Last 24 Hours   │
│                      ├───────────────────────────────────────────────────────┤
│ Identity             │ Vitals | Labs | Medications | I/O | Pain             │
│ Overview             ├───────────────────────────────┬───────────────────────┤
│ Clinical Summary     │ Clinical Trends               │ AI/CDS Alerts         │
│ Vitals & Labs        │                               │ Recommendations       │
│ Medications          │                               │ Risk notifications    │
│ Problems             │                               │                       │
│ Care Plan            │                               │                       │
│ Notes                │                               │                       │
└──────────────────────┴───────────────────────────────┴───────────────────────┘
```

---

## Project Structure

```text
liberia_ehr/
├── README.md
├── manage.py
├── .env.example
├── .gitignore
├── package.json
├── tailwind.config.js
├── postcss.config.js
├── pytest.ini
├── docker-compose.yml
├── requirements/
│   ├── base.txt
│   ├── development.txt
│   └── production.txt
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
├── apps/
│   ├── core/
│   ├── accounts/
│   ├── facilities/
│   ├── patients/
│   ├── encounters/
│   ├── nursing/
│   ├── vitals/
│   ├── diagnoses/
│   ├── medications/
│   ├── orders/
│   ├── laboratories/
│   ├── imaging/
│   ├── care_management/
│   ├── documents/
│   ├── flowsheets/
│   ├── analytics/
│   ├── decision_support/
│   ├── ai_assistant/
│   ├── audit/
│   └── notifications/
├── templates/
│   ├── base.html
│   ├── layouts/
│   │   └── app_shell.html
│   ├── components/
│   │   ├── primary_nav.html
│   │   ├── secondary_nav.html
│   │   ├── patient_sidebar.html
│   │   ├── summary_card.html
│   │   ├── cds_alert.html
│   │   └── loading_indicator.html
│   ├── dashboard/
│   │   └── clinical_overview.html
│   └── partials/
│       ├── navigation/
│       ├── patients/
│       ├── dashboard/
│       └── decision_support/
├── static/
│   ├── src/
│   │   ├── css/input.css
│   │   └── js/app.js
│   └── dist/
│       ├── css/
│       └── js/
├── tests/
├── scripts/
└── docs/
```

## Template structures

liberia_ehr/
├── templates/
│   ├── base.html
│   ├── layouts/
│   ├── components/
│   ├── includes/
│   ├── errors/
│   └── registration/
│
└── apps/
    ├── patients/
    │   └── templates/
    │       └── patients/
    │           ├── patient_list.html
    │           ├── patient_detail.html
    │           ├── patient_form.html
    │           └── partials/
    │
    ├── nursing/
    │   └── templates/
    │       └── nursing/
    │
    ├── vitals/
    │   └── templates/
    │       └── vitals/
    │
    ├── analytics/
    │   └── templates/
    │       └── analytics/
    │
    └── decision_support/
        └── templates/
            └── decision_support/

---

## Django Application Responsibilities

### `core`
Shared utilities, dashboard routing, base models, health checks, HTMX helpers, and common template context.

### `accounts`
Authentication, user profiles, staff roles, permissions, facility assignment, and session security.

Suggested roles:

- System administrator
- Facility administrator
- Physician
- Nurse practitioner
- Registered nurse
- Pharmacist
- Laboratory staff
- Radiology staff
- Medical records officer
- Care manager
- Data analyst
- Auditor

### `patients`
Patient registration, identifiers, demographics, contacts, emergency contacts, search, merge review, and patient status.

### `encounters`
Outpatient visits, emergency visits, admissions, transfers, discharges, encounter timelines, and care teams.

### `nursing`
Nursing assessments, care plans, notes, handoff, intake/output, pain assessment, fall-risk assessment, and nursing task lists.

### `vitals`
Vital-sign capture, validation, abnormal flags, trends, and observation history.

### `medications`
Medication catalog, reconciliation, prescriptions, administration records, allergies, reactions, and safety checks.

### `orders`
Laboratory, imaging, medication, procedure, and nursing orders with lifecycle tracking.

### `laboratories`
Test catalog, specimens, results, reference ranges, verification, abnormal flags, and critical-result workflows.

### `care_management`
Patient care plans, referrals, follow-up tasks, discharge planning, and multidisciplinary coordination.

### `flowsheets`
Structured repeated clinical documentation such as vitals, intake/output, neurological checks, and nursing observations.

### `analytics`
Clinical, operational, quality, surveillance, and nursing-informatics dashboards.

### `decision_support`
Rule-based clinical alerts, contraindication checks, abnormal-result interpretation, deterioration alerts, recommendation review, and override documentation.

### `ai_assistant`
Future AI functions such as clinical summarization, natural-language search, risk prediction, documentation assistance, and explainable model outputs.

AI output must remain reviewable, attributable, and subordinate to clinician judgment.

### `audit`
Patient-record access logs, authentication activity, exports, changes, CDS acknowledgments, and administrative actions.

---

## Recommended Internal App Pattern

Each larger domain app should use a predictable structure:

```text
apps/patients/
├── __init__.py
├── admin.py
├── apps.py
├── urls.py
├── models.py
├── forms.py
├── selectors.py
├── services.py
├── permissions.py
├── validators.py
├── views/
│   ├── __init__.py
│   ├── pages.py
│   └── partials.py
├── migrations/
└── tests/
```

- `models.py`: database entities and invariants
- `forms.py`: Django forms and validation
- `selectors.py`: read/query operations
- `services.py`: write operations and workflows
- `permissions.py`: role and object authorization
- `views/pages.py`: full-page responses
- `views/partials.py`: HTMX fragment responses

---

## Database Configuration

The database engine is selected through environment variables.

### Development with SQLite

```env
DJANGO_SETTINGS_MODULE=config.settings.development
DATABASE_ENGINE=sqlite
SQLITE_NAME=db.sqlite3
```

### Production with PostgreSQL

```env
DJANGO_SETTINGS_MODULE=config.settings.production
DATABASE_ENGINE=postgres
POSTGRES_DB=liberia_ehr
POSTGRES_USER=liberia_ehr
POSTGRES_PASSWORD=change-me
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
```

The settings module automatically switches between SQLite and PostgreSQL.

---

## HTMX Interaction Strategy

HTMX should be used for server-owned clinical state.

Recommended use cases:

- Patient search suggestions
- Loading a selected patient into the sidebar
- Replacing the secondary navigation
- Filtering observations by time range
- Opening clinical forms in a modal
- Saving notes without full-page reloads
- Updating summary cards after documentation
- Acknowledging decision-support alerts
- Paginating tables
- Loading chart data
- Validating order forms

Example patient search:

```html
<input
    type="search"
    name="q"
    placeholder="Search patients by name, MRN, DOB..."
    hx-get="{% url 'patients:search-results' %}"
    hx-trigger="input changed delay:350ms, search"
    hx-target="#patient-search-results"
    hx-indicator="#patient-search-spinner"
    autocomplete="off"
>
```

Example workspace navigation:

```html
<a
    href="{% url 'patients:overview' patient.id %}"
    hx-get="{% url 'patients:overview' patient.id %}"
    hx-target="#workspace"
    hx-push-url="true"
>
    Overview
</a>
```

---

## Alpine.js Responsibilities

Alpine.js is intended only for lightweight browser-side state:

- Mobile navigation
- Dropdown menus
- Sidebar collapse
- Temporary tabs
- Modal visibility
- Dismissible alerts
- Menu expansion
- Non-clinical presentation state

Do not keep authoritative clinical data only in Alpine.js state.

---

## Tailwind Design Tokens

The professional dashboard uses:

- Deep teal primary navigation
- Slightly lighter teal patient sidebar
- White cards and workspace panels
- Slate page background
- Emerald clinical-success accents
- Amber warning accents
- Red critical-alert accents
- Blue action and chart accents

The starter Tailwind configuration provides semantic colors:

```javascript
ehr: {
  50:  "#effcfb",
  100: "#d5f6f2",
  500: "#0f9f8f",
  700: "#087368",
  800: "#075d57",
  900: "#064b47",
  950: "#033c3a"
}
```

---

## Security and Clinical Safety

Before production use, implement and validate:

- Role-based and object-level authorization
- Facility-level data separation
- Secure password and session policies
- HTTPS
- CSRF protection
- Audit logging
- Automatic session timeout
- Sensitive-data masking
- Backups and tested restoration
- Database encryption strategy
- Clinical alert governance
- AI/CDS version tracking
- Clinician acknowledgment and override reasons
- Downtime and data-recovery procedures

This scaffold is a software foundation and is not, by itself, a certified medical device or production-ready clinical system.

---

## Local Setup

### 1. Create a virtual environment

```bash
python -m venv .venv
source .venv/bin/activate
```

Windows:

```powershell
.venv\Scripts\activate
```

### 2. Install Python packages

```bash
pip install -r requirements/development.txt
```

### 3. Install frontend packages

```bash
npm install
```

### 4. Create environment file

```bash
cp .env.example .env
```

### 5. Run migrations

```bash
python manage.py migrate
```

### 6. Create an administrator

```bash
python manage.py createsuperuser
```

### 7. Compile Tailwind

```bash
npm run dev
```

### 8. Start Django

```bash
python manage.py runserver
```

Open:

```text
http://127.0.0.1:8000/
```

---

## Suggested Implementation Order

1. Core configuration and authentication
2. Facilities, departments, and user roles
3. Patient registration and patient search
4. Encounter lifecycle
5. Patient context sidebar
6. Vitals and nursing documentation
7. Diagnoses and medications
8. Orders and laboratory workflows
9. Clinical overview dashboard
10. Audit logging
11. Rule-based decision support
12. Analytics
13. Carefully governed AI features

---

## Initial Milestone

The first functional milestone should support:

- Staff login
- Patient registration
- HTMX patient search
- Patient selection
- Persistent patient sidebar
- Patient overview dashboard
- Vital-sign entry
- Recent vital-sign trends
- Allergy and problem display
- Basic rule-based alert
- Audit record for patient access
