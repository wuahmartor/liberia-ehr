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

    Raised when the external RxNorm service cannot complete a request.

    """

class RxNormNotFound(RxNormError):

    """

    Raised when a requested RxNorm concept does not exist or is unavailable.

    """

class RxNormInvalidRequest(RxNormError):

    """

    Raised when invalid data is supplied to the RxNorm client.

    """

# ============================================================

# DATA OBJECTS

# ============================================================

@dataclass(frozen=True, slots=True)

class RxNormMedication:

    """

    Normalized representation of an RxNorm medication concept.

    Fields:

    - rxcui

    - name

    - term_type

    - generic_name

    - brand_name

    - strength

    - dosage_form

    - route

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

        Return a clean clinical display value.

        """

        parts = [

            self.generic_name or self.name,

            self.strength,

            self.dosage_form,

        ]

        return " ".join(

            part.strip()

            for part in parts

            if part and part.strip()

        )

    @property

    def is_clinical_drug(self) -> bool:

        """

        Return True for common prescribable drug/product term types.

        """

        return self.term_type in {

            "SCD",

            "SBD",

            "SCDF",

            "SBDF",

            "SCDG",

            "SBDG",

            "GPCK",

            "BPCK",

        }

# ============================================================

# RXNORM CLIENT

# ============================================================

class RxNormClient:

    """

    Small client for the National Library of Medicine RxNorm API.

    This service is used for medication terminology normalization

    and lookup.

    RxNorm results should not be interpreted as:

    - local formulary approval

    - medication availability

    - inventory status

    - clinical appropriateness

    - prescribing authorization

    """

    DEFAULT_TIMEOUT_SECONDS = 5

    DEFAULT_SEARCH_LIMIT = 20

    MAX_SEARCH_LIMIT = 100

    # ========================================================

    # CONFIGURATION

    # ========================================================

    @property

    def base_url(self) -> str:

        """

        Return configured RxNorm API base URL.

        Example:

        https://rxnav.nlm.nih.gov/REST

        """

        base_url = getattr(

            settings,

            "RXNORM_API_BASE_URL",

            "https://rxnav.nlm.nih.gov/REST",

        )

        return base_url.rstrip("/")

    @property

    def timeout_seconds(self) -> int | float:

        """

        Allow deployment-specific timeout configuration.

        """

        return getattr(

            settings,

            "RXNORM_API_TIMEOUT_SECONDS",

            self.DEFAULT_TIMEOUT_SECONDS,

        )

    # ========================================================

    # INTERNAL HTTP

    # ========================================================

    def _get_json(

        self,

        path: str,

        query: dict[str, Any] | None = None,

    ) -> dict[str, Any]:

        """

        Perform a GET request against RxNorm and return JSON.

        """

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

        except (URLError, TimeoutError) as error:

            logger.warning(

                "RxNorm connection failure url=%s error=%s",

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

                "RxNorm returned an invalid response url=%s",

                url,

            )

            raise RxNormUnavailable(

                "The RxNorm terminology service "

                "returned an invalid response."

            ) from error

        except OSError as error:

            logger.warning(

                "RxNorm network error url=%s error=%s",

                url,

                error,

            )

            raise RxNormUnavailable(

                "The RxNorm terminology service "

                "is temporarily unavailable."

            ) from error

        if not isinstance(payload, dict):

            raise RxNormUnavailable(

                "The RxNorm terminology service "

                "returned an unexpected response."

            )

        return payload

    # ========================================================

    # VALIDATION

    # ========================================================

    @staticmethod

    def _normalize_query(query: str) -> str:

        """

        Normalize user-entered medication search text.

        """

        if not isinstance(query, str):

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

        """

        Ensure search limits remain within allowed bounds.

        """

        try:

            limit = int(limit)

        except (TypeError, ValueError) as error:

            raise RxNormInvalidRequest(

                "Medication search limit must be a number."

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

        """

        Validate a supplied RxNorm Concept Unique Identifier.

        """

        value = str(

            rxcui

        ).strip()

        if (

            not value

            or not value.isdigit()

        ):

            raise RxNormInvalidRequest(

                "A valid numeric RxNorm concept identifier "

                "is required."

            )

        return value

    # ========================================================

    # MEDICATION NAME PARSING

    # ========================================================

    @staticmethod

    def _normalize_whitespace(

        value: str,

    ) -> str:

        """

        Normalize internal whitespace.

        """

        return " ".join(

            str(value or "").split()

        ).strip()

    @classmethod

    def _extract_strength(

        cls,

        name: str,

    ) -> str:

        """

        Extract common medication strengths from RxNorm names.

        Examples:

        - 500 MG

        - 250 MG/5 ML

        - 100 MCG/ACTUAT

        - 20 MG/ML

        """

        text = cls._normalize_whitespace(

            name

        )

        patterns = [

            # 250 MG/5 ML

            r"\b\d+(?:\.\d+)?\s*"

            r"(?:MCG|MG|G|UNIT|UNITS)"

            r"\s*/\s*"

            r"\d+(?:\.\d+)?\s*"

            r"(?:ML|L|ACTUAT|DOSE)\b",

            # 20 MG/ML

            r"\b\d+(?:\.\d+)?\s*"

            r"(?:MCG|MG|G|UNIT|UNITS)"

            r"\s*/\s*"

            r"(?:ML|L|ACTUAT|DOSE)\b",

            # 500 MG

            r"\b\d+(?:\.\d+)?\s*"

            r"(?:MCG|MG|G|UNIT|UNITS|MEQ|MMOL)\b",

            # 0.5 %

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

    @staticmethod

    def _normalize_strength(

        value: str,

    ) -> str:

        """

        Normalize strength casing.

        500 MG -> 500 mg

        250 MG/5 ML -> 250 mg/5 mL

        """

        value = " ".join(

            str(value or "").split()

        ).strip()

        replacements = {

            "MCG": "mcg",

            "MG": "mg",

            "G": "g",

            "ML": "mL",

            "MEQ": "mEq",

            "MMOL": "mmol",

            "UNITS": "units",

            "UNIT": "unit",

            "ACTUAT": "actuation",

            "DOSE": "dose",

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

    def _extract_dosage_form(

        cls,

        name: str,

    ) -> str:

        """

        Extract a human-friendly dosage form.

        """

        text = cls._normalize_whitespace(

            name

        ).lower()

        dosage_forms = [

            (

                "extended release oral tablet",

                "Extended Release Tablet",

            ),

            (

                "delayed release oral tablet",

                "Delayed Release Tablet",

            ),

            (

                "extended release tablet",

                "Extended Release Tablet",

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

                "tablet",

                "Tablet",

            ),

            (

                "oral capsule",

                "Capsule",

            ),

            (

                "capsule",

                "Capsule",

            ),

            (

                "oral suspension",

                "Suspension",

            ),

            (

                "suspension",

                "Suspension",

            ),

            (

                "oral solution",

                "Solution",

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

                "transdermal patch",

                "Patch",

            ),

            (

                "patch",

                "Patch",

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

                "injectable solution",

                "Injection",

            ),

            (

                "inhalation solution",

                "Inhalation Solution",

            ),

            (

                "metered dose inhaler",

                "Inhaler",

            ),

            (

                "inhaler",

                "Inhaler",

            ),

            (

                "nasal spray",

                "Nasal Spray",

            ),

            (

                "spray",

                "Spray",

            ),

            (

                "ophthalmic solution",

                "Ophthalmic Solution",

            ),

            (

                "ophthalmic drops",

                "Ophthalmic Drops",

            ),

            (

                "otic solution",

                "Otic Solution",

            ),

            (

                "otic drops",

                "Otic Drops",

            ),

            (

                "lozenge",

                "Lozenge",

            ),

            (

                "powder",

                "Powder",

            ),

        ]

        for token, label in dosage_forms:

            if token in text:

                return label

        return ""

    @classmethod

    def _extract_route(

        cls,

        name: str,

    ) -> str:

        """

        Extract a common route from the RxNorm concept name.

        """

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

    def _extract_generic_name(

        cls,

        name: str,

        strength: str,

    ) -> str:

        """

        Produce a cleaner medication name from an RxNorm product name.

        Example:

        Amoxicillin 500 MG Oral Capsule

        -> Amoxicillin

        """

        text = cls._normalize_whitespace(

            name

        )

        if strength:

            strength_pattern = re.escape(

                strength

            )

            # Strength is normalized when returned, but RxNorm name

            # usually uses uppercase units. Remove with a more

            # permissive expression instead.

            text = re.sub(

                r"\b\d+(?:\.\d+)?\s*"

                r"(?:MCG|MG|G|UNIT|UNITS|MEQ|MMOL)"

                r"(?:\s*/\s*"

                r"(?:\d+(?:\.\d+)?\s*)?"

                r"(?:ML|L|ACTUAT|DOSE))?\b",

                "",

                text,

                flags=re.IGNORECASE,

            )

        removable_terms = [

            "Extended Release Oral Tablet",

            "Delayed Release Oral Tablet",

            "Orally Disintegrating Tablet",

            "Extended Release Tablet",

            "Delayed Release Tablet",

            "Chewable Tablet",

            "Sublingual Tablet",

            "Oral Tablet",

            "Oral Capsule",

            "Oral Suspension",

            "Oral Solution",

            "Tablet",

            "Capsule",

            "Suspension",

            "Solution",

            "Syrup",

            "Cream",

            "Ointment",

            "Gel",

            "Patch",

            "Suppository",

            "Injection",

            "Inhalation Solution",

            "Inhaler",

            "Nasal Spray",

            "Spray",

            "Lozenge",

            "Powder",

        ]

        for term in removable_terms:

            text = re.sub(

                re.escape(term),

                "",

                text,

                flags=re.IGNORECASE,

            )

        text = cls._normalize_whitespace(

            text

        )

        return text or cls._normalize_whitespace(

            name

        )

    @classmethod

    def _normalize_medication(

        cls,

        *,

        rxcui: str,

        name: str,

        term_type: str = "",

    ) -> RxNormMedication:

        """

        Convert an RxNorm concept into the internal normalized object.

        """

        clean_name = cls._normalize_whitespace(

            name

        )

        strength = cls._extract_strength(

            clean_name

        )

        dosage_form = cls._extract_dosage_form(

            clean_name

        )

        route = cls._extract_route(

            clean_name

        )

        generic_name = cls._extract_generic_name(

            clean_name,

            strength,

        )

        return RxNormMedication(

            rxcui=str(rxcui).strip(),

            name=clean_name,

            term_type=str(

                term_type or ""

            ).strip(),

            generic_name=generic_name,

            brand_name="",

            strength=strength,

            dosage_form=dosage_form,

            route=route,

        )

    # ========================================================

    # SEARCH

    # ========================================================

    def search(

        self,

        query: str,

        limit: int = DEFAULT_SEARCH_LIMIT,

        *,

        active_only: bool = True,

    ) -> list[RxNormMedication]:

        """

        Search RxNorm using approximate medication-name matching.

        """

        query = self._normalize_query(

            query

        )

        limit = self._normalize_limit(

            limit

        )

        payload = self._get_json(

            "/approximateTerm.json",

            {

                "term": query,

                "maxEntries": limit,

                # RxNorm:

                # 0 = current concepts

                # 1 = active concepts

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

        seen_rxcuis: set[

            str

        ] = set()

        for candidate in candidates:

            if not isinstance(

                candidate,

                dict,

            ):

                continue

            rxcui = str(

                candidate.get(

                    "rxcui"

                )

                or ""

            ).strip()

            name = str(

                candidate.get(

                    "name"

                )

                or ""

            ).strip()

            term_type = str(

                candidate.get(

                    "tty"

                )

                or ""

            ).strip()

            if (

                not rxcui

                or not name

            ):

                continue

            if rxcui in seen_rxcuis:

                continue

            seen_rxcuis.add(

                rxcui

            )

            results.append(

                self._normalize_medication(

                    rxcui=rxcui,

                    name=name,

                    term_type=term_type,

                )

            )

            if len(results) >= limit:

                break

        return results

    # ========================================================

    # SINGLE CONCEPT LOOKUP

    # ========================================================

    def get(

        self,

        rxcui: str,

    ) -> RxNormMedication:

        """

        Retrieve a specific RxNorm concept by RxCUI.

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

            properties.get(

                "rxcui"

            )

            or ""

        ).strip()

        name = str(

            properties.get(

                "name"

            )

            or ""

        ).strip()

        term_type = str(

            properties.get(

                "tty"

            )

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

    # ========================================================

    # COMPATIBILITY ALIAS

    # ========================================================

    def get_medication(

        self,

        rxcui: str,

    ) -> RxNormMedication:

        """

        Compatibility alias for medication import code.

        Both of these now work:

            client.get(rxcui)

            client.get_medication(rxcui)

        """

        return self.get(

            rxcui

        )