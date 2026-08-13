import csv
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.diagnoses.models import ClinicalConcept, TerminologySource


def format_icd10cm_code(value):
    """Add the standard decimal after the third character when omitted."""
    value = value.strip().upper().replace(".", "")
    return f"{value[:3]}.{value[3:]}" if len(value) > 3 else value


class Command(BaseCommand):
    help = "Import an official ICD-10-CM code-description CSV/TSV into the local terminology index."

    def add_arguments(self, parser):
        parser.add_argument("file", type=Path)
        parser.add_argument(
            "--release", required=True, help="Release label, for example FY2026"
        )
        parser.add_argument("--delimiter", choices=("comma", "tab"), default="tab")
        parser.add_argument(
            "--format",
            choices=("delimited", "order"),
            default="delimited",
            help="Use 'order' for the official fixed-width code descriptions/order text file.",
        )
        parser.add_argument("--code-column", default="code")
        parser.add_argument("--title-column", default="description")
        parser.add_argument("--billable-column", default="billable")
        parser.add_argument("--deactivate-missing", action="store_true")

    @transaction.atomic
    def handle(self, *args, **options):
        source_file = options["file"]
        if not source_file.is_file():
            raise CommandError(f"File not found: {source_file}")
        source, _ = TerminologySource.objects.update_or_create(
            name="ICD-10-CM",
            defaults={
                "source_type": TerminologySource.SourceType.ICD_10,
                "organization": "CDC/NCHS",
                "release_version": options["release"],
                "canonical_url": "https://www.cdc.gov/nchs/icd/icd-10-cm/files.html",
                "language": "en",
                "is_active": True,
                "requires_license": False,
            },
        )
        seen = set()
        skipped = 0
        delimiter = "," if options["delimiter"] == "comma" else "\t"
        with source_file.open(encoding="utf-8-sig", newline="") as handle:
            if options["format"] == "order":
                # NCHS order layout: sequence(5), code(7), header flag(1),
                # short description(60), long description(remainder).
                rows = (
                    {
                        "code": line[6:13].strip(),
                        "description": line[77:].strip() or line[16:76].strip(),
                        "billable": "false" if line[14:15] == "0" else "true",
                    }
                    for line in handle
                    if line.strip()
                )
            else:
                reader = csv.DictReader(handle, delimiter=delimiter)
                required = {options["code_column"], options["title_column"]}
                if not reader.fieldnames or not required.issubset(reader.fieldnames):
                    raise CommandError(
                        f"Required columns missing. Expected {sorted(required)}; found {reader.fieldnames or []}"
                    )
                rows = reader
            parsed = []
            for row in rows:
                code = format_icd10cm_code(
                    row.get(
                        "code"
                        if options["format"] == "order"
                        else options["code_column"],
                        "",
                    )
                )
                title = row.get(
                    "description"
                    if options["format"] == "order"
                    else options["title_column"],
                    "",
                ).strip()
                if not code or not title:
                    skipped += 1
                    continue
                seen.add(code)
                billable_raw = (
                    row.get(
                        "billable"
                        if options["format"] == "order"
                        else options["billable_column"],
                        "",
                    )
                    .strip()
                    .lower()
                )
                parsed.append((code, title, billable_raw in {"1", "true", "yes", "y"}))
        existing = {
            item.code: item for item in ClinicalConcept.objects.filter(source=source)
        }
        to_create = []
        to_update = []
        for code, title, billable in parsed:
            item = existing.get(code)
            if item is None:
                to_create.append(
                    ClinicalConcept(
                        source=source,
                        code=code,
                        title=title,
                        fully_specified_name=title,
                        concept_kind=ClinicalConcept.ConceptKind.OTHER,
                        is_leaf=billable,
                        is_billable=billable,
                        is_active=True,
                        source_payload={"release": options["release"]},
                    )
                )
            else:
                item.title = title
                item.fully_specified_name = title
                item.is_leaf = billable
                item.is_billable = billable
                item.is_active = True
                item.source_payload = {"release": options["release"]}
                to_update.append(item)
        if options["deactivate_missing"]:
            for code, item in existing.items():
                if code not in seen:
                    item.is_active = False
                    to_update.append(item)
        ClinicalConcept.objects.bulk_create(to_create, batch_size=1000)
        ClinicalConcept.objects.bulk_update(
            to_update,
            [
                "title",
                "fully_specified_name",
                "is_leaf",
                "is_billable",
                "is_active",
                "source_payload",
            ],
            batch_size=1000,
        )
        source.last_synchronized_at = timezone.now()
        source.save(update_fields=["last_synchronized_at", "updated_at"])
        self.stdout.write(
            self.style.SUCCESS(
                f"ICD-10-CM {options['release']}: {len(to_create)} created, {len(to_update)} updated, {skipped} skipped."
            )
        )
