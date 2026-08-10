from __future__ import annotations

import json

import logging

import re

from dataclasses import dataclass

from typing import Any

from urllib.error import HTTPError, URLError

from urllib.parse import urlencode

from urllib.request import Request, urlopen

from django.conf import settings

logger = logging.getLogger(__name__)

# ============================================================

# EXCEPTIONS

# ============================================================

class RxNormError(Exception):

    """

    Base exception for RxNorm integration errors.

    """

class RxNormUnavailable(RxNormError):

    """

    Raised when RxNorm cannot complete a request.

    """

class RxNormNotFound(RxNormError):

    """

    Raised when a requested RxNorm concept does not exist.

    """

class RxNormInvalidRequest(RxNormError):

    """

    Raised when invalid input is supplied to the client.

    """

# ============================================================

# DATA OBJECT

# ============================================================

@dataclass(

    frozen=True,

    slots=True,

)

class RxNormMedication:

    """

    Normalized medication product returned by RxNorm.

    """

    rxcui: str

    name: str

    term_type: str = ""

    generic_name: str = ""

    brand_name: str = ""

    strength: str = ""

    dosage_form: str = ""

    route: str = ""

    @property

    def display_name(self) -> str:

        """

        Clean provider-facing medication label.

        """

        pieces = [

            self.generic_name or self.name,

            self.strength,

            self.dosage_form,

        ]

        return " ".join(

            value

            for value in pieces

            if value

        ).strip()

    @property

    def is_clinical_drug(self) -> bool:

        """

        Return True for product-level concepts suitable

        for medication selection.

        """

        return self.term_type in {

            "SCD",

            "SBD",

        }

# ============================================================

# CLIENT

# ============================================================

class RxNormClient:

    """

    RxNorm medication terminology client.

    Provider ordering search intentionally favors product-level

    medication concepts containing useful prescribing details

    such as strength and dosage form.

    """

    DEFAULT_TIMEOUT_SECONDS = 5

    DEFAULT_SEARCH_LIMIT = 30

    MAX_SEARCH_LIMIT = 100

    ORDERABLE_TERM_TYPES = {

        "SCD",

        "SBD",

    }

    # ========================================================

    # CONFIG

    # ========================================================

    @property

    def base_url(self) -> str:

        return getattr(

            settings,

            "RXNORM_API_BASE_URL",

            "https://rxnav.nlm.nih.gov/REST",

        ).rstrip("/")

    @property

    def timeout_seconds(self) -> int | float:

        return getattr(

            settings,

            "RXNORM_API_TIMEOUT_SECONDS",

            self.DEFAULT_TIMEOUT_SECONDS,

        )

    # ========================================================

    # HTTP

    # ========================================================

    def _get_json(

        self,

        path: str,

        query: dict[str, Any] | None = None,

    ) -> dict[str, Any]:

        url = f"{self.base_url}{path}"

        if query:

            clean_query = {

                key: value

                for key, value in query.items()

                if value is not None

            }

            if clean_query:

                url = (

                    f"{url}?"

                    f"{urlencode(clean_query)}"

                )

        request = Request(

            url,

            headers={

                "Accept": "application/json",

                "User-Agent": "Liberia-EHR/1.0",

            },

            method="GET",

        )

        try:

            with urlopen(

                request,

                timeout=self.timeout_seconds,

            ) as response:

                payload = json.load(response)

        except HTTPError as error:

            logger.warning(

                "RxNorm HTTP error status=%s url=%s",

                error.code,

                url,

            )

            if error.code == 404:

                raise RxNormNotFound(

                    "The requested RxNorm concept was not found."

                ) from error

            raise RxNormUnavailable(

                "The RxNorm terminology service "

                "is temporarily unavailable."

            ) from error

        except (

            URLError,

            TimeoutError,

            OSError,

        ) as error:

            logger.warning(

                "RxNorm network failure url=%s error=%s",

                url,

                error,

            )

            raise RxNormUnavailable(

                "The RxNorm terminology service "

                "is temporarily unavailable."

            ) from error

        except (

            json.JSONDecodeError,

            UnicodeDecodeError,

        ) as error:

            logger.warning(

                "Invalid RxNorm response url=%s",

                url,

            )

            raise RxNormUnavailable(

                "The RxNorm terminology service returned "

                "an invalid response."

            ) from error

        if not isinstance(

            payload,

            dict,

        ):

            raise RxNormUnavailable(

                "The RxNorm terminology service returned "

                "an unexpected response."

            )

        return payload

    # ========================================================

    # VALIDATION

    # ========================================================

    @staticmethod

    def _normalize_query(

        query: str,

    ) -> str:

        if not isinstance(

            query,

            str,

        ):

            raise RxNormInvalidRequest(

                "Medication search text must be a string."

            )

        query = " ".join(

            query.split()

        ).strip()

        if len(query) < 2:

            raise RxNormInvalidRequest(

                "Enter at least two characters "

                "to search medications."

            )

        return query

    @classmethod

    def _normalize_limit(

        cls,

        limit: int,

    ) -> int:

        try:

            limit = int(limit)

        except (

            TypeError,

            ValueError,

        ) as error:

            raise RxNormInvalidRequest(

                "Medication search limit must be numeric."

            ) from error

        return max(

            1,

            min(

                limit,

                cls.MAX_SEARCH_LIMIT,

            ),

        )

    @staticmethod

    def _validate_rxcui(

        rxcui: str,

    ) -> str:

        value = str(

            rxcui

        ).strip()

        if (

            not value

            or not value.isdigit()

        ):

            raise RxNormInvalidRequest(

                "A valid numeric RxCUI is required."

            )

        return value

    # ========================================================

    # NORMALIZATION HELPERS

    # ========================================================

    @staticmethod

    def _normalize_whitespace(

        value: str,

    ) -> str:

        return " ".join(

            str(value or "").split()

        ).strip()

    @staticmethod

    def _normalize_strength(

        value: str,

    ) -> str:

        value = " ".join(

            str(value or "").split()

        ).strip()

        replacements = {

            "MCG": "mcg",

            "MG": "mg",

            "ML": "mL",

            "MEQ": "mEq",

            "MMOL": "mmol",

            "UNITS": "units",

            "UNIT": "unit",

        }

        for old, new in replacements.items():

            value = re.sub(

                rf"\b{old}\b",

                new,

                value,

                flags=re.IGNORECASE,

            )

        value = re.sub(

            r"\s*/\s*",

            "/",

            value,

        )

        return value

    @classmethod

    def _extract_strength(

        cls,

        name: str,

    ) -> str:

        text = cls._normalize_whitespace(

            name

        )

        patterns = [

            # Combination or liquid:

            # 300 MG / 30 MG

            # 250 MG / 5 ML

            (

                r"\b\d+(?:\.\d+)?\s*"

                r"(?:MCG|MG|G|UNIT|UNITS|MEQ|MMOL)"

                r"(?:\s*/\s*"

                r"\d+(?:\.\d+)?\s*"

                r"(?:MCG|MG|G|ML|L|UNIT|UNITS|MEQ|MMOL)"

                r")+\b"

            ),

            # Concentration:

            # 20 MG/ML

            (

                r"\b\d+(?:\.\d+)?\s*"

                r"(?:MCG|MG|G|UNIT|UNITS)"

                r"\s*/\s*"

                r"(?:ML|L)\b"

            ),

            # Simple:

            # 500 MG

            (

                r"\b\d+(?:\.\d+)?\s*"

                r"(?:MCG|MG|G|UNIT|UNITS|MEQ|MMOL)\b"

            ),

            # Percentage:

            r"\b\d+(?:\.\d+)?\s*%\b",

        ]

        for pattern in patterns:

            match = re.search(

                pattern,

                text,

                flags=re.IGNORECASE,

            )

            if match:

                return cls._normalize_strength(

                    match.group(0)

                )

        return ""

    @classmethod

    def _extract_dosage_form(

        cls,

        name: str,

    ) -> str:

        text = cls._normalize_whitespace(

            name

        ).lower()

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

                "ophthalmic solution",

                "Ophthalmic Solution",

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

                "injectable solution",

                "Injection",

            ),

            (

                "injection",

                "Injection",

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

                "suppository",

                "Suppository",

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

        ]

        for token, label in forms:

            if token in text:

                return label

        return ""

    @classmethod

    def _extract_route(

        cls,

        name: str,

    ) -> str:

        text = cls._normalize_whitespace(

            name

        ).lower()

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

                "sublingual",

                "Sublingual",

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

        ]

        for token, label in routes:

            if token in text:

                return label

        return ""

    @classmethod

    def _extract_brand_name(

        cls,

        name: str,

    ) -> str:

        text = cls._normalize_whitespace(

            name

        )

        match = re.search(

            r"\[([^\]]+)\]",

            text,

        )

        if not match:

            return ""

        return cls._normalize_whitespace(

            match.group(1)

        )

    @classmethod

    def _extract_generic_name(

        cls,

        name: str,

        strength: str,

        dosage_form: str,

        brand_name: str,

    ) -> str:

        text = cls._normalize_whitespace(

            name

        )

        # Remove bracketed brand.

        text = re.sub(

            r"\s*\[[^\]]+\]\s*",

            " ",

            text,

        )

        # Remove strengths.

        text = re.sub(

            (

                r"\b\d+(?:\.\d+)?\s*"

                r"(?:MCG|MG|G|UNIT|UNITS|MEQ|MMOL)"

                r"(?:\s*/\s*"

                r"\d*(?:\.\d+)?\s*"

                r"(?:MCG|MG|G|ML|L|UNIT|UNITS|MEQ|MMOL)"

                r")*\b"

            ),

            " ",

            text,

            flags=re.IGNORECASE,

        )

        removable_terms = [

            "Extended Release Oral Tablet",

            "Extended Release Tablet",

            "Delayed Release Oral Tablet",

            "Delayed Release Tablet",

            "Orally Disintegrating Tablet",

            "Chewable Tablet",

            "Sublingual Tablet",

            "Oral Tablet",

            "Oral Capsule",

            "Oral Suspension",

            "Oral Solution",

            "Ophthalmic Solution",

            "Otic Solution",

            "Inhalation Solution",

            "Injectable Solution",

            "Injection",

            "Transdermal Patch",

            "Nasal Spray",

            "Cream",

            "Ointment",

            "Gel",

            "Suppository",

            "Tablet",

            "Capsule",

            "Suspension",

            "Solution",

        ]

        for term in removable_terms:

            text = re.sub(

                re.escape(term),

                " ",

                text,

                flags=re.IGNORECASE,

            )

        text = cls._normalize_whitespace(

            text

        )

        return (

            text

            or cls._normalize_whitespace(

                name

            )

        )

    @classmethod

    def _normalize_medication(

        cls,

        *,

        rxcui: str,

        name: str,

        term_type: str,

    ) -> RxNormMedication:

        clean_name = cls._normalize_whitespace(

            name

        )

        strength = cls._extract_strength(

            clean_name

        )

        dosage_form = (

            cls._extract_dosage_form(

                clean_name

            )

        )

        route = cls._extract_route(

            clean_name

        )

        brand_name = (

            cls._extract_brand_name(

                clean_name

            )

        )

        generic_name = (

            cls._extract_generic_name(

                clean_name,

                strength,

                dosage_form,

                brand_name,

            )

        )

        return RxNormMedication(

            rxcui=str(

                rxcui

            ).strip(),

            name=clean_name,

            term_type=str(

                term_type or ""

            ).strip(),

            generic_name=(

                generic_name

            ),

            brand_name=(

                brand_name

            ),

            strength=(

                strength

            ),

            dosage_form=(

                dosage_form

            ),

            route=(

                route

            ),

        )

    # ========================================================

    # PRODUCT SEARCH

    # ========================================================

    def search(

        self,

        query: str,

        limit: int = DEFAULT_SEARCH_LIMIT,

        *,

        active_only: bool = True,

    ) -> list[RxNormMedication]:

        """

        Search for actual drug products rather than broad

        terminology concepts.

        Uses RxNorm getDrugs first because it returns product

        concepts such as SCD and SBD.

        Approximate matching is used only to help resolve a

        partially typed or misspelled drug name.

        """

        query = self._normalize_query(

            query

        )

        limit = self._normalize_limit(

            limit

        )

        products = self._search_drug_products(

            query=query,

            limit=limit,

        )

        if products:

            return products

        # ----------------------------------------------------

        # FALLBACK: approximate search

        # ----------------------------------------------------

        approximate = (

            self._search_approximate(

                query=query,

                limit=10,

                active_only=active_only,

            )

        )

        results: list[

            RxNormMedication

        ] = []

        seen: set[str] = set()

        for candidate in approximate:

            # Try the RxNorm candidate name through getDrugs.

            expanded = (

                self._search_drug_products(

                    query=candidate.name,

                    limit=limit,

                )

            )

            for medication in expanded:

                if (

                    medication.rxcui

                    in seen

                ):

                    continue

                seen.add(

                    medication.rxcui

                )

                results.append(

                    medication

                )

                if len(results) >= limit:

                    return results

        return results

    def _search_drug_products(

        self,

        *,

        query: str,

        limit: int,

    ) -> list[RxNormMedication]:

        """

        Use RxNorm getDrugs to retrieve product-level

        prescribing concepts.

        """

        payload = self._get_json(

            "/drugs.json",

            {

                "name": query,

                # Request prescribable name where available.

                "expand": "psn",

            },

        )

        concept_groups = (

            payload

            .get(

                "drugGroup",

                {},

            )

            .get(

                "conceptGroup",

                [],

            )

        )

        if not isinstance(

            concept_groups,

            list,

        ):

            return []

        results: list[

            RxNormMedication

        ] = []

        seen: set[str] = set()

        for group in concept_groups:

            if not isinstance(

                group,

                dict,

            ):

                continue

            group_tty = str(

                group.get("tty")

                or ""

            ).strip()

            # Do not expose broad concepts like:

            # Pill

            # Oral Product

            # Dose Form Group

            #

            # Only return actual drug products.

            if (

                group_tty

                not in self.ORDERABLE_TERM_TYPES

            ):

                continue

            concepts = (

                group.get(

                    "conceptProperties",

                    []

                )

                or []

            )

            if not isinstance(

                concepts,

                list,

            ):

                continue

            for concept in concepts:

                if not isinstance(

                    concept,

                    dict,

                ):

                    continue

                rxcui = str(

                    concept.get("rxcui")

                    or ""

                ).strip()

                tty = str(

                    concept.get("tty")

                    or group_tty

                ).strip()

                # Prefer the Prescribable Name.

                name = (

                    str(

                        concept.get("psn")

                        or ""

                    ).strip()

                    or str(

                        concept.get("name")

                        or ""

                    ).strip()

                    or str(

                        concept.get("synonym")

                        or ""

                    ).strip()

                )

                if (

                    not rxcui

                    or not name

                ):

                    continue

                if (

                    tty

                    not in self.ORDERABLE_TERM_TYPES

                ):

                    continue

                if rxcui in seen:

                    continue

                seen.add(

                    rxcui

                )

                medication = (

                    self._normalize_medication(

                        rxcui=rxcui,

                        name=name,

                        term_type=tty,

                    )

                )

                # For ordering we want actual useful product

                # definitions. Avoid broad product names that

                # still have no strength.

                if (

                    not medication.strength

                ):

                    continue

                results.append(

                    medication

                )

        # Generic products first, then branded products.

        results.sort(

            key=lambda med: (

                0

                if med.term_type == "SCD"

                else 1,

                med.generic_name.lower(),

                med.strength.lower(),

                med.dosage_form.lower(),

                med.brand_name.lower(),

            )

        )

        return results[:limit]

    def _search_approximate(

        self,

        *,

        query: str,

        limit: int,

        active_only: bool,

    ) -> list[RxNormMedication]:

        """

        Approximate search used only as a name-resolution

        fallback.

        """

        payload = self._get_json(

            "/approximateTerm.json",

            {

                "term": query,

                "maxEntries": limit,

                "option": (

                    1

                    if active_only

                    else 0

                ),

            },

        )

        candidates = (

            payload

            .get(

                "approximateGroup",

                {},

            )

            .get(

                "candidate",

                [],

            )

        )

        if not isinstance(

            candidates,

            list,

        ):

            return []

        results: list[

            RxNormMedication

        ] = []

        seen: set[str] = set()

        for candidate in candidates:

            if not isinstance(

                candidate,

                dict,

            ):

                continue

            rxcui = str(

                candidate.get("rxcui")

                or ""

            ).strip()

            name = str(

                candidate.get("name")

                or ""

            ).strip()

            if (

                not rxcui

                or not name

            ):

                continue

            if rxcui in seen:

                continue

            seen.add(

                rxcui

            )

            results.append(

                RxNormMedication(

                    rxcui=rxcui,

                    name=name,

                )

            )

        return results

    # ========================================================

    # SINGLE CONCEPT LOOKUP

    # ========================================================

    def get(

        self,

        rxcui: str,

    ) -> RxNormMedication:

        """

        Retrieve and normalize a specific RxNorm concept.

        """

        rxcui = self._validate_rxcui(

            rxcui

        )

        payload = self._get_json(

            f"/rxcui/{rxcui}/properties.json"

        )

        properties = payload.get(

            "properties"

        )

        if not isinstance(

            properties,

            dict,

        ):

            raise RxNormNotFound(

                "The selected RxNorm medication "

                "concept was not found."

            )

        returned_rxcui = str(

            properties.get("rxcui")

            or ""

        ).strip()

        name = (

            str(

                properties.get("psn")

                or ""

            ).strip()

            or str(

                properties.get("name")

                or ""

            ).strip()

            or str(

                properties.get("synonym")

                or ""

            ).strip()

        )

        term_type = str(

            properties.get("tty")

            or ""

        ).strip()

        if (

            not returned_rxcui

            or not name

        ):

            raise RxNormNotFound(

                "The selected RxNorm medication "

                "concept was not found."

            )

        return self._normalize_medication(

            rxcui=returned_rxcui,

            name=name,

            term_type=term_type,

        )

    def get_medication(

        self,

        rxcui: str,

    ) -> RxNormMedication:

        """

        Compatibility alias.

        """

        return self.get(

            rxcui

        )