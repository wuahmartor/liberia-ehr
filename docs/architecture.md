# System architecture

This document describes the implemented architecture of Liberia EHR. It is a developer guide, not a clinical certification or production-readiness claim. See [requirements.md](requirements.md) for requirement status and [htmx-rendering.md](htmx-rendering.md) for the rendering contract.

## Architectural goals

- Keep clinical state and authorization on the Django server.
- Preserve a longitudinal patient record across many encounters.
- Separate ordering, verification, dispensing, and administration records.
- Prefer auditable lifecycle transitions over destructive deletion.
- Deliver a compact interface with server-rendered HTML and targeted HTMX updates.
- Keep domain applications independently understandable while using explicit cross-app relationships.

## System context

```mermaid
flowchart LR
    Staff["Clinical and administrative staff"] -->|"HTTPS browser session"| EHR["Liberia EHR"]
    Admin["System administrator"] -->|"Users, groups, facilities"| EHR
    EHR --> DB[("SQLite development / PostgreSQL production")]
    EHR --> Static["WhiteNoise static assets"]
    EHR -. "future integration boundary" .-> External["Laboratory, imaging, pharmacy and identity systems"]
    EHR -. "optional production telemetry" .-> Monitor["Sentry-compatible monitoring"]
```

External clinical integrations are not complete. The dotted connections identify boundaries, not active interfaces.

## Runtime containers

```mermaid
flowchart TB
    Browser["Browser: HTML, HTMX, Alpine.js, Tailwind"]
    URLs["Django URL dispatcher"]
    Auth["Authentication, middleware and decorators"]
    Views["Views and forms"]
    Services["Domain services and selectors"]
    Models["Django ORM models"]
    DB[("Relational database")]

    Browser -->|"full GET, HTMX GET/POST, JSON polling"| URLs
    URLs --> Auth --> Views
    Views --> Services
    Views --> Models
    Services --> Models --> DB
    Views -->|"full page or HTML fragment"| Browser
```

The application is a modular monolith. All Django apps run in one process and share one relational database. App boundaries organize ownership; they are not network-service boundaries.

## Application layers

[![Liberia EHR application layers and dependencies](diagrams/app-dependencies.svg)](diagrams/app-dependencies.svg)

```mermaid
flowchart TB
    Experience["Experience: core, analytics, administration"]
    Workflow["Clinical workflow: encounters, nursing, vitals, diagnoses, clinical_notes, orders, medications, pharmacy, messaging, decision_support"]
    Record["Foundational record: accounts, facilities, patients"]
    Platform["Platform/scaffold: audit, notifications, documents, flowsheets, laboratories, imaging, care_management, ai_assistant"]

    Experience --> Workflow
    Experience --> Record
    Workflow --> Record
    Workflow --> Platform
```

Dependencies should generally point downward. `core` and `analytics` deliberately read across workflow apps to build dashboards. `nursing` creates decision-support records, so that workflow has an explicit cross-domain dependency documented in [application-dependencies.md](application-dependencies.md).

## Request and rendering lifecycle

```mermaid
sequenceDiagram
    actor User
    participant Browser
    participant Middleware
    participant View
    participant ORM
    participant Template

    User->>Browser: Open page or activate HTMX control
    Browser->>Middleware: Session, CSRF and optional HX-Request
    Middleware->>Middleware: Authenticate and enforce session policy
    Middleware->>View: Authorized request
    View->>ORM: Select or mutate scoped records
    ORM-->>View: Domain objects
    View->>Template: Full template or partial template
    Template-->>Browser: HTML response
    Browser->>Browser: Navigate document or swap target
```

For a normal request, the response includes the complete application shell. For `HX-Request: true`, participating views return only the fragment intended for the declared target. Both paths execute the same authentication, authorization, validation, and domain logic.

## Shared presentation shell

```mermaid
flowchart TD
    Base["templates/base.html: assets and document"]
    Shell["templates/layouts/app_shell.html: navigation and sidebar"]
    Page["App full-page template: workspace metadata"]
    Partial["App partial template: replaceable content"]
    Base --> Shell --> Page --> Partial
```

Full templates extend the shell and normally include the corresponding partial. A partial must be independently renderable inside its HTMX target and must not extend `base.html` or duplicate the navigation chrome.

## Domain boundaries and ownership

| App | Owns | Important consumers |
| --- | --- | --- |
| `accounts` | Staff profile and role metadata | encounters, administration, messaging, core |
| `facilities` | Facility, department, unit, room, and bed hierarchy | encounters, scheduling, administration |
| `patients` | Longitudinal identity and demographics | every patient-centered workflow |
| `encounters` | Episode of care, status, timing, provider, location | nursing, vitals, notes, diagnoses, orders |
| `orders` | Provider medication authorization | pharmacy, MAR, patient overview |
| `pharmacy` | Medication catalog, review, dispense, inventory | orders, MAR, dashboard |
| `medications` | Medication administration record | dashboard and patient views |
| `messaging` | Conversations, patient context, messages, read receipts | primary-navigation unread indicator |
| `decision_support` | Rules, alerts, recommendations, risk outputs | nursing and patient-facing clinical views |

The full app catalog and hard-import graph are in [application-dependencies.md](application-dependencies.md).

## Data and transaction principles

- Use timezone-aware timestamps and render them in the configured local timezone.
- Use database transactions for multi-record changes such as conversation creation and inventory decrement.
- Retain clinical history through status, amendment, void, archive, discontinue, or entered-in-error workflows.
- Treat foreign keys as integrity relationships, not sufficient authorization; views and services still scope accessible objects.
- Optimize cross-app read models with bounded queries before introducing a separate service.

See [database.md](database.md) for relationship diagrams and operational conventions.

## Security boundaries

1. The authenticated session identifies the user.
2. Middleware and decorators enforce broad access requirements.
3. Views and services enforce resource scope, participant membership, role, and workflow rules.
4. Forms validate user-supplied transitions and references.
5. CSRF protection covers state-changing browser requests.
6. Production transport must use HTTPS and secure cookies.

Hiding a link, button, sidebar item, or Alpine.js panel is presentation logic and is never an authorization control.

## Constraints and open work

- Unread messaging uses polling, so interval and query load need review at production scale.
- Several installed applications remain scaffolds and must not be presented as complete workflows.
- Object-level patient authorization needs a consistent service shared by all clinical apps.
- Laboratory, imaging, document, flowsheet, and interoperability boundaries require further design.
- Production readiness requires threat modeling, clinical validation, recovery testing, observability, and load testing.

## Related documentation

- [Project requirements](requirements.md)
- [Application dependencies](application-dependencies.md)
- [Application and web map](web-map.md)
- [HTMX rendering](htmx-rendering.md)
- [Database](database.md)
- [Permissions](permissions.md)
- [Clinical safety](clinical-safety.md)
- [Deployment](deployment.md)
