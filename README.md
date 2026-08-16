# Liberia EHR

Liberia EHR is a modular, server-rendered electronic health record built with Django, HTMX, Alpine.js, and Tailwind CSS.

Current clinical workflow highlights include compact drag/drop care-team assignment, editable multi-patient care teams, a cross-patient hourly Shift MAR, and a patient MAR with shift/custom-range filtering and recurring due-time expansion.

> [!WARNING]
> This project is under active development and is not certified or validated for production clinical use. Do not load real protected health information until the required security, privacy, clinical-safety, backup, recovery, and regulatory reviews are complete.

## Project documentation

The comprehensive project handbook is maintained in [`docs/README.md`](docs/README.md).

- [Full project handbook](docs/README.md)
- [Application and web map](docs/web-map.md)
- [Project requirements](docs/requirements.md)
- [System architecture](docs/architecture.md)
- [Application dependencies](docs/application-dependencies.md)
- [HTMX full pages and partials](docs/htmx-rendering.md)
- [Database architecture](docs/database.md)
- [Permissions](docs/permissions.md)
- [Clinical safety](docs/clinical-safety.md)
- [Deployment](docs/deployment.md)

## Visual overview

[![Liberia EHR application and web sitemap](docs/diagrams/application-sitemap.svg)](docs/diagrams/application-sitemap.svg)

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements/development.txt
python manage.py migrate
python manage.py runserver
```

See the [full installation, configuration, testing, and operational guide](docs/README.md#installation) for complete instructions.
