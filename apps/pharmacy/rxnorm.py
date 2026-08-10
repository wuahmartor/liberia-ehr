from __future__ import annotations

import json
import logging
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
    Minimal normalized representation of an RxNorm concept.

    RxCUI:
        RxNorm Concept Unique Identifier.

    name:
        Human-readable RxNorm concept name.

    term_type:
        RxNorm term type such as:
        - IN  = Ingredient
        - PIN = Precise Ingredient
        - SCD = Semantic Clinical Drug
        - SBD = Semantic Branded Drug
        - GPCK = Generic Pack
        - BPCK = Branded Pack
    """

    rxcui: str
    name: str
    term_type: str = ""

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

    This service is used for medication terminology normalization and
    lookup. RxNorm results should not be interpreted as:

    - local formulary approval
    - medication availability
    - inventory status
    - clinical appropriateness
    - prescribing authorization
    """

    DEFAULT_TIMEOUT_SECONDS = 5
    DEFAULT_SEARCH_LIMIT = 20
    MAX_SEARCH_LIMIT = 100

    @property
    def base_url(self) -> str:
        """
        Return configured RxNorm API base URL.

        Expected example:

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
        Perform a GET request against the RxNorm API and return JSON.

        External service errors are converted into application-specific
        exceptions so Django views do not need to handle urllib details.
        """

        url = f"{self.base_url}{path}"

        if query:
            clean_query = {
                key: value
                for key, value in query.items()
                if value is not None
            }

            if clean_query:
                url = f"{url}?{urlencode(clean_query)}"

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
                "The RxNorm terminology service is temporarily unavailable."
            ) from error

        except (URLError, TimeoutError) as error:
            logger.warning(
                "RxNorm connection failure url=%s error=%s",
                url,
                error,
            )

            raise RxNormUnavailable(
                "The RxNorm terminology service is temporarily unavailable."
            ) from error

        except (json.JSONDecodeError, UnicodeDecodeError) as error:
            logger.warning(
                "RxNorm returned an invalid response url=%s",
                url,
            )

            raise RxNormUnavailable(
                "The RxNorm terminology service returned an invalid response."
            ) from error

        except OSError as error:
            logger.warning(
                "RxNorm network error url=%s error=%s",
                url,
                error,
            )

            raise RxNormUnavailable(
                "The RxNorm terminology service is temporarily unavailable."
            ) from error

        if not isinstance(payload, dict):
            raise RxNormUnavailable(
                "The RxNorm terminology service returned an unexpected response."
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

        query = " ".join(query.split()).strip()

        if len(query) < 2:
            raise RxNormInvalidRequest(
                "Enter at least two characters to search medications."
            )

        return query

    @classmethod
    def _normalize_limit(cls, limit: int) -> int:
        """
        Ensure search limits remain within RxNorm API constraints.
        """

        try:
            limit = int(limit)
        except (TypeError, ValueError) as error:
            raise RxNormInvalidRequest(
                "Medication search limit must be a number."
            ) from error

        return max(
            1,
            min(limit, cls.MAX_SEARCH_LIMIT),
        )

    @staticmethod
    def _validate_rxcui(rxcui: str) -> str:
        """
        Validate a supplied RxNorm Concept Unique Identifier.
        """

        value = str(rxcui).strip()

        if not value or not value.isdigit():
            raise RxNormInvalidRequest(
                "A valid numeric RxNorm concept identifier is required."
            )

        return value

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

        Approximate matching is useful for:
        - misspellings
        - partial medication names
        - incomplete drug descriptions
        - strength/form text entered by clinicians

        active_only=True limits matches to active RxNorm concepts.
        """

        query = self._normalize_query(query)
        limit = self._normalize_limit(limit)

        payload = self._get_json(
            "/approximateTerm.json",
            {
                "term": query,
                "maxEntries": limit,

                # RxNorm option:
                # 0 = current concepts
                # 1 = active concepts
                "option": 1 if active_only else 0,
            },
        )

        candidates = (
            payload
            .get("approximateGroup", {})
            .get("candidate", [])
        )

        if not isinstance(candidates, list):
            return []

        results: list[RxNormMedication] = []
        seen_rxcuis: set[str] = set()

        for candidate in candidates:
            if not isinstance(candidate, dict):
                continue

            rxcui = str(
                candidate.get("rxcui") or ""
            ).strip()

            name = str(
                candidate.get("name") or ""
            ).strip()

            term_type = str(
                candidate.get("tty") or ""
            ).strip()

            if not rxcui:
                continue

            if not name:
                continue

            if rxcui in seen_rxcuis:
                continue

            seen_rxcuis.add(rxcui)

            results.append(
                RxNormMedication(
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

    def get(self, rxcui: str) -> RxNormMedication:
        """
        Retrieve an active RxNorm concept by RxCUI.
        """

        rxcui = self._validate_rxcui(rxcui)

        payload = self._get_json(
            f"/rxcui/{rxcui}/properties.json"
        )

        properties = payload.get("properties")

        if not isinstance(properties, dict):
            raise RxNormNotFound(
                "The selected RxNorm medication concept was not found."
            )

        returned_rxcui = str(
            properties.get("rxcui") or ""
        ).strip()

        name = str(
            properties.get("name") or ""
        ).strip()

        term_type = str(
            properties.get("tty") or ""
        ).strip()

        if not returned_rxcui or not name:
            raise RxNormNotFound(
                "The selected RxNorm medication concept was not found."
            )

        return RxNormMedication(
            rxcui=returned_rxcui,
            name=name,
            term_type=term_type,
        )