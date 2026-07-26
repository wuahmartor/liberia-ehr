#!/usr/bin/env python3
"""
Apply compact layout changes to the Liberia EHR project in one run.

Run this file from the project root (same folder as manage.py):

    python compact_ehr_layout.py

Or pass the project path:

    python compact_ehr_layout.py /full/path/to/liberia_ehr

The script:
- creates timestamped backups
- compacts navigation bars
- reduces sidebar width
- reduces workspace padding
- compacts dashboard cards
- compacts AI/CDS cards
- compacts the clinical overview page
- updates Tailwind component classes
"""

from __future__ import annotations

import shutil
import sys
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = (
    Path(sys.argv[1]).expanduser().resolve()
    if len(sys.argv) > 1
    else Path.cwd().resolve()
)

if not (PROJECT_ROOT / "manage.py").exists():
    raise SystemExit(
        "\nERROR: manage.py was not found.\n"
        f"Project path checked: {PROJECT_ROOT}\n\n"
        "Run this script from the Liberia EHR project root,\n"
        "or pass the project folder as the first argument.\n"
    )

BACKUP_ROOT = (
    PROJECT_ROOT
    / ".layout_backups"
    / datetime.now().strftime("%Y%m%d_%H%M%S")
)

changed_files: list[Path] = []
warnings: list[str] = []


def locate(*candidates: str) -> Path | None:
    for candidate in candidates:
        path = PROJECT_ROOT / candidate
        if path.exists():
            return path
    return None


def backup(path: Path) -> None:
    relative = path.relative_to(PROJECT_ROOT)
    destination = BACKUP_ROOT / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, destination)


def replace_many(
    path: Path | None,
    replacements: list[tuple[str, str]],
    label: str,
) -> None:
    if path is None:
        warnings.append(f"{label}: file not found")
        return

    original = path.read_text(encoding="utf-8")
    updated = original
    missing = 0

    for old, new in replacements:
        if old in updated:
            updated = updated.replace(old, new)
        else:
            missing += 1

    if updated == original:
        warnings.append(f"{label}: no matching patterns changed")
        return

    backup(path)
    path.write_text(updated, encoding="utf-8")
    changed_files.append(path)

    if missing:
        warnings.append(
            f"{label}: {missing} optional replacement pattern(s) were not found"
        )


def overwrite(path: Path | None, content: str, label: str) -> None:
    if path is None:
        warnings.append(f"{label}: file not found")
        return

    new_content = content.strip() + "\n"
    old_content = path.read_text(encoding="utf-8")

    if old_content == new_content:
        return

    backup(path)
    path.write_text(new_content, encoding="utf-8")
    changed_files.append(path)


# ------------------------------------------------------------------
# Tailwind CSS
# ------------------------------------------------------------------

css_path = locate("static/src/css/input.css")

compact_css = """
@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {
    html {
        font-size: 14px;
    }

    body {
        @apply antialiased;
    }

    input,
    select,
    textarea,
    button {
        @apply text-sm;
    }
}

@layer components {
    .panel {
        @apply rounded-lg border border-slate-200 bg-white shadow-sm;
    }

    .primary-nav-link {
        @apply rounded-md px-2.5 py-1.5 text-xs font-medium
               text-white/85 transition
               hover:bg-white/10 hover:text-white;
    }

    .primary-nav-link-active {
        @apply bg-white/10 text-white;
    }

    .secondary-nav-link {
        @apply rounded-md px-2 py-1.5 text-xs font-medium
               text-slate-600 transition
               hover:bg-ehr-50 hover:text-ehr-800;
    }

    .patient-nav-link {
        @apply flex items-center gap-2 rounded-md px-2.5 py-1.5
               text-xs font-medium text-white/80 transition
               hover:bg-white/10 hover:text-white;
    }

    .patient-nav-link-active {
        @apply bg-white text-ehr-900 shadow-sm
               hover:bg-white hover:text-ehr-900;
    }

    .dashboard-card {
        @apply rounded-lg border border-slate-200 bg-white p-3 shadow-sm;
    }

    .dashboard-card-icon {
        @apply grid h-8 w-8 shrink-0 place-items-center rounded-md
               bg-ehr-50 text-base text-ehr-700;
    }

    .dashboard-card-label {
        @apply text-[11px] font-medium uppercase tracking-wide text-slate-500;
    }

    .dashboard-card-value {
        @apply mt-0.5 text-base font-semibold text-slate-900;
    }

    .workspace-panel {
        @apply rounded-lg border border-slate-200 bg-white p-4 shadow-sm;
    }

    .btn-primary {
        @apply inline-flex items-center justify-center rounded-md
               bg-ehr-800 px-3 py-1.5 text-xs font-semibold text-white
               transition hover:bg-ehr-900;
    }

    .btn-secondary {
        @apply inline-flex items-center justify-center rounded-md
               border border-slate-300 bg-white px-3 py-1.5
               text-xs font-semibold text-slate-700
               transition hover:bg-slate-50;
    }

    .form-control-compact {
        @apply rounded-md border-slate-300 px-2.5 py-1.5 text-xs
               focus:border-ehr-500 focus:ring-ehr-500;
    }
}

.htmx-indicator {
    display: none;
}

.htmx-request .htmx-indicator,
.htmx-request.htmx-indicator {
    display: block;
}
"""

overwrite(css_path, compact_css, "Tailwind input CSS")


# ------------------------------------------------------------------
# Application shell
# ------------------------------------------------------------------

app_shell = locate(
    "templates/layouts/app_shell.html",
    "apps/core/templates/layouts/app_shell.html",
)

replace_many(
    app_shell,
    [
        (
            "lg:grid-cols-[17rem_minmax(0,1fr)]",
            "lg:grid-cols-[14rem_minmax(0,1fr)]",
        ),
        (
            "bg-slate-50 p-4 md:p-6",
            "bg-slate-50 p-3 md:p-4",
        ),
    ],
    "Application shell",
)


# ------------------------------------------------------------------
# Primary navigation
# ------------------------------------------------------------------

primary_nav = locate("templates/components/primary_nav.html")

replace_many(
    primary_nav,
    [
        (
            "flex min-h-16 items-center gap-3 px-4 lg:px-5",
            "flex h-12 items-center gap-2 px-3 lg:px-4",
        ),
        (
            "grid h-8 w-8 place-items-center rounded-lg",
            "grid h-7 w-7 place-items-center rounded-md",
        ),
        (
            "grid h-9 w-9 place-items-center rounded-full",
            "grid h-7 w-7 place-items-center rounded-full",
        ),
        (
            "block text-sm font-semibold",
            "block text-xs font-semibold",
        ),
        (
            "block text-xs text-white/70",
            "block text-[10px] text-white/70",
        ),
        (
            "flex items-center gap-2 rounded-lg px-2 py-1",
            "flex items-center gap-1.5 rounded-md px-1.5 py-1",
        ),
    ],
    "Primary navigation",
)


# ------------------------------------------------------------------
# Secondary navigation
# ------------------------------------------------------------------

secondary_nav = locate("templates/components/secondary_nav.html")

replace_many(
    secondary_nav,
    [
        (
            "flex min-h-14 items-center gap-3 overflow-x-auto px-4 lg:px-5",
            "flex h-11 items-center gap-2 overflow-x-auto px-3 lg:px-4",
        ),
        (
            "relative min-w-[19rem] max-w-md flex-1",
            "relative min-w-[15rem] max-w-sm flex-1",
        ),
        (
            "w-full rounded-lg border-slate-200 py-2 pl-10 pr-3 text-sm",
            "w-full rounded-md border-slate-200 py-1.5 pl-8 pr-2.5 text-xs",
        ),
        (
            "absolute left-3 top-2.5 text-slate-400",
            "absolute left-2.5 top-2 text-slate-400",
        ),
        (
            "absolute left-0 right-0 top-12 z-40",
            "absolute left-0 right-0 top-10 z-40",
        ),
    ],
    "Secondary navigation",
)


# ------------------------------------------------------------------
# Patient sidebar
# ------------------------------------------------------------------

patient_sidebar = locate("templates/components/patient_sidebar.html")

replace_many(
    patient_sidebar,
    [
        ('<div class="p-4">', '<div class="p-3">'),
        (
            "border-b border-white/15 pb-5",
            "border-b border-white/15 pb-3",
        ),
        (
            "h-16 w-16 shrink-0",
            "h-11 w-11 shrink-0",
        ),
        (
            "rounded-full border-4",
            "rounded-full border-2",
        ),
        (
            "truncate text-lg font-bold",
            "truncate text-sm font-bold",
        ),
        (
            "text-sm font-semibold text-white/90",
            "text-[11px] font-semibold text-white/90",
        ),
        (
            "mt-1 text-xs leading-5 text-white/75",
            "mt-0.5 text-[10px] leading-4 text-white/75",
        ),
        (
            "mt-4 space-y-1",
            "mt-3 space-y-0.5",
        ),
        (
            "flex items-start gap-3",
            "flex items-start gap-2.5",
        ),
    ],
    "Patient sidebar",
)


# ------------------------------------------------------------------
# Summary cards
# ------------------------------------------------------------------

summary_card = locate("templates/components/summary_card.html")

compact_summary_card = """
<article class="dashboard-card flex min-h-16 items-center gap-3">
    <div class="dashboard-card-icon">
        {{ icon }}
    </div>

    <div class="min-w-0">
        <p class="dashboard-card-label">
            {{ label }}
        </p>

        <p class="dashboard-card-value truncate">
            {{ value }}
        </p>
    </div>
</article>
"""

overwrite(summary_card, compact_summary_card, "Summary card")


# ------------------------------------------------------------------
# AI/CDS alert cards
# ------------------------------------------------------------------

cds_alert = locate("templates/components/cds_alert.html")

compact_cds_alert = """
<article class="rounded-lg border border-slate-200 bg-white p-3 shadow-sm">
    <div class="flex gap-2.5">
        <div class="mt-0.5 text-base {{ icon_class }}">
            {{ icon }}
        </div>

        <div class="min-w-0">
            <h3 class="text-xs font-semibold text-slate-900">
                {{ title }}
            </h3>

            <p class="mt-1 text-[11px] leading-4 text-slate-600">
                {{ message }}
            </p>

            {% if action_label %}
                <button
                    type="button"
                    class="btn-secondary mt-2"
                >
                    {{ action_label }}
                </button>
            {% endif %}
        </div>
    </div>
</article>
"""

overwrite(cds_alert, compact_cds_alert, "Clinical decision-support alert")


# ------------------------------------------------------------------
# Clinical overview page
# ------------------------------------------------------------------

clinical_overview = locate(
    "apps/core/templates/core/clinical_overview.html",
    "templates/dashboard/clinical_overview.html",
    "templates/core/clinical_overview.html",
)

replace_many(
    clinical_overview,
    [
        (
            'class="mx-auto max-w-[1600px]"',
            'class="mx-auto max-w-[1450px]"',
        ),
        (
            "mb-5 flex flex-wrap items-center justify-between gap-3",
            "mb-3 flex flex-wrap items-center justify-between gap-2",
        ),
        (
            "text-2xl font-bold tracking-tight text-ehr-950",
            "text-lg font-bold tracking-tight text-ehr-950",
        ),
        (
            "mt-1 text-sm text-slate-500",
            "mt-0.5 text-xs text-slate-500",
        ),
        (
            "rounded-lg border-slate-200 bg-white text-sm font-medium",
            "form-control-compact bg-white font-medium",
        ),
        (
            "grid gap-4 sm:grid-cols-2 xl:grid-cols-5",
            "grid gap-2.5 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5",
        ),
        (
            "mt-5 grid gap-5 xl:grid-cols-[minmax(0,1.2fr)_minmax(22rem,0.8fr)]",
            "mt-3 grid gap-3 xl:grid-cols-[minmax(0,1.35fr)_minmax(19rem,0.65fr)]",
        ),
        (
            'class="panel min-h-[25rem] p-5"',
            'class="workspace-panel min-h-[19rem]"',
        ),
        (
            "text-lg font-semibold text-slate-900",
            "text-sm font-semibold text-slate-900",
        ),
        (
            "text-sm text-slate-500",
            "text-[11px] text-slate-500",
        ),
        (
            "flex gap-4 text-sm",
            "flex gap-3 text-[11px]",
        ),
        (
            "mt-8 grid h-64 place-items-center rounded-xl",
            "mt-4 grid h-48 place-items-center rounded-lg",
        ),
        (
            "font-semibold text-slate-600",
            "text-xs font-semibold text-slate-600",
        ),
        (
            "mt-1 text-sm text-slate-400",
            "mt-1 text-[11px] text-slate-400",
        ),
        (
            "text-lg font-semibold text-ehr-950",
            "text-sm font-semibold text-ehr-950",
        ),
        (
            'class="space-y-4"',
            'class="space-y-2.5"',
        ),
        (
            'class="mb-3"',
            'class="mb-2"',
        ),
    ],
    "Clinical overview dashboard",
)


print("\nCompact EHR layout changes completed.\n")

if changed_files:
    print("Changed files:")
    for file in changed_files:
        print(f"  - {file.relative_to(PROJECT_ROOT)}")
else:
    print("No files were changed.")

print(f"\nBackups saved to:\n  {BACKUP_ROOT}")

if warnings:
    print("\nWarnings:")
    for warning in warnings:
        print(f"  - {warning}")

print(
    "\nNext steps:\n"
    "  npm run build\n"
    "  python manage.py runserver\n"
    "\nThen hard-refresh the browser with Command + Shift + R.\n"
)
