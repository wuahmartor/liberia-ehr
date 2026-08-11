from __future__ import annotations

import csv
import logging
import re
import tempfile
import urllib.request
import zipfile

from pathlib import Path
from typing import Any

from django.contrib.auth import get_user_model
from django.core.management.base import (
    BaseCommand,
    CommandError,
)
from django.db import transaction

from apps.pharmacy.models import Medication


logger = logging.getLogger(__name__)


# ============================================================
# RXNORM CURRENT PRESCRIBABLE CONTENT
# ============================================================

RXNORM_CURRENT_PRESCRIBABLE_URL = (
    "https://download.nlm.nih.gov/rxnorm/"
    "RxNorm_full_prescribe_08032026.zip"
)


# ============================================================
# IMPORT POLICY
# ============================================================

# Provider-facing drug products only.
#
# SCD = Semantic Clinical Drug
# SBD = Semantic Branded Drug

IMPORT_TERM_TYPES = {
    "SCD",
    "SBD",
}


# ============================================================
# RXNCONSO.RRF COLUMN POSITIONS
# ============================================================

RXCUI_INDEX = 0
SAB_INDEX = 11
TTY_INDEX = 12
STR_INDEX = 14
SUPPRESS_INDEX = 16


# ============================================================
# BULK SETTINGS
# ============================================================

BULK_BATCH_SIZE = 1000


class Command(BaseCommand):
    """
    Synchronize RxNorm Current Prescribable Content into the
    local pharmacy.Medication table.

    Normal provider medication ordering should search the
    local Medication table instead of calling RxNorm live.
    """

    help = (
        "Download and synchronize RxNorm Current Prescribable "
        "Content into the local medication database."
    )


    # ========================================================
    # ARGUMENTS
    # ========================================================

    def add_arguments(
        self,
        parser,
    ) -> None:

        parser.add_argument(
            "--zip",
            dest="zip_path",
            default="",
            help=(
                "Optional local RxNorm Prescribable Content "
                "ZIP file. If omitted, the current official "
                "NLM release is downloaded."
            ),
        )

        parser.add_argument(
            "--user",
            dest="username",
            default="",
            help=(
                "Username to use for created_by / updated_by."
            ),
        )

        parser.add_argument(
            "--limit",
            dest="limit",
            type=int,
            default=0,
            help=(
                "Maximum number of products to process. "
                "Use 0 for all."
            ),
        )

        parser.add_argument(
            "--dry-run",
            action="store_true",
            dest="dry_run",
            help=(
                "Parse and display records without saving."
            ),
        )


    # ========================================================
    # MAIN
    # ========================================================

    def handle(
        self,
        *args,
        **options,
    ) -> None:

        zip_path = (
            options.get(
                "zip_path",
                "",
            )
            .strip()
        )

        username = (
            options.get(
                "username",
                "",
            )
            .strip()
        )

        limit = int(
            options.get(
                "limit",
                0,
            )
            or 0
        )

        dry_run = bool(
            options.get(
                "dry_run",
                False,
            )
        )


        audit_user = (
            self._get_audit_user(
                username
            )
        )


        self.stdout.write(
            self.style.NOTICE(
                "Starting RxNorm medication synchronization..."
            )
        )


        temporary_directory = None


        try:

            # =================================================
            # ARCHIVE SOURCE
            # =================================================

            if zip_path:

                archive_path = (
                    Path(zip_path)
                    .expanduser()
                    .resolve()
                )


                if not archive_path.exists():

                    raise CommandError(
                        (
                            "RxNorm ZIP file does not exist: "
                            f"{archive_path}"
                        )
                    )


            else:

                temporary_directory = (
                    tempfile.TemporaryDirectory()
                )


                archive_path = (
                    Path(
                        temporary_directory.name
                    )
                    / "rxnorm_prescribable.zip"
                )


                self.stdout.write(
                    (
                        "Downloading current RxNorm "
                        "Prescribable Content:"
                    )
                )

                self.stdout.write(
                    RXNORM_CURRENT_PRESCRIBABLE_URL
                )


                self._download_file(
                    url=RXNORM_CURRENT_PRESCRIBABLE_URL,
                    destination=archive_path,
                )


            self.stdout.write(
                f"Archive: {archive_path}"
            )


            # =================================================
            # EXTRACT
            # =================================================

            conso_file = (
                self._extract_rxnconso(
                    archive_path
                )
            )


            self.stdout.write(
                f"Reading: {conso_file}"
            )


            # =================================================
            # PARSE
            # =================================================

            products = list(
                self._iter_product_concepts(
                    conso_file=conso_file,
                    limit=limit,
                )
            )


            self.stdout.write(
                (
                    f"Parsed "
                    f"{len(products):,} "
                    f"prescribable medication products."
                )
            )


            # =================================================
            # DRY RUN
            # =================================================

            if dry_run:

                for product in products[:50]:

                    self.stdout.write(
                        (
                            f"{product['rxcui']} | "
                            f"{product['generic_name']} | "
                            f"{product['brand_name']} | "
                            f"{product['strength']} | "
                            f"{product['dosage_form']} | "
                            f"{product['route']}"
                        )
                    )


                self.stdout.write("")


                self.stdout.write(
                    self.style.SUCCESS(
                        "RxNorm dry run complete."
                    )
                )


                self.stdout.write(
                    (
                        f"Matched products: "
                        f"{len(products):,}"
                    )
                )


                self.stdout.write(
                    self.style.WARNING(
                        (
                            "DRY RUN: no medication records "
                            "were written to the database."
                        )
                    )
                )


                return


            # =================================================
            # SAVE
            # =================================================

            statistics = (
                self._bulk_sync(
                    products=products,
                    audit_user=audit_user,
                )
            )


            self.stdout.write("")


            self.stdout.write(
                self.style.SUCCESS(
                    "RxNorm synchronization complete."
                )
            )


            self.stdout.write(
                (
                    f"Matched products: "
                    f"{statistics['matched']:,}"
                )
            )

            self.stdout.write(
                (
                    f"Created: "
                    f"{statistics['created']:,}"
                )
            )

            self.stdout.write(
                (
                    f"Updated: "
                    f"{statistics['updated']:,}"
                )
            )

            self.stdout.write(
                (
                    f"Unchanged: "
                    f"{statistics['unchanged']:,}"
                )
            )

            self.stdout.write(
                (
                    f"Skipped: "
                    f"{statistics['skipped']:,}"
                )
            )


        finally:

            if temporary_directory:

                temporary_directory.cleanup()


    # ========================================================
    # DOWNLOAD
    # ========================================================

    def _download_file(
        self,
        *,
        url: str,
        destination: Path,
    ) -> None:

        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": (
                    "Liberia-EHR-RxNorm-Sync/1.0"
                ),
                "Accept": (
                    "application/zip,"
                    "application/octet-stream,*/*"
                ),
            },
            method="GET",
        )


        try:

            with urllib.request.urlopen(
                request,
                timeout=180,
            ) as response:

                with destination.open(
                    "wb"
                ) as output:

                    while True:

                        chunk = (
                            response.read(
                                1024 * 1024
                            )
                        )


                        if not chunk:

                            break


                        output.write(
                            chunk
                        )


        except Exception as exc:

            raise CommandError(
                (
                    "Unable to download RxNorm "
                    f"Prescribable Content: {exc}"
                )
            ) from exc


        if (
            not destination.exists()
            or destination.stat().st_size
            == 0
        ):

            raise CommandError(
                "Downloaded RxNorm archive is empty."
            )


    # ========================================================
    # EXTRACT RXNCONSO.RRF
    # ========================================================

    def _extract_rxnconso(
        self,
        archive_path: Path,
    ) -> Path:

        extraction_directory = (
            archive_path.parent
            / "rxnorm_extracted"
        )


        extraction_directory.mkdir(
            parents=True,
            exist_ok=True,
        )


        try:

            with zipfile.ZipFile(
                archive_path,
                "r",
            ) as archive:

                member = None


                for name in archive.namelist():

                    if (
                        Path(name)
                        .name
                        .upper()
                        == "RXNCONSO.RRF"
                    ):

                        member = name
                        break


                if member is None:

                    raise CommandError(
                        (
                            "RXNCONSO.RRF was not found "
                            "inside the RxNorm archive."
                        )
                    )


                archive.extract(
                    member,
                    extraction_directory,
                )


        except zipfile.BadZipFile as exc:

            raise CommandError(
                (
                    "The RxNorm archive is not "
                    "a valid ZIP file."
                )
            ) from exc


        extracted_path = (
            extraction_directory
            / member
        )


        if not extracted_path.exists():

            raise CommandError(
                (
                    "RXNCONSO.RRF could not "
                    "be extracted."
                )
            )


        return extracted_path


    # ========================================================
    # READ PRODUCT CONCEPTS
    # ========================================================

    def _iter_product_concepts(
        self,
        *,
        conso_file: Path,
        limit: int,
    ):

        seen_rxcuis: set[str] = set()

        matched = 0


        with conso_file.open(
            "r",
            encoding="utf-8",
            errors="replace",
            newline="",
        ) as handle:

            reader = csv.reader(
                handle,
                delimiter="|",
            )


            for row in reader:

                if len(row) < 17:

                    continue


                rxcui = (
                    row[
                        RXCUI_INDEX
                    ]
                    .strip()
                )

                sab = (
                    row[
                        SAB_INDEX
                    ]
                    .strip()
                )

                tty = (
                    row[
                        TTY_INDEX
                    ]
                    .strip()
                )

                name = (
                    row[
                        STR_INDEX
                    ]
                    .strip()
                )

                suppress = (
                    row[
                        SUPPRESS_INDEX
                    ]
                    .strip()
                )


                if sab != "RXNORM":

                    continue


                if tty not in IMPORT_TERM_TYPES:

                    continue


                if suppress not in {
                    "",
                    "N",
                }:

                    continue


                if (
                    not rxcui
                    or not name
                ):

                    continue


                if rxcui in seen_rxcuis:

                    continue


                product = (
                    self._parse_product(
                        rxcui=rxcui,
                        name=name,
                        term_type=tty,
                    )
                )


                if not product[
                    "strength"
                ]:

                    continue


                seen_rxcuis.add(
                    rxcui
                )


                yield product


                matched += 1


                if (
                    limit
                    and matched >= limit
                ):

                    return


    # ========================================================
    # PRODUCT PARSING
    # ========================================================

    def _parse_product(
        self,
        *,
        rxcui: str,
        name: str,
        term_type: str,
    ) -> dict[str, str]:

        clean_name = (
            self._normalize_spaces(
                name
            )
        )


        brand_name = (
            self._extract_brand_name(
                clean_name
            )
        )


        strength = (
            self._extract_strength(
                clean_name
            )
        )


        dosage_form = (
            self._extract_dosage_form(
                clean_name
            )
        )


        route = (
            self._extract_route(
                clean_name
            )
        )


        generic_name = (
            self._extract_generic_name(
                clean_name
            )
        )


        return {
            "rxcui":
                rxcui,

            "term_type":
                term_type,

            "source_name":
                clean_name,

            "generic_name":
                generic_name,

            "brand_name":
                brand_name,

            "strength":
                strength,

            "dosage_form":
                dosage_form,

            "route":
                route,
        }


    # ========================================================
    # NORMALIZATION
    # ========================================================

    def _normalize_spaces(
        self,
        value: str,
    ) -> str:

        return (
            " ".join(
                str(value or "")
                .split()
            )
            .strip()
        )


    # ========================================================
    # STRENGTH
    # ========================================================
    def _extract_strength(
        self,
        name: str,
    ) -> str:
        """
        Extract complete medication strength information.

        Handles:
        - 500 MG
        - 250 MG / 5 ML
        - 10 MG/ML
        - 875 MG / 125 MG
        - 2 MG / 200 MG / 30 MG
        - percentages
        """

        # --------------------------------------------------------
        # LIQUID / CONCENTRATION FIRST
        # --------------------------------------------------------

        liquid_patterns = [

            # 250 MG / 5 ML
            (
                r"\b"
                r"\d+(?:\.\d+)?\s*"
                r"(?:MCG|MG|G|MEQ|MMOL|UNIT|UNITS)"
                r"\s*/\s*"
                r"\d+(?:\.\d+)?\s*"
                r"(?:ML|L)"
                r"\b"
            ),

            # 10 MG/ML
            (
                r"\b"
                r"\d+(?:\.\d+)?\s*"
                r"(?:MCG|MG|G|MEQ|MMOL|UNIT|UNITS)"
                r"\s*/\s*"
                r"(?:ML|L)"
                r"\b"
            ),
        ]


        for pattern in liquid_patterns:

            match = re.search(
                pattern,
                name,
                flags=re.IGNORECASE,
            )

            if match:

                return self._normalize_strength(
                    match.group(0)
                )


        # --------------------------------------------------------
        # MULTI-INGREDIENT PRODUCTS
        # --------------------------------------------------------

        component_matches = re.findall(
            (
                r"\b"
                r"\d+(?:\.\d+)?\s*"
                r"(?:MCG|MG|G|MEQ|MMOL|UNIT|UNITS)"
                r"\b"
            ),
            name,
            flags=re.IGNORECASE,
        )


        if len(component_matches) > 1:

            normalized_components = [
                self._normalize_strength(
                    component
                )
                for component in component_matches
            ]

            return " / ".join(
                normalized_components
            )


        # --------------------------------------------------------
        # SIMPLE STRENGTH
        # --------------------------------------------------------

        if component_matches:

            return self._normalize_strength(
                component_matches[0]
            )


        # --------------------------------------------------------
        # PERCENTAGE
        # --------------------------------------------------------

        percentage_match = re.search(
            r"\b\d+(?:\.\d+)?\s*%\b",
            name,
            flags=re.IGNORECASE,
        )


        if percentage_match:

            return (
                percentage_match
                .group(0)
                .replace(
                    " ",
                    ""
                )
            )


        return ""


    def _normalize_strength(
        self,
        value: str,
    ) -> str:

        result = (
            self._normalize_spaces(
                value
            )
        )


        replacements = {
            "MCG": "mcg",
            "MG": "mg",
            "ML": "mL",
            "MEQ": "mEq",
            "MMOL": "mmol",
            "UNIT": "unit",
            "UNITS": "units",
        }


        for source, target in (
            replacements.items()
        ):

            result = re.sub(
                rf"\b{source}\b",
                target,
                result,
                flags=re.IGNORECASE,
            )


        result = re.sub(
            r"\s*/\s*",
            "/",
            result,
        )


        return result


    # ========================================================
    # DOSAGE FORM
    # ========================================================

    def _extract_dosage_form(
        self,
        name: str,
    ) -> str:

        lowered = (
            name.lower()
        )


        forms = [

            (
                "extended release oral tablet",
                "Extended Release Tablet",
            ),

            (
                "extended release tablet",
                "Extended Release Tablet",
            ),

            (
                "delayed release oral tablet",
                "Delayed Release Tablet",
            ),

            (
                "delayed release tablet",
                "Delayed Release Tablet",
            ),

            (
                "orally disintegrating tablet",
                "Orally Disintegrating Tablet",
            ),

            (
                "disintegrating tablet",
                "Disintegrating Tablet",
            ),

            (
                "chewable tablet",
                "Chewable Tablet",
            ),

            (
                "sublingual tablet",
                "Sublingual Tablet",
            ),

            (
                "oral tablet",
                "Tablet",
            ),

            (
                "oral capsule",
                "Capsule",
            ),

            (
                "oral suspension",
                "Suspension",
            ),

            (
                "oral solution",
                "Solution",
            ),

            (
                "oral syrup",
                "Syrup",
            ),

            (
                "ophthalmic suspension",
                "Ophthalmic Suspension",
            ),

            (
                "ophthalmic solution",
                "Ophthalmic Solution",
            ),

            (
                "ophthalmic ointment",
                "Ophthalmic Ointment",
            ),

            (
                "otic suspension",
                "Otic Suspension",
            ),

            (
                "otic solution",
                "Otic Solution",
            ),

            (
                "inhalation solution",
                "Inhalation Solution",
            ),

            (
                "inhalation suspension",
                "Inhalation Suspension",
            ),

            (
                "inhalation powder",
                "Inhalation Powder",
            ),

            (
                "metered dose inhaler",
                "Inhaler",
            ),

            (
                "metered dose",
                "Inhaler",
            ),

            (
                "injectable solution",
                "Injection",
            ),

            (
                "injectable suspension",
                "Injection",
            ),

            (
                "prefilled syringe",
                "Prefilled Syringe",
            ),

            (
                "auto-injector",
                "Auto-Injector",
            ),

            (
                "transdermal patch",
                "Patch",
            ),

            (
                "nasal spray",
                "Nasal Spray",
            ),

            (
                "nasal solution",
                "Nasal Solution",
            ),

            (
                "topical lotion",
                "Lotion",
            ),

            (
                "topical cream",
                "Cream",
            ),

            (
                "topical ointment",
                "Ointment",
            ),

            (
                "topical gel",
                "Gel",
            ),

            (
                "topical foam",
                "Foam",
            ),

            (
                "rectal suppository",
                "Suppository",
            ),

            (
                "vaginal suppository",
                "Suppository",
            ),

            (
                "rectal enema",
                "Enema",
            ),

            (
                "enema",
                "Enema",
            ),

            (
                "tablet",
                "Tablet",
            ),

            (
                "capsule",
                "Capsule",
            ),

            (
                "suspension",
                "Suspension",
            ),

            (
                "solution",
                "Solution",
            ),

            (
                "syrup",
                "Syrup",
            ),

            (
                "lotion",
                "Lotion",
            ),

            (
                "cream",
                "Cream",
            ),

            (
                "ointment",
                "Ointment",
            ),

            (
                "gel",
                "Gel",
            ),

            (
                "foam",
                "Foam",
            ),

            (
                "patch",
                "Patch",
            ),

            (
                "spray",
                "Spray",
            ),

            (
                "suppository",
                "Suppository",
            ),

            (
                "injection",
                "Injection",
            ),

            (
                "enema",
                "Enema",
            ),
        ]


        for token, label in forms:

            if token in lowered:

                return label


        return "Other"


    # ========================================================
    # ROUTE
    # ========================================================

    def _extract_route(
        self,
        name: str,
    ) -> str:

        lowered = (
            name.lower()
        )


        routes = [

            (
                "intravenous",
                "Intravenous",
            ),

            (
                "intramuscular",
                "Intramuscular",
            ),

            (
                "subcutaneous",
                "Subcutaneous",
            ),

            (
                "intradermal",
                "Intradermal",
            ),

            (
                "sublingual",
                "Sublingual",
            ),

            (
                "buccal",
                "Buccal",
            ),

            (
                "transdermal",
                "Transdermal",
            ),

            (
                "ophthalmic",
                "Ophthalmic",
            ),

            (
                "otic",
                "Otic",
            ),

            (
                "nasal",
                "Nasal",
            ),

            (
                "inhalation",
                "Inhalation",
            ),

            (
                "rectal",
                "Rectal",
            ),

            (
                "vaginal",
                "Vaginal",
            ),

            (
                "topical",
                "Topical",
            ),

            (
                "oral",
                "Oral",
            ),

            (
                "enteral",
                "Enteral",
            ),
        ]


        for token, label in routes:

            if token in lowered:

                return label


        # Certain dosage forms strongly imply route.

        if (
            "tablet" in lowered
            or "capsule" in lowered
            or "oral solution" in lowered
            or "oral suspension" in lowered
        ):

            return "Oral"


        if (
            "cream" in lowered
            or "ointment" in lowered
            or "lotion" in lowered
            or "gel" in lowered
            or "foam" in lowered
        ):

            return "Topical"


        return "Unspecified"


    # ========================================================
    # BRAND
    # ========================================================

    def _extract_brand_name(
        self,
        name: str,
    ) -> str:

        match = re.search(
            r"\[([^\]]+)\]",
            name,
        )


        if not match:

            return ""


        return (
            self._normalize_spaces(
                match.group(1)
            )
        )


    # ========================================================
    # GENERIC NAME
    # ========================================================

    def _extract_generic_name(
        self,
        name: str,
    ) -> str:

        value = (
            name
        )


        # Remove bracketed brand.

        value = re.sub(
            r"\s*\[[^\]]+\]\s*",
            " ",
            value,
        )


        # Remove leading package quantities such as:
        # 2 ML digoxin Injection
        # 5 ML ...
        # 10 ACTUAT ...

        value = re.sub(
            (
                r"^\s*"
                r"\d+(?:\.\d+)?\s*"
                r"(?:ML|L|MG|G|ACTUAT|DOSE|TABLET|CAPSULE)"
                r"\s+"
            ),
            "",
            value,
            flags=re.IGNORECASE,
        )


        # Remove strength expressions.

        value = re.sub(
            (
                r"\b"
                r"\d+(?:\.\d+)?\s*"
                r"(?:MCG|MG|G|MEQ|MMOL|UNIT|UNITS)"
                r"(?:"
                r"\s*/\s*"
                r"(?:\d+(?:\.\d+)?\s*)?"
                r"(?:MCG|MG|G|ML|L|MEQ|MMOL|UNIT|UNITS)"
                r")*"
                r"\b"
            ),
            " ",
            value,
            flags=re.IGNORECASE,
        )


        # Remove percentages.

        value = re.sub(
            r"\b\d+(?:\.\d+)?\s*%\b",
            " ",
            value,
            flags=re.IGNORECASE,
        )


        removable_terms = [

            "Extended Release Oral Tablet",
            "Extended Release Tablet",

            "Delayed Release Oral Tablet",
            "Delayed Release Tablet",

            "Orally Disintegrating Tablet",
            "Disintegrating Tablet",

            "Chewable Tablet",
            "Sublingual Tablet",

            "Oral Tablet",
            "Oral Capsule",
            "Oral Suspension",
            "Oral Solution",
            "Oral Syrup",

            "Ophthalmic Suspension",
            "Ophthalmic Solution",
            "Ophthalmic Ointment",

            "Otic Suspension",
            "Otic Solution",

            "Inhalation Solution",
            "Inhalation Suspension",
            "Inhalation Powder",

            "Metered Dose Inhaler",

            "Injectable Solution",
            "Injectable Suspension",

            "Prefilled Syringe",
            "Auto-Injector",

            "Transdermal Patch",

            "Nasal Spray",
            "Nasal Solution",

            "Topical Lotion",
            "Topical Cream",
            "Topical Ointment",
            "Topical Gel",
            "Topical Foam",

            "Rectal Suppository",
            "Vaginal Suppository",

            "Rectal Enema",

            "Injection",
            "Tablet",
            "Capsule",
            "Suspension",
            "Solution",
            "Syrup",
            "Cream",
            "Ointment",
            "Lotion",
            "Gel",
            "Foam",
            "Patch",
            "Spray",
            "Suppository",
            "Enema",
        ]


        for term in removable_terms:

            value = re.sub(
                re.escape(
                    term
                ),
                " ",
                value,
                flags=re.IGNORECASE,
            )


        value = (
            self._normalize_spaces(
                value
            )
            .strip(
                " ,-/[]"
            )
        )


        return (
            value
            or name
        )


    # ========================================================
    # BULK DATABASE SYNC
    # ========================================================

    def _bulk_sync(
        self,
        *,
        products: list[
            dict[str, str]
        ],
        audit_user,
    ) -> dict[str, int]:

        statistics = {
            "matched":
                len(products),

            "created":
                0,

            "updated":
                0,

            "unchanged":
                0,

            "skipped":
                0,
        }


        rxcuis = [
            product["rxcui"]
            for product in products
        ]


        existing = {
            medication.rxnorm_rxcui:
                medication

            for medication in (
                Medication.objects
                .filter(
                    rxnorm_rxcui__in=rxcuis
                )
            )
        }


        to_create = []

        to_update = []


        update_fields = [
            "generic_name",
            "brand_name",
            "strength",
            "dosage_form",
            "route",
            "is_active",
        ]


        if audit_user is not None:

            update_fields.append(
                "updated_by"
            )


        for product in products:

            rxcui = (
                product["rxcui"]
            )


            medication = (
                existing.get(
                    rxcui
                )
            )


            # =================================================
            # CREATE
            # =================================================

            if medication is None:

                values: dict[
                    str,
                    Any,
                ] = {

                    "code":
                        f"RXNORM-{rxcui}",

                    "terminology_source": (
                        Medication
                        .TerminologySource
                        .RXNORM
                    ),

                    "rxnorm_rxcui":
                        rxcui,

                    "generic_name":
                        product[
                            "generic_name"
                        ],

                    "brand_name":
                        product[
                            "brand_name"
                        ],

                    "strength":
                        product[
                            "strength"
                        ],

                    "dosage_form":
                        product[
                            "dosage_form"
                        ],

                    "route":
                        product[
                            "route"
                        ],

                    "unit_of_measure":
                        "unit",

                    "formulary_status": (
                        Medication
                        .FormularyStatus
                        .NON_FORMULARY
                    ),

                    "is_active":
                        True,

                    "quantity_on_hand":
                        0,
                }


                if audit_user is not None:

                    values[
                        "created_by"
                    ] = audit_user

                    values[
                        "updated_by"
                    ] = audit_user


                to_create.append(
                    Medication(
                        **values
                    )
                )


                continue


            # =================================================
            # UPDATE
            # =================================================

            changed = False


            terminology_values = {

                "generic_name":
                    product[
                        "generic_name"
                    ],

                "brand_name":
                    product[
                        "brand_name"
                    ],

                "strength":
                    product[
                        "strength"
                    ],

                "dosage_form":
                    product[
                        "dosage_form"
                    ],

                "route":
                    product[
                        "route"
                    ],
            }


            for (
                field_name,
                new_value,
            ) in (
                terminology_values.items()
            ):

                if not new_value:

                    continue


                if (
                    getattr(
                        medication,
                        field_name,
                    )
                    != new_value
                ):

                    setattr(
                        medication,
                        field_name,
                        new_value,
                    )

                    changed = True


            if not medication.is_active:

                medication.is_active = (
                    True
                )

                changed = True


            if (
                changed
                and audit_user is not None
            ):

                medication.updated_by = (
                    audit_user
                )


            if changed:

                to_update.append(
                    medication
                )

            else:

                statistics[
                    "unchanged"
                ] += 1


        # =====================================================
        # DATABASE WRITE
        # =====================================================

        with transaction.atomic():

            if to_create:

                Medication.objects.bulk_create(
                    to_create,
                    batch_size=BULK_BATCH_SIZE,
                    ignore_conflicts=True,
                )


            if to_update:

                Medication.objects.bulk_update(
                    to_update,
                    fields=update_fields,
                    batch_size=BULK_BATCH_SIZE,
                )


        statistics[
            "created"
        ] = len(
            to_create
        )


        statistics[
            "updated"
        ] = len(
            to_update
        )


        return statistics


    # ========================================================
    # AUDIT USER
    # ========================================================

    def _get_audit_user(
        self,
        username: str,
    ):

        User = (
            get_user_model()
        )


        if username:

            try:

                return (
                    User.objects.get(
                        username=username
                    )
                )


            except User.DoesNotExist as exc:

                raise CommandError(
                    (
                        f"User '{username}' "
                        "does not exist."
                    )
                ) from exc


        return (
            User.objects
            .filter(
                is_superuser=True,
                is_active=True,
            )
            .order_by(
                "pk"
            )
            .first()
        )