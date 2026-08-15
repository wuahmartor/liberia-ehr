# Liberia EHR

Liberia EHR is a modular, server-rendered electronic health record under active development. It combines longitudinal patient records, encounter-based clinical workflows, nursing documentation, medication ordering and administration, pharmacy operations, scheduling, and operational analytics in a compact Django interface.

> [!WARNING]
> This project is not certified or validated for production clinical use. Do not load real protected health information until security, privacy, clinical-safety, backup, recovery, and regulatory reviews are complete.

## Contents

- [Project status](#project-status)
- [Documentation map](#documentation-map)
- [Visual project maps](#visual-project-maps)
- [Implemented workflows](#implemented-workflows)
- [Clinical workflow diagrams](#clinical-workflow-diagrams)
- [Architecture](#architecture)
- [Technology stack](#technology-stack)
- [Repository layout](#repository-layout)
- [Domain model](#domain-model)
- [Database relationships](#database-relationships)
- [Application catalog](#application-catalog)
- [Permissions and access control](#permissions-and-access-control)
- [State, audit, and record lifecycle](#state-audit-and-record-lifecycle)
- [Clinical evidence register](#clinical-evidence-register)
- [Navigation and application areas](#navigation-and-application-areas)
- [Installation](#installation)
- [Configuration](#configuration)
- [Running the application](#running-the-application)
- [Development workflow](#development-workflow)
- [Testing](#testing)
- [Security and clinical safety](#security-and-clinical-safety)
- [Deployment](#deployment)
- [Known limitations](#known-limitations)
- [Roadmap](#roadmap)
- [Documentation](#documentation)

## Project status

- **Status:** active development
- **Framework:** Django 5.x
- **Default development database:** SQLite
- **Recommended production database:** PostgreSQL
- **Application timezone:** `America/Chicago` (Iowa local time)
- **UI model:** Django templates + HTMX + Alpine.js + Tailwind CSS

The repository contains both operational workflows and scaffold applications. “Installed” in Django does not necessarily mean “clinically complete.” The table below describes the current implementation rather than the intended final product.

| Area | Current state |
| --- | --- |
| Authentication and staff profiles | Implemented foundation |
| Access groups and permission assignment | Implemented group administration and user assignment foundation |
| Facilities, departments, units, rooms, and beds | Implemented management foundation |
| Patient registry and longitudinal overview | Implemented |
| Encounters and encounter audit timeline | Implemented |
| Admission navigation | Implemented through patient registration/admission entry |
| Discharge and transfer | Encounter-scoped nursing assessment workflow; discharge completes encounter |
| Nursing workspace | Implemented assessment, task, I/O, and handoff foundation |
| Vital signs | Implemented entry, history, detail, trends, validation, and correction workflow |
| Diagnoses | Data model and patient integration implemented; dedicated UI remains incomplete |
| Clinical notes | Implemented create, edit, detail, list, and signing workflow |
| Medication orders | Implemented provider order entry and order status workflow |
| MAR | Implemented scheduled/PRN administration and administration history |
| Pharmacy | Implemented review, clarification, verification, dispensing, formulary, and stock ledger foundation |
| Scheduling | Implemented appointment management foundation |
| Care assignments | Implemented time-bounded shifts, nurse/aide patient assignments, self-assignment, workload ratios, and logout-aware completion |
| Secure staff messaging | Implemented direct messaging, broadcasts, patient context, read receipts, and unread polling |
| Clinical dashboard | Live database statistics implemented |
| Analytics dashboards | Implemented foundations; metric governance and validation remain ongoing |
| Laboratory, imaging, documents, flowsheets | Application scaffolds/partial foundations; not complete workflows |
| Clinical decision support | Rules, alerts, acknowledgement/override, recommendations, and risk-score foundation implemented; not clinically validated |
| AI assistant | Application shell only; no production model workflow or autonomous clinical decision-making |
| Billing, patient portal, integrations | Placeholder or early foundation |

## Documentation map

The README is the operational overview and onboarding entry point. Detailed design decisions and traceability live in the documents below:

```mermaid
flowchart TD
    README["README: setup, workflows, status, operations"]
    Requirements["Requirements: actors, functional/non-functional IDs, status, release gates"]
    Architecture["Architecture: system context, layers, request lifecycle, boundaries"]
    WebMap["Web map: navigation, workspaces, URL hierarchy, contextual routes"]
    Dependencies["Application dependencies: ownership, imports, workflows, change impact"]
    HTMX["HTMX rendering: full pages, partials, targets, polling, tests"]
    Database["Database: entities, integrity, migrations, lifecycle"]
    Governance["Permissions, clinical safety, deployment"]

    README --> Requirements
    README --> WebMap
    Requirements --> Architecture
    Architecture --> Dependencies
    Architecture --> HTMX
    Dependencies --> Database
    Requirements --> Governance
```

| Document | Use it when |
| --- | --- |
| [Project requirements](requirements.md) | defining scope, checking implementation status, planning acceptance tests, or preparing release gates |
| [System architecture](architecture.md) | understanding runtime layers, request flow, domain ownership, or security boundaries |
| [Application and web map](web-map.md) | locating user-facing pages, primary navigation, patient/encounter workspaces, URL prefixes, and support endpoints |
| [Application dependencies](application-dependencies.md) | changing a model/app boundary, assessing downstream impact, or adding a dependency |
| [HTMX full pages and partials](htmx-rendering.md) | creating or debugging a page/fragment pair, form swap, search fragment, or polling endpoint |
| [Database](database.md) | reviewing persistence and production database expectations |
| [Permissions](permissions.md) | designing role, group, patient-scope, or emergency-access controls |
| [Clinical safety](clinical-safety.md) | reviewing clinical rules, validation, overrides, or safety ownership |
| [Deployment](deployment.md) | preparing environments, backups, monitoring, or recovery |

## Visual project maps

The rendered SVG maps provide a pictorial overview for readers who do not have Mermaid rendering enabled. Select an image to open the full-size vector diagram.

### Application and web sitemap

[![Liberia EHR application and web sitemap](diagrams/application-sitemap.svg)](diagrams/application-sitemap.svg)

### End-to-end clinical workflow

[![Liberia EHR end-to-end clinical workflow](diagrams/clinical-workflow.svg)](diagrams/clinical-workflow.svg)

Additional visual maps:

- [Application dependencies](diagrams/app-dependencies.svg)
- [HTMX full-page and partial rendering](diagrams/htmx-page-partial.svg)
- [Database relationships](diagrams/database-relations.svg)
- [Secure staff messaging flow](diagrams/secure-messaging-flow.svg)

## Implemented workflows

### Patient registry

- Register and update patient demographics.
- Search by supported identity fields.
- Maintain MRN, DOB/age, sex, contact information, identifiers, addresses, emergency contacts, relationships, insurance, consent, allergies, and patient flags.
- Archive and restore patient records without treating encounter discharge as chart deactivation.
- Review possible duplicate/merge candidates.
- Display a compact longitudinal overview with encounter, diagnosis, medication, note, and current-vitals statistics.
- Distinguish permanent record status from current care status (`Encounter open`, `Discharged`, or `No open encounter`).

### Encounters

- Create, update, view, complete, cancel, or mark an encounter entered in error.
- Support outpatient, inpatient, emergency, observation, telehealth, home visit, community, maternity, surgical, pharmacy, laboratory, imaging, and other encounter types.
- Track planned, scheduled, arrived, triaged, in-progress, on-hold, completed, cancelled, and entered-in-error states.
- Preserve workflow timestamps and status history for audit display.
- Load encounter-associated clinical notes from the encounter summary.
- Expose Discharge/Transfer actions only within an open encounter.
- Complete the encounter when a valid discharge nursing assessment is saved.
- Preselect a patient when the form is opened from the patient chart.
- Require a reason for visit and an intentional attending-provider choice.
- Display providers by full name and job title/role instead of username.
- Support an explicit `N/A — Not applicable` provider choice when no provider applies.
- Prevent duplicate open encounters for the same patient.

### Secure staff messaging

The dedicated `messaging` application provides authenticated, participant-restricted communication at `/secure-chat/`.

- Start a secure message from the high-contrast **Messages** control in the primary green navigation bar.
- Poll unread counts every eight seconds and display a flashing unread badge.
- Send to one or multiple selected staff members.
- Broadcast to the care teams associated with one or more selected patients.
- Broadcast to all active, authorized, non-patient staff accounts.
- Search staff by full name or title and add/remove recipients as chips.
- Search active patients by name or MRN and add/remove them in a Concerned Patients panel.
- Classify a message as general or patient-related before choosing its subject.
- For patient-related messages, select a category such as change of condition, diagnostic results, new order, medication update, care-plan update, discharge/transfer, scheduling, safety concern, or other.
- Link one or multiple patient records to a conversation.
- Display a compact conversation header containing subject, sender, recipients, and concerned patients.
- Distinguish outgoing dark-green bubbles from incoming blue bubbles.
- Mark incoming messages read when an authorized recipient opens or polls the conversation.
- Display read status on sent messages after another participant reads them.
- Escape message content in templates and limit message bodies to 4,000 characters.

Care-team broadcast recipients are resolved from active `PatientCareTeamMember` assignments plus attending providers recorded on the selected patients' encounters. If the selected care-team audience has no eligible recipients, sending is rejected rather than silently dropping the message.

Messaging is server-rendered and uses HTMX/JSON polling; it does not currently require Django Channels, Redis, or a WebSocket service. “Secure” here means authenticated access, participant filtering, CSRF protection, non-cacheable message responses, production HTTPS settings, and restricted administration. It does **not** mean end-to-end encryption or application-level encryption of message bodies at rest.

#### Messaging records and delivery lifecycle

| Record | Purpose |
| --- | --- |
| `Conversation` | Stores subject, general/patient context, patient subject category, audience, participants, optional concerned patients, creator, and activity timestamps |
| `Message` | Stores one sender-authored body, conversation relationship, creation time, and per-user `read_by` receipts |
| `PatientCareTeamMember` | Stores an explicit active patient/staff care-team assignment and role label for care-team recipient resolution |

Message delivery proceeds as follows:

1. The server validates that the sender is an active authorized non-patient staff user (or Django staff/superuser).
2. The compose form validates context, patient selection, subject/category, audience, recipients, and body.
3. The service resolves the audience and rejects an empty eligible-recipient set.
4. The server creates the conversation, participants, optional patient links, and initial message transactionally.
5. The sender is immediately included in `read_by`; recipients remain unread.
6. The primary-nav badge polls `/secure-chat/unread-count/` every eight seconds.
7. An open conversation polls its message fragment every eight seconds and marks incoming messages read for that participant.
8. Non-participants cannot retrieve either the full conversation or its polling fragment.

Messaging routes:

| Route | Purpose |
| --- | --- |
| `/secure-chat/` | Participant-filtered inbox |
| `/secure-chat/new/` | Compose direct or broadcast message |
| `/secure-chat/unread-count/` | Authenticated JSON unread count for the primary navigation badge |
| `/secure-chat/<conversation UUID>/` | Conversation, replies, compact context, and concerned-patient links |
| `/secure-chat/<conversation UUID>/messages/` | Participant-only HTMX polling fragment and read-receipt update |

### Access and security administration

- Manage user identities, active state, staff status, profile role, job title, facility, password-change requirement, and group membership.
- Create and edit reusable Django groups from **Administration → Groups and Permissions**.
- Browse permissions grouped by Django application instead of one undifferentiated list.
- Review member and permission counts for each group.
- Display assigned groups as compact badges in the user directory.
- Reset temporary passwords and require a password change at next login.
- Keep the Administration workspace restricted to Django staff and superusers.

These screens manage assignment. They do not automatically add missing authorization checks to clinical views; server-side permission enforcement remains mandatory.

### Nursing

- Admission, shift, focused, transfer, discharge, post-procedure, and change-in-condition assessments.
- Categorical body-system assessments with WNL/exception behavior.
- Structured neurological, respiratory, cardiovascular, gastrointestinal, genitourinary, integumentary, musculoskeletal, and psychosocial findings.
- Nursing tasks with priority, due time, completion user, and completion time.
- Intake/output records and daily totals.
- Handoff documentation with giving and receiving clinicians.
- Fall-risk and pressure-injury-risk indicators.
- Per-shift structured fall-risk assessment with the six Morse items, shift due/completed status, conservative risk classification, and individualized interventions.
- Side-by-side Morse, logistic, and XGBoost-candidate comparison with explicit model/version provenance; development comparison models are labeled unvalidated.
- Automatic high-fall-risk CDS alert plus three auditable `RiskAssessment` outputs when the per-shift screen is saved.

### Vital signs

- Patient- and encounter-associated observations.
- Blood pressure, pulse, respiratory rate, temperature, oxygen saturation, pain, and supporting clinical context.
- Observation date/time in Iowa local time.
- History, trend, abnormal-vitals, detail, update, and entered-in-error views.
- Current vitals on the patient overview include the actual measurement timestamp.

### Clinical notes

- Encounter-optional patient notes.
- Progress, SOAP, physician, NP, nursing, admission, consultation, procedure, discharge, case-management, care-coordination, telephone, follow-up, and general note types.
- Draft, signed, amended, and voided lifecycle foundation.
- Combined note-detail presentation with clearly separated subjective, objective, assessment, plan, and related sections.

### Medication ordering and MAR

- Provider, order method, order type, clinical indication, receiving user, dose, unit, route, frequency, quantity, timing, and instructions.
- Electronic, written, verbal, and telephone order methods.
- Active, on-hold, discontinued, and completed medication-order states.
- Ordered discontinuation workflow with prescriber, method, reason, date, and receiving user.
- Scheduled and PRN MAR organization.
- Due, overdue, early/not-due, held, refused, omitted, not-given, and administered handling.
- Out-of-window reason capture and next-dose recalculation.
- Grouped administration history to reduce repeated medication names.

### Pharmacy

- Live active-order queue.
- Pharmacist review with allergy, dose, route/frequency, interaction, and formulary checks.
- Verification, clarification-required, and rejection decisions.
- Required reason for clarification or rejection.
- Verified-order dispensing with quantity, lot, expiration, notes, pharmacist, and timestamp.
- Transactional stock decrement that prevents negative inventory.
- Formulary catalog with local/RxNorm terminology support.
- Low-stock and out-of-stock visibility.
- Auditable receipts, adjustments, dispensing movements, and balances.
- Local high-alert, LASA, controlled-medication, and safety-note display.

RxNorm is used for terminology support. The local safety screen is not a substitute for a maintained drug-interaction knowledge base.

### Clinical dashboard

The dashboard uses live database aggregates for the selected 24-hour, 48-hour, or 7-day period:

- Registered patients.
- Open, new, and completed encounters.
- Encounter-type mix and linked current workload.
- Active diagnoses.
- Vital observations, patients assessed, and high-pain observations.
- Active medication orders and administrations.
- Held/refused/not-given medication events.
- Pending pharmacy reviews and low-stock items.
- Nursing assessments, risks, open tasks, and overdue tasks.
- Signed and draft clinical notes.

## Clinical workflow diagrams

These diagrams describe the intended interaction between implemented modules. They are workflow documentation, not a claim of clinical certification.

### End-to-end patient care workflow

```mermaid
flowchart LR
    A["Patient search"] --> B{"Existing chart?"}
    B -- No --> C["Register patient"]
    B -- Yes --> D["Verify identity"]
    C --> D
    D --> E["Create appointment or encounter"]
    E --> F["Arrival and registration"]
    F --> G["Triage and vital signs"]
    G --> H["Nursing assessment"]
    H --> I["Provider evaluation"]
    I --> J["Diagnoses and clinical notes"]
    I --> K["Medication and other orders"]
    K --> L["Pharmacy review and dispense"]
    L --> M["MAR administration"]
    J --> N["Ongoing reassessment"]
    M --> N
    N --> O{"Disposition"}
    O -- Continue care --> H
    O -- Transfer --> P["Transfer assessment and handoff"]
    O -- Discharge --> Q["Discharge assessment"]
    Q --> R["Encounter completed"]
    P --> S["Receiving unit or facility"]
```

### Encounter lifecycle

```mermaid
stateDiagram-v2
    [*] --> Planned
    Planned --> Scheduled
    Planned --> Cancelled
    Scheduled --> Arrived
    Scheduled --> Cancelled
    Arrived --> Triaged
    Arrived --> InProgress
    Triaged --> InProgress
    InProgress --> OnHold
    OnHold --> InProgress
    InProgress --> Completed: discharge/completion
    Planned --> EnteredInError
    Scheduled --> EnteredInError
    Arrived --> EnteredInError
    InProgress --> EnteredInError
    Cancelled --> [*]
    Completed --> [*]
    EnteredInError --> [*]
```

Encounter status is distinct from patient-chart status. Completing or discharging an encounter does not deactivate the longitudinal patient record.

### Medication order-to-administration workflow

```mermaid
flowchart TD
    A["Provider enters medication order"] --> B["Prescriber, method, type, indication, dose, route, frequency, timing"]
    B --> C{"Pharmacy review"}
    C -- Clarification required --> D["Return to ordering clinician"]
    D --> B
    C -- Rejected --> E["Rejected with reason"]
    C -- Verified --> F["Dispensing"]
    F --> G["Inventory transaction"]
    G --> H["Active MAR order"]
    H --> I{"Scheduled or PRN?"}
    I -- Scheduled --> J["Calculate due window"]
    I -- PRN --> K["Check interval and last dose"]
    J --> L{"Administered in window?"}
    K --> L
    L -- Yes --> M["Record administration"]
    L -- Early or late --> N["Require reason"]
    N --> M
    M --> O["Recalculate next due time"]
    O --> H
    H --> P{"Order state change"}
    P -- Hold --> Q["Hidden from actionable MAR until unheld"]
    P -- Discontinue order --> R["Removed from active MAR; retained in history"]
```

### Nursing workflow

```mermaid
flowchart LR
    A["Open patient encounter"] --> B{"Assessment type"}
    B --> C["Admission"]
    B --> D["Shift"]
    B --> E["Focused/change in condition"]
    B --> F["Transfer"]
    B --> G["Discharge"]
    C --> H["Body-system assessment"]
    D --> H
    E --> H
    H --> I{"System WNL?"}
    I -- Yes --> J["Hide exception fields"]
    I -- No --> K["Capture structured exceptions"]
    J --> L["Risks, pain, narrative"]
    K --> L
    L --> M["Tasks and intake/output"]
    M --> N["SBAR handoff: giver and receiver"]
    F --> N
    G --> O["Disposition and education"]
    O --> P["Complete encounter"]
```

### Appointment workflow

```mermaid
flowchart LR
    A["Create appointment"] --> B["Patient, provider, department, unit, room, date/time"]
    B --> C["Requested or scheduled"]
    C --> D["Confirmed"]
    D --> E["Checked in"]
    E --> F["In progress"]
    F --> G["Completed"]
    C --> H["Cancelled/no-show"]
    D --> H
```

## Architecture

```text
Browser
  ├─ Django-rendered HTML
  ├─ HTMX fragment requests
  ├─ Secure-message thread and unread-count polling
  ├─ Alpine.js presentation state
  └─ Tailwind CSS
          │
          ▼
Django URL routing and authentication
          │
          ▼
Views / forms / selectors / services
          │
          ▼
Domain models and transactional workflows
          │
          ▼
SQLite (development) or PostgreSQL (recommended production)
```

Architectural rules used by the project:

- Django owns authoritative clinical state.
- HTMX returns server-rendered partials; it does not duplicate the domain model in JavaScript.
- Alpine.js controls local disclosure, tabs, conditional form sections, and presentation state.
- Multi-record clinical writes use database transactions.
- Patient records and clinical history should normally be archived, voided, amended, discontinued, or entered in error—not hard-deleted.
- Patient identity is longitudinal; an encounter is one episode of care.
- Medication catalog, provider order, pharmacy review/dispense, and bedside administration are separate records.
- Time values are stored timezone-aware and displayed in `America/Chicago`.
- Secure-message authorization is enforced in server-side views and services; Alpine.js only controls recipient/patient search presentation.
- Direct and broadcast messages share one participant-restricted conversation model with per-user read receipts.

See [Architecture](architecture.md) and [Database](database.md).

## Technology stack

| Layer | Technology |
| --- | --- |
| Backend | Python, Django 5.x |
| UI rendering | Django templates |
| Partial page updates | HTMX |
| Local UI state | Alpine.js |
| Styling | Tailwind CSS 3.x, Tailwind Forms |
| Development database | SQLite |
| Production database | PostgreSQL via psycopg |
| Static files | WhiteNoise |
| WSGI server | Gunicorn |
| Environment configuration | django-environ |
| Testing | Django test runner, pytest, pytest-django, factory-boy |
| Code quality | Ruff |
| Production monitoring dependency | Sentry SDK |

## Repository layout

```text
liberia_ehr/
├── apps/                    # Django domain applications
│   ├── accounts/           # Authentication profiles and role metadata
│   ├── administration/     # Scheduling and administrative workspaces
│   ├── analytics/          # Operational/clinical analytics foundations
│   ├── clinical_notes/     # Clinical documentation
│   ├── encounters/         # Episodes of care and encounter lifecycle
│   ├── facilities/         # Facility hierarchy and locations
│   ├── medications/        # MAR and medication administration
│   ├── messaging/          # Secure direct/broadcast staff conversations
│   ├── nursing/            # Assessments, tasks, I/O, handoff
│   ├── orders/             # Medication orders
│   ├── patients/           # Patient identity and longitudinal record
│   ├── pharmacy/           # Formulary, review, dispensing, inventory
│   ├── vitals/             # Vital observations and trends
│   └── ...                 # Partial/planned clinical domains
├── config/
│   ├── settings/           # Base, development, test, production settings
│   └── urls.py             # Project URL composition
├── docs/                   # Architecture, safety, database, deployment docs
├── requirements/           # Python dependency sets
├── static/                 # Tailwind source and static assets
├── templates/              # Shared shell, navigation, sidebars, components
├── manage.py
├── package.json
├── pytest.ini
└── README.md
```

The directory `apps/liberia_ehr_patient_facility_htmx_views 2/` appears to be a legacy/reference copy and is not listed in `INSTALLED_APPS`. Do not make new application changes there.

## Domain model

```text
Patient
  └─ Encounter
      ├─ VitalObservation
      ├─ PatientDiagnosis
      ├─ ClinicalNote
      ├─ NursingAssessment / NursingTask / IntakeOutput / Handoff
      ├─ MedicationOrder
      │   ├─ PharmacyReview
      │   ├─ DispenseRecord ── InventoryTransaction
      │   └─ MedicationAdministration
      └─ audit/status timing

Medication (formulary)
  ├─ MedicationOrder
  ├─ DispenseRecord
  ├─ MedicationAdministration
  └─ InventoryTransaction

Conversation
  ├─ participants (authorized staff users)
  ├─ patients (optional concerned patient records)
  ├─ Message
  │   └─ read_by (per-user read receipts)
  └─ subject / context / audience

Patient
  └─ PatientCareTeamMember ── authorized staff user
```

Important distinctions:

- `Patient.is_active` describes the administrative availability of the longitudinal chart. Discharge does not deactivate it.
- `Encounter.status` describes the current episode of care. A discharge assessment completes that encounter.
- `Medication` is the formulary product/concept.
- `MedicationOrder` is the provider authorization.
- `PharmacyReview` documents pharmacist verification or clarification.
- `DispenseRecord` documents supply from pharmacy.
- `MedicationAdministration` documents what occurred at the bedside.
- `Conversation` is the authorization boundary for secure messages; membership—not possession of a UUID—permits access.
- `notifications` remains a separate scaffold for future system-generated alerts and is not the storage domain for staff chat.

## Database relationships

### Core clinical relationship diagram

```mermaid
erDiagram
    AUTH_USER ||--o| USER_PROFILE : has
    FACILITY ||--o{ DEPARTMENT : contains
    FACILITY ||--o{ CLINICAL_UNIT : contains
    DEPARTMENT ||--o{ CLINICAL_UNIT : organizes
    FACILITY ||--o{ ROOM : contains
    CLINICAL_UNIT ||--o{ ROOM : contains
    ROOM ||--o{ BED : contains

    PATIENT ||--o{ PATIENT_IDENTIFIER : has
    PATIENT ||--o{ PATIENT_ALIAS : has
    PATIENT ||--o{ PATIENT_ALLERGY : has
    PATIENT ||--o{ PATIENT_ADDRESS : has
    PATIENT ||--o{ PATIENT_CONTACT_POINT : has
    PATIENT ||--o{ EMERGENCY_CONTACT : has
    PATIENT ||--o{ INSURANCE_COVERAGE : has
    PATIENT ||--o{ PATIENT_CONSENT : has
    PATIENT ||--o{ PATIENT_FLAG : has

    PATIENT ||--o{ APPOINTMENT : schedules
    FACILITY ||--o{ APPOINTMENT : hosts
    DEPARTMENT o|--o{ APPOINTMENT : assigns
    CLINICAL_UNIT o|--o{ APPOINTMENT : assigns
    ROOM o|--o{ APPOINTMENT : assigns
    AUTH_USER o|--o{ APPOINTMENT : provides

    PATIENT ||--o{ ENCOUNTER : receives
    FACILITY ||--o{ ENCOUNTER : hosts
    AUTH_USER o|--o{ ENCOUNTER : attends
    ENCOUNTER ||--o{ VITAL_OBSERVATION : records
    ENCOUNTER ||--o{ CLINICAL_NOTE : documents
    ENCOUNTER ||--o{ PATIENT_DIAGNOSIS : diagnoses
    ENCOUNTER ||--o{ NURSING_ASSESSMENT : assesses
    ENCOUNTER ||--o{ NURSING_TASK : assigns
    ENCOUNTER ||--o{ INTAKE_OUTPUT_RECORD : measures
    ENCOUNTER ||--o{ NURSING_HANDOFF : communicates

    MEDICATION ||--o{ MEDICATION_ORDER : ordered_as
    PATIENT ||--o{ MEDICATION_ORDER : receives
    ENCOUNTER o|--o{ MEDICATION_ORDER : authorizes
    AUTH_USER ||--o{ MEDICATION_ORDER : prescribes
    MEDICATION_ORDER ||--o{ PHARMACY_REVIEW : reviewed_by
    MEDICATION_ORDER ||--o{ DISPENSE_RECORD : dispensed_as
    MEDICATION_ORDER ||--o{ MEDICATION_ADMINISTRATION : administered_as
    MEDICATION ||--o{ INVENTORY_TRANSACTION : moves
    DISPENSE_RECORD o|--o{ INVENTORY_TRANSACTION : generates

    CLINICAL_RULE ||--o{ CLINICAL_ALERT : triggers
    PATIENT ||--o{ CLINICAL_ALERT : receives
    ENCOUNTER o|--o{ CLINICAL_ALERT : contextualizes
    PATIENT ||--o{ RISK_ASSESSMENT : scored

    AUTH_USER }o--o{ CONVERSATION : participates
    AUTH_USER ||--o{ MESSAGE : sends
    CONVERSATION ||--o{ MESSAGE : contains
    AUTH_USER }o--o{ MESSAGE : reads
    PATIENT }o--o{ CONVERSATION : concerns
    PATIENT ||--o{ PATIENT_CARE_TEAM_MEMBER : has
    AUTH_USER ||--o{ PATIENT_CARE_TEAM_MEMBER : assigned
```

### Major model ownership

| Domain | Primary models | Ownership and relationship notes |
| --- | --- | --- |
| Identity | `Patient`, identifiers, aliases, addresses, contacts, consents, insurance, allergies, flags | Patient is the longitudinal root; supporting identity records belong to one patient |
| Organization | `Facility`, `Department`, `ClinicalUnit`, `Room`, `Bed`, `FacilityService`, `FacilityOperatingHour` | Hierarchical care-delivery locations; child records are facility-scoped |
| Scheduling | `Appointment` | Connects patient, facility, optional department/unit/room, provider, timing, status, and priority |
| Care episode | `Encounter` | Patient-specific episode of care and parent context for clinical documentation |
| Observations | `VitalObservation` | Belongs to a patient and encounter; records observer and observation time |
| Diagnoses | `PatientDiagnosis`, terminology/concept models, manifestations, procedure codes | Clinical terminology foundation and patient diagnosis history |
| Notes | `ClinicalNote` | Patient note with optional encounter association and author/signature lifecycle |
| Nursing | `NursingAssessment`, `NursingTask`, `IntakeOutputRecord`, `NursingHandoff` | All are protected patient/encounter records with recording clinician and timestamp |
| Orders | `MedicationOrder` | Provider authorization and medication schedule/state source for MAR and pharmacy |
| Pharmacy | `Medication`, `PharmacyReview`, `DispenseRecord`, `InventoryTransaction` | Separates formulary, clinical review, physical dispense, and stock ledger |
| MAR | `MedicationAdministration` | Immutable-style administration event linked to order, patient, encounter, and administering user |
| CDS | `ClinicalRule`, `ClinicalAlert`, `RiskAssessment` | Versioned deterministic rules and patient/encounter outputs |
| Analytics | `SavedReport`, `MeasureDefinition`, `MeasureResult`, `AnalyticsSnapshot`, `DataExportJob` | Report definitions, governed measures, snapshots, and exports |
| Administration | `SystemSetting`, `ClinicalDictionaryEntry`, `IntegrationConfiguration` | Operational configuration records |
| Secure messaging | `Conversation`, `Message`, `PatientCareTeamMember` | Participant-restricted direct/broadcast threads, patient context, care-team routing, and read receipts |

### Relationship and deletion rules

- Clinical foreign keys generally use `PROTECT` so referenced patients, encounters, users, medications, and organizational records cannot be silently removed.
- Longitudinal clinical data should be corrected through status, amendment, void, archive, discontinue, or entered-in-error workflows.
- `created_by`, `updated_by`, `recorded_by`, `administered_by`, `reviewed_by`, and similar user links preserve accountability.
- Optional encounter links support valid longitudinal records created outside a specific episode, where the model permits it.
- The development database is SQLite. PostgreSQL is recommended for production concurrency, locking, operational resilience, and backup tooling.
- Messaging conversations protect message membership with participant relationships; messages cascade with their conversation, while sender references are protected.

## Application catalog

All entries below are present in `INSTALLED_APPS`. “Foundation” means useful models or screens exist but the domain is not yet complete end to end.

| Django app | Responsibility | Notable features/routes | Maturity |
| --- | --- | --- | --- |
| `accounts` | Authentication and staff profile metadata | Login/logout, profile, access-denied handling, role helpers | Foundation |
| `core` | Shared dashboards and application shell | Main, clinical, analytics, pharmacy, laboratory, radiology, billing, front-desk, audit dashboards | Mixed |
| `facilities` | Organization and physical locations | Facilities, departments, units, rooms, beds, services, operating hours | Implemented foundation |
| `patients` | Enterprise patient registry | Search, registration, overview, demographics, child records, archive/restore, merge review, flags | Implemented foundation |
| `encounters` | Episodes of care | List, create, detail, update, complete, cancel, entered-in-error | Implemented foundation |
| `vitals` | Vital observations | Entry, patient/encounter history, trends, update, entered-in-error | Implemented |
| `nursing` | Encounter nursing workspace | Assessments, tasks, intake/output, handoff, discharge/transfer documentation | Implemented foundation |
| `clinical_notes` | Clinical documentation | Create, list, detail, edit, sign | Implemented foundation |
| `diagnoses` | Terminology and diagnoses | Concept sources/terms/relationships, patient diagnoses, manifestations, procedures | Model-rich foundation |
| `orders` | Medication ordering | Patient/encounter orders, prescriber and order-method capture, hold/discontinue workflows | Implemented foundation |
| `medications` | MAR and medication reconciliation | Patient medication list, reconciliation, scheduled/PRN MAR, history | Implemented foundation |
| `messaging` | Secure staff communication | Direct messages, specific-recipient broadcasts, care-team/all-staff broadcasts, patient context, read receipts, unread polling | Implemented foundation |
| `pharmacy` | Formulary, verification, dispense, stock | Work queues, catalog, RxNorm import/search, review, dispensing, inventory | Implemented foundation |
| `administration` | Administrative operations | Scheduling calendar, users, groups/permissions, facilities, dictionaries, integrations, settings | Implemented foundation |
| `analytics` | Measures and reports | Dashboard families, saved reports, definitions/results, snapshots, exports | Foundation |
| `decision_support` | Deterministic clinical decision support | Rules, alerts, action/override, recommendations, risk scores | Foundation; unvalidated |
| `ai_assistant` | Future governed AI assistance | Installed shell; no autonomous or validated clinical workflow | Scaffold |
| `audit` | Audit domain | Installed application shell | Scaffold |
| `notifications` | Notification domain | Installed application shell | Scaffold |
| `laboratories` | Laboratory domain | Installed model/app shell; dashboard entry exists | Scaffold |
| `imaging` | Imaging/radiology domain | Installed model/app shell; dashboard entry exists | Scaffold |
| `care_management` | Shift-based care staffing | Shift creation, nurse/aide patient assignment, self-assignment, drag/drop board, ratios, two-condition completion | Implemented foundation |
| `documents` | Clinical document management | Installed model/app shell | Scaffold |
| `flowsheets` | Structured longitudinal charting | Installed model/app shell | Scaffold |

### Route namespaces

| URL prefix | Namespace | Purpose |
| --- | --- | --- |
| `/` | `core` | Dashboards and global entry points |
| `/accounts/` | `accounts` and Django auth | Authentication, profile, password workflows |
| `/patients/` | `patients` | Patient registry and chart |
| `/encounters/` | `encounters` | Encounter lifecycle |
| `/vitals/` | `vitals` | Vital observation workflows |
| `/nursing/` | `nursing` | Patient/encounter nursing workspace |
| `/care-management/` | `care_management` | Care shifts, patient assignments, staff loads, and ratios |
| `/clinical-notes/` | `clinical_notes` | Note workflows |
| `/orders/` | `orders` | Medication-order entry and history |
| `/medications/` | `medications` | Patient medications, reconciliation, MAR |
| `/secure-chat/` | `messaging` | Secure staff inbox, compose, conversation, message polling, unread count |
| `/pharmacy/` | `pharmacy` | Pharmacy operations and formulary |
| `/facilities/` | `facilities` | Organization hierarchy management |
| `/administration/` | `administration` | Scheduling, user/role, and system administration |
| `/analytics/` | `analytics` | Analytical dashboards |
| `/ai-cds/` | `decision_support` | Rules, alerts, recommendations, risk scores |
| `/admin/` | Django admin | Framework-level administration |

## Permissions and access control

### Current authorization model

The project combines four mechanisms:

1. Django authentication (`is_authenticated`).
2. Django staff/superuser flags (`is_staff`, `is_superuser`).
3. `UserProfile` attributes such as active-staff status and clinical role.
4. Django groups and model permissions managed in the Administration role interface.

The Administration **Groups and Permissions** workspace creates reusable Django groups, organizes permission choices by application, shows group member/permission counts, and assigns groups to user accounts. Group membership is displayed in the user directory. Permission existence or assignment does not replace enforcement in each protected view/service.

The existence of a Django permission in a group does not guarantee every view currently enforces it. Authorization enforcement remains a documented hardening priority.

### Current access matrix

| Area/action | Current gate | Notes |
| --- | --- | --- |
| Login/profile | Authenticated user | Standard Django authentication lifecycle |
| Patient, encounter, vitals, notes, nursing, medication views | Primarily authenticated user | Clinical/facility/object-level policy is not yet consistently enforced |
| Administration workspace | Staff or superuser | Enforced by `AdministrationAccessMixin` |
| User and role administration | Staff or superuser | Can create/edit users, toggle access, reset temporary passwords, and assign groups/permissions |
| Formulary create/update/delete | Staff or superuser | Enforced by pharmacy catalog management mixin |
| Pharmacy operational views | Authenticated user, with staff gates on selected mutations | Requires systematic role review before production |
| CDS rules management | Staff user | Rule-management views use a staff predicate |
| Secure messaging inbox/compose | Active non-patient staff, staff flag, or superuser | Enforced by `StaffMessagingAccessMixin` |
| Secure conversation/thread polling | Conversation participant only | Non-participants receive 404; message responses are marked `no-store, private` |
| Messaging broadcasts | Authorized messaging user | Server resolves and validates specific, care-team, or all-staff recipients |
| Messaging Django admin | Superuser only | Ordinary Django staff cannot browse message contents through admin |
| Superuser | Full bypass where decorators/mixins explicitly allow it | Reserve for emergency technical administration |
| Django admin | Staff plus Django model permissions | Separate from the custom Administration workspace |

### Available authorization helpers

| Helper | Intended rule |
| --- | --- |
| `active_staff_required` | Superuser or active EHR staff profile |
| `role_required(*roles)` | Superuser or active staff whose profile role is in the allowed set |
| `clinical_staff_required` | Superuser or active clinical staff profile |
| `AdministrationAccessMixin` | Authenticated staff or superuser |
| `StaffMessagingAccessMixin` | Active authorized non-patient staff, Django staff, or superuser |
| `ParticipantConversationMixin` | Messaging access plus explicit conversation participation |
| `MedicationCatalogManagementMixin` | Authenticated staff or superuser |
| `LoginRequiredMixin` / `login_required` | Any authenticated account |

### Recommended production role matrix

This is a target policy and must be implemented and tested before deployment.

| Capability | Registrar | Nurse | Provider | Pharmacist | Analyst | Facility admin | System admin |
| --- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| Search/register patients | ✓ | View | View | View | Limited | ✓ | ✓ |
| Create/manage appointments | ✓ | View | View | — | — | ✓ | ✓ |
| Create/manage encounters | ✓ | Update workflow | ✓ | View | — | ✓ | ✓ |
| Record vitals and nursing care | — | ✓ | ✓ | — | — | — | ✓ |
| Author/sign clinical notes | — | Role-scoped | ✓ | Role-scoped | — | — | ✓ |
| Enter medication orders | — | Protocol-limited | ✓ | Clarification only | — | — | ✓ |
| Administer medication/MAR | — | ✓ | Role-scoped | — | — | — | ✓ |
| Verify/dispense medication | — | — | View | ✓ | — | — | ✓ |
| Manage formulary/inventory | — | — | View | ✓ | — | Limited | ✓ |
| View identified analytics | Limited | Limited | Limited | Limited | Approved | Approved | ✓ |
| Manage facilities/users/roles | — | — | — | — | — | Facility-scoped | ✓ |
| Secure direct messaging | ✓ | ✓ | ✓ | ✓ | Approved | ✓ | ✓ |
| Broadcast to care team/all staff | Policy-scoped | Policy-scoped | Policy-scoped | Policy-scoped | — | Approved | ✓ |
| Configure CDS rules | — | — | Clinical owner | Pharmacy rules | — | — | Technical only |

### Permission implementation requirements

- Enforce permissions in views/services, not only by hiding navigation links.
- Scope access by facility, department, role, patient relationship, and encounter where applicable.
- Separate view, add, change, sign, verify, administer, discontinue, export, and delete/void permissions.
- Require reason capture for overrides, early/late medication administration, order discontinuation, corrections, and emergency access.
- Audit both successful and denied access to sensitive actions.
- Test normal requests and HTMX partial requests for identical authorization behavior.
- Never rely on client-side Alpine.js state as an authorization control.
- Treat patient-linked messages as PHI: enforce the same patient/facility relationship policy used by the underlying chart before production.
- Restrict all-staff broadcasting through an explicit permission/approval policy before production; current access is based on authorized messaging eligibility.

## State, audit, and record lifecycle

### Clinical record principles

- Patient identity persists across encounters.
- Encounter completion closes an episode; it does not delete its documentation.
- Signed notes should be amended or voided, not overwritten without trace.
- Medication orders move through active, held, completed, or discontinued states.
- Discontinued medication orders leave the active MAR but remain visible in audit/history views.
- Medication administrations remain event records even when the parent order later changes state.
- Incorrect observations should be marked entered in error through the supported workflow.
- Pharmacy stock movements use ledger records; dispensing should be transactional and prevent negative inventory.

### Minimum audit event content

Every production-grade audit event should capture:

- Actor user ID and effective role.
- Patient and encounter context, when applicable.
- Facility/workstation/session context.
- Action and affected object type/ID.
- Previous and new state for material changes.
- UTC timestamp plus Iowa-local presentation.
- Override, correction, cancellation, or discontinuation reason.
- Request/correlation identifier for related transactions.

The installed `audit` application is currently a scaffold. Django model timestamps and user-tracking fields provide useful provenance but are not a substitute for an immutable access and change audit log.

## Clinical evidence register

This register identifies the source and governance status of clinical content currently represented in code. Every new evidence-based threshold, score, protocol, clinical dictionary, alert, or recommendation must add an entry here and store a source/version in the relevant configuration or CDS rule when the model supports it.

### Evidence classifications

| Classification | Meaning |
| --- | --- |
| External standard/guideline | Published by an authoritative professional, governmental, standards, or patient-safety organization |
| Textbook framework | Used to organize assessment content; does not independently define a local escalation policy |
| Local policy | A configurable operational choice that requires facility approval and is not presented as universally evidence-based |
| Development model | Experimental or illustrative logic that requires local training, validation, monitoring, and approval before clinical reliance |
| Terminology service | Provides normalized concepts/codes, not clinical judgment or medication safety conclusions |

### Evidence and policy matrix

| Clinical content in Liberia EHR | Implementation | Source/reference | Classification and limitations |
| --- | --- | --- | --- |
| Head-to-toe nursing physical assessment organization | `NursingAssessment`, assessment form, collapsible system sections | Carolyn Jarvis and Ann L. Eckhardt, *Physical Examination & Health Assessment*, 9th ed., Elsevier, 2024, ISBN 978-0-323-80984-9. [Elsevier title page](https://www.us.elsevierhealth.com/physical-examination-and-health-assessment-9780323809849.html) | Textbook framework. The application uses original field labels and structured categories; it does not reproduce proprietary textbook narrative, images, or tables. Facility educators must validate scope and competency expectations. |
| General survey; mental status; skin; head/face/neck; eyes; ears; nose/mouth/throat; thorax/lungs; cardiovascular; peripheral vascular; abdomen; musculoskeletal; neurological; functional assessment | Nursing body-system components | Jarvis & Eckhardt, 9th ed., above | Textbook framework mapped to the most appropriate nursing components. Sensitive examinations and population-specific examinations require indication, consent, privacy, training, and local documentation policy. |
| WNL versus exception disclosure | Nursing Alpine.js assessment UI and server form cleaning | Jarvis structured examination framework; local documentation design | Hybrid textbook framework/local policy. “WNL” must mean the organization’s approved expected findings and must never conceal an assessed exception. |
| Morse Fall Scale six items and item weights | `apps/nursing/fall_risk.py::calculate_morse` | [VA National Center for Patient Safety Morse Fall Scale pocket card](https://www.patientsafety.va.gov/docs/fallsToolkit/morse_falls_pocket_card.pdf); [AHRQ fall-prevention resources](https://www.ahrq.gov/patient-safety/settings/hospital/fall-prevention/toolkit/index.html) | External assessment tool. Current low/moderate/high cut points must be approved against the facility’s adopted Morse policy before production. |
| Per-shift fall-risk screening and individualized prevention | Nursing Assessment tab and fall-risk due indicator | [AHRQ Preventing Falls in Hospitals toolkit](https://www.ahrq.gov/patient-safety/settings/hospital/fall-prevention/toolkit/index.html); [CDC STEADI clinical resources](https://www.cdc.gov/steadi/hcp/clinical-resources/index.html) | External guidance plus local workflow. Exact shift frequency is local policy and should also trigger after transfer, fall, medication/condition change, or other locally defined events. |
| Logistic fall-risk comparison | `logistic_probability()` | Local development equation, version `0.1-unvalidated`; comparative model rationale informed by published inpatient fall-prediction research such as [Jung et al., 2022](https://pubmed.ncbi.nlm.nih.gov/36128798/) | Development model. Coefficients were not trained on Liberia EHR data. Do not use for autonomous clinical decisions. |
| XGBoost-labeled fall-risk comparison | `boosted_tree_probability()` | Local transparent boosted-tree comparator, version `0.1-unvalidated`; model-family rationale informed by [Ho et al., 2023](https://pubmed.ncbi.nlm.nih.gov/38076265/) | Development model. This is not a fitted XGBoost library artifact; the UI labels it as an unvalidated comparison. Replace with a governed, trained, calibrated, externally validated artifact before clinical reliance. |
| Conservative fall-risk alert | Highest category among Morse and development comparators | Local safety policy | Local policy. Prevents a development comparator from silently lowering a nurse-observed risk; clinical action remains subject to nursing judgment and approved protocol. |
| Blood pressure categories and severe threshold | `VitalObservation.abnormal_findings` | [American Heart Association blood pressure categories](https://www.heart.org/en/health-topics/high-blood-pressure/understanding-blood-pressure-readings) | External guideline reference. The application’s low-pressure threshold is a local screening threshold and must be population-/context-validated. Alerts do not diagnose hypertension or shock. |
| Oxygen saturation flags | `VitalObservation.abnormal_findings` | [British Thoracic Society guideline for oxygen use](https://thorax.bmj.com/content/72/Suppl_1/ii1); local escalation policy | External guideline plus local thresholds. Target saturation varies for conditions such as risk of hypercapnic respiratory failure; fixed flags require clinician interpretation. |
| Temperature flags | `VitalObservation.abnormal_findings` | Local screening thresholds; clinical context informed by standard temperature assessment practice | Local policy. Measurement site, device, age, immune status, and clinical condition materially affect interpretation. |
| Numeric pain score and moderate/severe display groups | Vitals and Nursing pain fields | [Defense and Veterans Pain Rating Scale](https://www.health.mil/Military-Health-Topics/Conditions-and-Treatments/Pain-Management/DVPRS) and local policy | External scale concept plus local display categories. Self-report, function, goals, and reassessment matter; a number alone is not a treatment order. |
| High-alert medication designation | Pharmacy formulary safety flags and MAR badges | [ISMP List of High-Alert Medications in Acute Care Settings](https://www.ismp.org/recommendations/high-alert-medications-acute-list) | External patient-safety reference. Local formulary flags require pharmacy governance and version review. |
| Look-alike/sound-alike medication designation | Pharmacy formulary and MAR badges | [ISMP confused drug names resources](https://www.ismp.org/recommendations/confused-drug-names-list) and local formulary review | External reference plus local policy. Display flags are not a complete interaction or dispensing safety system. |
| Controlled medication designation | Pharmacy formulary fields | Applicable national/state controlled-substance law and local pharmacy policy | Regulatory/local policy. The deployment jurisdiction must maintain the authoritative schedule and audit requirements. |
| RxNorm identifiers and US medication search/import | Pharmacy catalog and `RxNormClient` | [U.S. National Library of Medicine RxNorm](https://www.nlm.nih.gov/research/umls/rxnorm/) and [RxNav APIs](https://lhncbc.nlm.nih.gov/RxNav/APIs/) | Terminology service only. RxNorm normalization does not establish formulary approval, dose safety, interaction safety, or legal availability. |
| MAR one-hour due display window | `MAR_DUE_WINDOW` | Local medication-administration policy | Local policy, not asserted as a universal standard. Must be configurable by medication, route, urgency, and organization policy. |
| MAR three-hour early/late reason requirement | `MAR_REASON_WINDOW` | Local medication-administration policy | Local policy. Reason capture does not by itself make an early/late administration clinically safe. Time-critical medications require narrower governed windows. |
| Medication frequency-to-interval mapping | `FREQUENCY_INTERVALS` | Order semantics and local scheduling policy | Local implementation. Calendar scheduling must respect the actual prescriber order, pharmacy verification, time-critical classification, and maximum dose/interval rules. |
| Drug interaction screen disclaimer | Pharmacy medication-safety workspace | [ISMP medication-safety resources](https://www.ismp.org/resources) | The project currently displays local safety flags only and explicitly does not claim a comprehensive interaction knowledge base. |
| Clinical alert acknowledgement/override lifecycle | `ClinicalRule`, `ClinicalAlert`, action form | Local CDS governance design informed by traceability and human-review principles | Local policy. Each production rule requires named clinical ownership, evidence, version, effective/review dates, validation, monitoring, and override review. |

### Jarvis-aligned nursing component map

| Nursing assessment component | Structured Liberia EHR fields |
| --- | --- |
| General survey | Overall WNL/exception, general appearance, apparent distress, hygiene/grooming, pain and functional cues |
| Mental status and neurological | Consciousness, orientation, pupils, speech, motor strength, neurological narrative |
| Skin/hair/nails | Color, temperature, moisture, integrity, wounds, pressure-injury stage/risk |
| Head, face, and neck | Facial symmetry, head/scalp, neck findings |
| Eyes | Vision concern, corrective lenses, visible redness/drainage |
| Ears | Hearing concern, hearing aid, pain/drainage |
| Nose, mouth, and throat | Nasal patency/sinuses, mucosa/dentition, lesions, swallowing concern |
| Thorax and lungs | Pattern, effort, lobe-specific breath sounds, cough, oxygen support, respiratory narrative |
| Heart and neck vessels | Rhythm, heart sounds, cardiovascular narrative |
| Peripheral vascular | Pulses, laterality, capillary refill, edema grade/location |
| Abdomen/GI | Abdomen, bowel sounds and exception quadrant, nausea/vomiting, bowel movement, diet tolerance |
| Genitourinary | Urinary pattern, urine characteristics, urinary device |
| Musculoskeletal and function | Strength, gait, assistive device, mobility, activity tolerance, baseline function |
| Psychosocial/communication | Mood/affect, behavior, communication needs, handoff safety concerns |

This mapping is intentionally a nursing documentation framework, not a verbatim reproduction of Jarvis. Genital, breast, rectal, detailed cranial nerve, and other focused examinations should be added only to an appropriate role- and indication-specific workflow with consent, chaperone, privacy, competency, and local-policy controls.

### Evidence maintenance rules

- Record title, publisher/organization, edition/version, publication year, URL/identifier, owner, review date, and affected code/configuration.
- Prefer primary guidelines, official standards, validated instruments, regulators, and maintained terminology services over secondary summaries.
- Do not encode textbook-derived content beyond licensed use; cite and paraphrase the framework.
- Mark all locally chosen thresholds and workflows as local policy.
- Mark all unfitted, unvalidated, or non-local models as development models in code and UI.
- Review changed or withdrawn sources and revalidate affected alerts before release.
- Clinical governance—not a software commit alone—approves production activation.

## Navigation and application areas

### Clinical

Implemented links include Clinical Dashboard, Patients, Admission, patient-specific Encounters, Nursing, Orders, Medications/MAR, and Pharmacy. Patient-specific items are hidden until a patient—and where required an open encounter—is selected.

### Encounter actions

Discharge and Transfer belong to the selected open encounter, not the global navbar. Discharge and Transfer open the appropriate nursing assessment. Saving a discharge assessment completes the encounter.

### Analytics

Clinical, nursing, operations, quality, population, and patient-outcomes routes exist. These remain subject to metric-definition, data-quality, access-control, and clinical-validation work.

### Administration

Scheduling, users, groups/permissions, facilities, departments, rooms, system settings, dictionaries, integrations, audit logs, and system-health routes exist. User accounts can be assigned to reusable groups whose permissions are organized by Django application. Some areas remain operational foundations rather than finished administrative products.

### Secure messaging

The primary green navigation bar contains a persistent amber **Messages** control for authenticated users. Its red badge flashes when unread messages exist and refreshes every eight seconds. The secure-chat inbox supports direct and broadcast threads. Conversation pages poll for new messages every eight seconds and keep the reply box adjacent to short threads while making long threads scrollable.

### Remaining navbar work

Laboratory, imaging/radiology, billing, care management, documents, flowsheets, system notifications, AI assistant, patient portal, and interoperability require further implementation. Secure staff messaging is implemented separately from the scaffold `notifications` domain. Decision support has an operational foundation but requires clinical validation and governance. See [Roadmap](#roadmap).

## Installation

### Prerequisites

- Python 3.12 or newer (the current local environment may use a newer Python version).
- Node.js and npm.
- Git.
- PostgreSQL 17 if using the included database container or a production-like database.

### 1. Create the Python environment

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
pip install -r requirements/development.txt
```

Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip setuptools wheel
pip install -r requirements/development.txt
```

### 2. Install frontend dependencies

```bash
npm install
```

### 3. Create `.env`

There is currently no committed `.env.example`; create `.env` in the repository root. `.env` is ignored by Git.

SQLite development example:

```dotenv
DJANGO_SETTINGS_MODULE=config.settings.development
DJANGO_SECRET_KEY=replace-with-a-long-development-secret
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=127.0.0.1,localhost
DATABASE_ENGINE=sqlite
SQLITE_NAME=db.sqlite3
RXNORM_API_BASE_URL=https://rxnav.nlm.nih.gov/REST
```

PostgreSQL example:

```dotenv
DJANGO_SETTINGS_MODULE=config.settings.development
DJANGO_SECRET_KEY=replace-with-a-long-development-secret
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=127.0.0.1,localhost
DATABASE_ENGINE=postgres
POSTGRES_DB=liberia_ehr
POSTGRES_USER=liberia_ehr
POSTGRES_PASSWORD=replace-this-password
POSTGRES_HOST=127.0.0.1
POSTGRES_PORT=5432
RXNORM_API_BASE_URL=https://rxnav.nlm.nih.gov/REST
```

### 4. Initialize the database

```bash
python manage.py check
python manage.py migrate
python manage.py createsuperuser
```

Messaging schema is introduced by `messaging.0001_initial`, extended with broadcast/patient/care-team fields in `messaging.0002_...`, and extended with context/category fields in `messaging.0003_...`. Normal `migrate` applies all three. Explicit patient care-team memberships can currently be managed by a superuser through Django admin; encounter attending providers are also considered during care-team broadcast resolution.

Do not run `makemigrations` routinely during setup. Migrations should already be committed; use it only while intentionally changing models.

### 5. Build CSS

Watch during development:

```bash
npm run dev
```

One-time minimized build:

```bash
npm run build
```

## Configuration

| Variable | Purpose | Default/requirement |
| --- | --- | --- |
| `DJANGO_SETTINGS_MODULE` | Settings module | Use `config.settings.development` locally |
| `DJANGO_SECRET_KEY` | Django signing secret | Unsafe development default exists; required securely in production |
| `DJANGO_DEBUG` | Debug mode | `False` in base settings |
| `DJANGO_ALLOWED_HOSTS` | Comma-separated hosts | `127.0.0.1,localhost` |
| `DATABASE_ENGINE` | `sqlite` or `postgres` | `sqlite` |
| `SQLITE_NAME` | SQLite filename | `db.sqlite3` |
| `POSTGRES_DB` | PostgreSQL database | Required for PostgreSQL |
| `POSTGRES_USER` | PostgreSQL user | Required for PostgreSQL |
| `POSTGRES_PASSWORD` | PostgreSQL password | Required for PostgreSQL |
| `POSTGRES_HOST` | PostgreSQL host | `127.0.0.1` |
| `POSTGRES_PORT` | PostgreSQL port | `5432` |
| `RXNORM_API_BASE_URL` | RxNorm REST endpoint | NLM RxNav REST URL |

Base settings enable timezone-aware datetimes and set `TIME_ZONE = "America/Chicago"`.

## Running the application

Run Tailwind in one terminal:

```bash
npm run dev
```

Run Django in another:

```bash
source .venv/bin/activate
python manage.py runserver
```

Open:

- Application: <http://127.0.0.1:8000/>
- Django Admin: <http://127.0.0.1:8000/admin/>
- Patient registry: <http://127.0.0.1:8000/patients/>
- Secure staff messaging: <http://127.0.0.1:8000/secure-chat/>
- Pharmacy: <http://127.0.0.1:8000/pharmacy/>

The development server is not suitable for production.

### PostgreSQL container

The included `docker-compose.yml` starts **only PostgreSQL**; it does not build or run the Django web application.

```bash
docker compose up -d db
docker compose logs -f db
docker compose down
```

The compose file uses development credentials. Change them before any shared or persistent deployment.

## Development workflow

### Before editing

```bash
git status --short
python manage.py check
```

### After Python changes

```bash
ruff format apps config
ruff check apps config
python manage.py check
```

The current repository contains pre-existing Ruff findings in legacy sections of `apps/pharmacy/views.py`; targeted checks are sometimes necessary until that file is consolidated.

### After model changes

```bash
python manage.py makemigrations <app_name>
python manage.py migrate
python manage.py makemigrations --check --dry-run
```

Review generated migrations before applying them, especially migrations that populate clinical or administrative records.

### After template/navigation changes

- Load the full page while authenticated.
- Test HTMX requests separately.
- Check desktop and mobile navigation.
- Verify no patient-specific links appear without an active patient.
- Verify encounter-specific actions disappear after completion.
- Run `python manage.py check`.

### Data integrity practices

- Use `transaction.atomic()` for multi-record state transitions.
- Use `select_for_update()` for stock or other contested balances.
- Preserve the user and timestamp for clinical transitions.
- Do not infer that patient-chart deactivation equals discharge.
- Do not directly edit computed/audit timestamps unless implementing a correction workflow.

## Testing

Run Django checks:

```bash
python manage.py check
python manage.py makemigrations --check --dry-run
```

Run pytest:

```bash
pytest
```

Run one application:

```bash
pytest apps/vitals
pytest apps/pharmacy
python manage.py test apps.messaging.tests
```

Run Django tests directly:

```bash
python manage.py test
python manage.py test apps.pharmacy
```

### Clean test-database behavior

`apps/administration/migrations/0002_populate_appointment_assignments.py` now exits safely when a fresh database contains no appointments. It still requires a valid provider fallback when existing appointment rows actually need provider population. This permits deterministic clean test-database creation without weakening migration behavior for populated databases.

The targeted secure-messaging suite currently contains 15 tests and runs successfully with:

```bash
python manage.py test apps.messaging.tests
```

Coverage includes staff/patient access gates, participant-only conversation access, sending, receiving and polling, sent/received presentation, XSS escaping, unread/read state, specific recipients, all-staff broadcasts, care-team broadcasts, patient links, subject/context categories, compose selectors, and primary-navigation visibility.

### High-risk workflows requiring coverage

- Patient registration, duplicate review, merge, archive, and restoration.
- Encounter state transitions, discharge, cancellation, and entered-in-error.
- Vital validation and correction.
- Medication-order discontinuation and hold/unhold.
- MAR time-window enforcement and next-dose calculation.
- Pharmacy verification, stock locking, dispensing, and ledger creation.
- Clinical-note signing and amendment.
- Facility/patient access control and audit events.
- Secure-message participant isolation, recipient expansion, patient authorization, read receipts, broadcast permissions, and message retention.

## Security and clinical safety

Existing foundations include Django authentication, CSRF middleware, secure cookie settings in non-debug mode, clickjacking protection, password validators, and production HTTPS/HSTS settings.

Secure messaging additionally provides:

- Server-side active-staff and non-patient access checks.
- Participant-filtered conversation and polling querysets that return 404 to outsiders.
- Server-side recipient resolution for specific-user, care-team, and all-staff broadcasts.
- Sender membership validation before message persistence.
- Per-user read receipts and unread queries.
- `Cache-Control: no-store, private` on messaging responses.
- CSRF-protected message creation/reply forms.
- Auto-escaped message bodies and bounded subject/body lengths.
- Superuser-only access to messaging models in Django admin.

Messaging content is **not** end-to-end encrypted and is **not** currently encrypted with a dedicated application-level field key. Database encryption, encrypted backups, transport security, key management, infrastructure access controls, immutable access audit events, retention policy, legal hold, and emergency-access governance remain deployment responsibilities.

These foundations are not a completed healthcare security program. Before production use, implement and verify:

- Explicit role-, facility-, department-, encounter-, and patient-level authorization.
- Permission-gated broadcast creation and patient-care-team membership administration.
- Least privilege and separation of clinical/administrative duties.
- Multi-factor authentication for privileged and remote access.
- Immutable and reviewable access/change audit trails.
- Audit events for search, view, print, export, correction, and override.
- Encrypted transport, encrypted backups, key management, and recovery testing.
- Session timeout, workstation locking, rate limiting, and login monitoring.
- Secure media/document storage and malware scanning.
- Data retention, legal hold, correction, and release-of-information policies.
- Downtime, reconciliation, incident response, and disaster recovery procedures.
- Clinical content governance, medication knowledge maintenance, and alert validation.
- Accessibility and user-acceptance testing with actual clinical roles.

Never commit real patient data, `.env`, credentials, tokens, database exports, private keys, or unencrypted backups.

See [Clinical Safety](clinical-safety.md) and [Permissions](permissions.md).

## Deployment

Production settings enable SSL redirect, secure session/CSRF cookies, and one-year HSTS with subdomains and preload.

A production deployment still requires:

1. PostgreSQL with restricted credentials.
2. A unique secret key stored outside source control.
3. Explicit allowed hosts.
4. HTTPS termination and trusted proxy configuration.
5. `python manage.py collectstatic`.
6. Gunicorn or another production application server.
7. Static/media storage strategy.
8. Database and media backups with tested restoration.
9. Monitoring, error reporting, log retention, and alerting.
10. Capacity, concurrency, failure-mode, and security testing.
11. Clinical validation and controlled release approval.

Example checks:

```bash
DJANGO_SETTINGS_MODULE=config.settings.production python manage.py check --deploy
python manage.py collectstatic --noinput
gunicorn config.wsgi:application
```

The repository currently does not include a complete production Docker image or reverse-proxy configuration. See [Deployment](deployment.md).

## Known limitations

- The project is not certified for clinical production.
- Object-level and facility-level authorization require further systematic enforcement and testing.
- Messaging patient selection and participant membership are enforced, but the project still needs a shared production-grade patient/facility access service applied consistently across every clinical domain.
- Secure messaging uses eight-second polling rather than WebSockets; message delivery is near-real-time, not instantaneous push.
- Secure-message bodies are not end-to-end encrypted or encrypted with a dedicated application-level field key.
- Messaging does not yet support attachments, delivery failure queues, recall, retention automation, legal hold, immutable access auditing, or notification channels outside the application.
- Laboratory and imaging applications are not complete end-to-end workflows.
- The local medication safety screen does not provide a comprehensive interaction database.
- Aggregate medication stock currently lives on the formulary medication while the ledger records movements; multi-location, batch-first inventory is not yet modeled.
- Discharge currently completes an encounter from the nursing discharge assessment; formal discharge-order and disposition governance may require additional role/authorization rules.
- Transfer captures a nursing assessment but does not yet implement bed/unit/facility movement orders.
- Analytics are live operational counts but still require formal metric definitions, denominator governance, facility scoping, missing-data reporting, and validation.
- Decision support has rules/alerts/risk foundations but is not clinically validated; the AI assistant remains a scaffold and is not a clinical tool.
- Background job processing, caching, interoperability APIs, and offline workflows are not implemented.
- `docker-compose.yml` runs PostgreSQL only.
- No `.env.example` is currently committed.
- Legacy duplicate/reference files remain outside installed apps and should be cleaned up deliberately.

## Diagnoses and ICD-10-CM

The diagnoses application provides a patient problem list and encounter-linked diagnosis workflow at `/diagnoses/`. Clinicians can search the locally indexed ICD-10-CM release, record diagnosis type, clinical and verification status, severity, onset/resolution dates, current-problem and sensitive flags, and supporting notes. Recorded terminology is copied into snapshot fields so later code-set updates do not rewrite historical clinical records. Incorrect records are retained for audit and marked **Entered in error** with a required reason rather than deleted.

The development database is loaded with the official April 1, 2026 FY2026 ICD-10-CM code-description release, appropriate for encounters from April 1 through September 30, 2026. Administrators can refresh the index from an official NCHS order file:

```bash
python manage.py import_icd10cm /path/to/icd10cm_order_2026.txt \
  --release "FY2026 April 1, 2026" \
  --format order \
  --deactivate-missing
```

Delimited CSV/TSV imports are also supported; run `python manage.py help import_icd10cm` for column options. Use only the release applicable to the encounter date and follow the official coding guidelines. The local search assists code selection but does not replace clinician documentation, qualified coding review, or payer-specific validation.

Authoritative references:

- [CDC/NCHS ICD-10-CM overview and browser](https://www.cdc.gov/nchs/icd/icd-10-cm/index.html)
- [CDC/NCHS ICD-10-CM release files](https://www.cdc.gov/nchs/icd/icd-10-cm/files.html)
- [CMS ICD-10 files and effective dates](https://www.cms.gov/medicare/coding-billing/icd-10-codes)
- [FY2026 ICD-10-CM Official Guidelines for Coding and Reporting](https://www.cms.gov/files/document/fy-2026-icd-10-cm-coding-guidelines.pdf)

Physician, nurse-practitioner, admission, consultation, progress, SOAP, procedure, and discharge notes can reference the patient's active ICD-10-CM diagnosis records and coded procedures. These are relational links to the problem list—not duplicated free text—so the patient dashboard, diagnosis workspace, encounter, and signed note share the same active-diagnosis source of truth.

### CPT procedure terminology

The diagnoses module also provides patient/encounter procedure records, CPT search, procedure status and performed-date tracking, provider attribution, immutable terminology snapshots, physician-note linkage, and patient-dashboard display. CPT descriptions are not bundled because CPT content is copyrighted by the American Medical Association and requires an appropriate license for electronic use. After obtaining an authorized CPT data file, an administrator may load it with:

```bash
python manage.py import_cpt /path/to/licensed-cpt.csv \
  --release "2026" \
  --acknowledge-license
```

The default columns are `code`, `description`, and `category`; run `python manage.py help import_cpt` for alternate column and delimiter options. The acknowledgement confirms authorization but does not itself grant a license.

- [AMA CPT licensing FAQ](https://www.ama-assn.org/practice-management/cpt/cpt-licensing-frequently-asked-questions-faqs)
- [CMS overview of HCPCS Level I CPT and Level II](https://www.cms.gov/medicare/coding-billing/healthcare-common-procedure-system)

## Roadmap

The next work should complete navbar areas in dependency order rather than adding disconnected screens.

### 1. Foundation hardening

- Add repeatable seed/reference-data commands.
- Complete role/facility/patient permission services.
- Expand immutable audit logging.
- Add `.env.example` and production deployment manifests.
- Consolidate duplicate/legacy code and existing Ruff findings.

### 2. Encounter movement and inpatient operations

- Formal admission order and bed assignment.
- Transfer order with origin, destination, accepting service/provider, timestamps, and bed movement.
- Discharge order, medication reconciliation, diagnoses, disposition, instructions, follow-up, and summary.
- Census and bed-board integration.

### 3. Laboratory

- Catalog/tests, order entry, collection, accession, specimen status, results, reference ranges, verification, critical result communication, amendments, and patient/encounter display.

### 4. Imaging

- Order entry, modality/work queue, scheduling, study status, report drafting/signing, critical findings, and result display.

### 5. Nursing and flowsheets

- Care plans, interventions, goals, structured flowsheets, wound assessment, device management, shift worklists, escalation, and validated acuity indicators.

### 6. Medication and pharmacy maturity

- Multi-location inventory, lots/batches, expiration-first selection, receipts, transfers, returns, waste witnesses, controlled-drug registers, dispense labels, partial fills, and formulary approval governance.
- Maintained drug knowledge integration for interactions, renal/hepatic dosing, duplicate therapy, contraindications, and monitoring.

### 7. Care management, documents, and notifications

- Referrals, discharge planning, social needs, patient education, document upload/classification, task routing, non-message system notifications, and follow-up reminders.
- Mature secure messaging with permission-gated broadcasts, facility/patient access integration, immutable access audit events, retention/legal-hold policy, optional attachments with malware scanning, and evaluated real-time delivery infrastructure.

### 8. Billing and revenue cycle

- Coverage verification, charge capture, coding, claims, payments, adjustments, remittance, and audit controls.

### 9. Analytics and reporting

- Governed metric catalog, facility filters, data-quality indicators, validated dashboards, exports, scheduled reports, and public-health reporting.

### 10. Interoperability and patient access

- FHIR-compatible resources/APIs, terminology governance, external identity matching, consent-aware exchange, patient portal, and governed patient-facing communication distinct from internal staff messaging.

### 11. Decision support and AI

- Versioned deterministic rules first.
- Clinical ownership, evidence, validation, alert lifecycle, acknowledgment, override reason, and monitoring.
- Only then governed AI summarization/assistance with provenance, human approval, model/version capture, and PHI controls.

## Documentation

- [Project requirements](requirements.md)
- [System architecture](architecture.md)
- [Application and web map](web-map.md)
- [Application dependencies and relationships](application-dependencies.md)
- [HTMX full pages and partials](htmx-rendering.md)
- [Clinical safety](clinical-safety.md)
- [Database](database.md)
- [Deployment](deployment.md)
- [Permissions](permissions.md)

Pictorial SVG assets are stored in [`diagrams/`](diagrams/). Mermaid source remains beside each diagram in the relevant document so relationships can be reviewed and updated without a graphics editor.

Treat documentation as part of the implementation. A change to requirements, domain ownership, page/partial behavior, safety assumptions, data storage, deployment, or authorization should update the relevant document in the same change.

## Contribution expectations

- Keep changes scoped and clinically explainable.
- Add tests proportional to patient-safety and data-integrity risk.
- Use named URLs and application namespaces.
- Keep HTMX responses as reusable server-rendered partials.
- Use Alpine.js for presentation state, not authoritative clinical state.
- Preserve patient and encounter context in clinical workflows.
- Document new environment variables, migrations, permissions, and clinical rules.
- Never use real patient information in fixtures, screenshots, commits, or issue reports.

## License

No license file is currently present. Until the project owner selects and adds a license, all rights are reserved.

## Clinical disclaimer

Liberia EHR is a software-development project. It is not a medical device, a substitute for professional judgment, an emergency service, or a validated production medical record system. Clinical users remain responsible for verifying patient identity, orders, results, medication safety, documentation, and disposition. Real-world deployment requires clinical governance, legal review, privacy/security assessment, validation, training, controlled rollout, monitoring, and tested downtime/recovery procedures.
