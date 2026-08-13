import csv
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.diagnoses.models import ProcedureCode, TerminologySource


class Command(BaseCommand):
    help = "Import an AMA-authorized CPT data file. This command does not grant a CPT license."

    def add_arguments(self, parser):
        parser.add_argument("file", type=Path)
        parser.add_argument("--release", required=True)
        parser.add_argument("--delimiter", choices=("comma", "tab"), default="comma")
        parser.add_argument("--code-column", default="code")
        parser.add_argument("--title-column", default="description")
        parser.add_argument("--category-column", default="category")
        parser.add_argument(
            "--acknowledge-license",
            action="store_true",
            help="Confirm the organization is authorized to load and display this CPT content.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        if not options["acknowledge_license"]:
            raise CommandError(
                "CPT content is copyrighted by the AMA. Re-run only after confirming "
                "your organization's license with --acknowledge-license."
            )
        source_file = options["file"]
        if not source_file.is_file():
            raise CommandError(f"File not found: {source_file}")
        source, _ = TerminologySource.objects.update_or_create(
            name="CPT",
            defaults={
                "source_type": TerminologySource.SourceType.CPT,
                "organization": "American Medical Association",
                "release_version": options["release"],
                "canonical_url": "https://www.ama-assn.org/practice-management/cpt",
                "is_active": True,
                "requires_license": True,
            },
        )
        delimiter = "," if options["delimiter"] == "comma" else "\t"
        with source_file.open(encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle, delimiter=delimiter)
            required = {options["code_column"], options["title_column"]}
            if not reader.fieldnames or not required.issubset(reader.fieldnames):
                raise CommandError(f"Missing required columns: {sorted(required)}")
            parsed = []
            for row in reader:
                code = row.get(options["code_column"], "").strip()
                title = row.get(options["title_column"], "").strip()
                if code and title:
                    parsed.append(
                        (
                            code,
                            title,
                            row.get(options["category_column"], "").strip(),
                        )
                    )
        existing = {
            item.code: item for item in ProcedureCode.objects.filter(source=source)
        }
        creates = []
        updates = []
        for code, title, category in parsed:
            item = existing.get(code)
            if item is None:
                creates.append(
                    ProcedureCode(
                        source=source,
                        code_system=ProcedureCode.CodeSystem.CPT,
                        code=code,
                        title=title,
                        category=category,
                        is_active=True,
                    )
                )
            else:
                item.title = title
                item.category = category
                item.is_active = True
                updates.append(item)
        ProcedureCode.objects.bulk_create(creates, batch_size=1000)
        ProcedureCode.objects.bulk_update(
            updates, ["title", "category", "is_active"], batch_size=1000
        )
        source.last_synchronized_at = timezone.now()
        source.save(update_fields=["last_synchronized_at", "updated_at"])
        self.stdout.write(
            self.style.SUCCESS(
                f"CPT {options['release']}: {len(creates)} created, {len(updates)} updated."
            )
        )
