from __future__ import annotations

import json
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import urlopen

from django.conf import settings


class RxNormUnavailable(Exception):
    """Raised when the external RxNorm service cannot serve a request."""


@dataclass(frozen=True)
class RxNormMedication:
    rxcui: str
    name: str
    term_type: str


class RxNormClient:
    timeout_seconds = 5

    @property
    def base_url(self) -> str:
        return settings.RXNORM_API_BASE_URL.rstrip("/")

    def _get_json(self, path: str, query: dict | None = None) -> dict:
        url = f"{self.base_url}{path}"
        if query:
            url = f"{url}?{urlencode(query)}"

        try:
            with urlopen(url, timeout=self.timeout_seconds) as response:
                return json.load(response)
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as error:
            raise RxNormUnavailable(
                "The US medication directory is temporarily unavailable."
            ) from error

    def search(self, query: str, limit: int = 20) -> list[RxNormMedication]:
        payload = self._get_json(
            "/approximateTerm.json",
            {"term": query, "maxEntries": limit},
        )
        candidates = payload.get("approximateGroup", {}).get("candidate", [])
        results: list[RxNormMedication] = []
        seen_rxcuis: set[str] = set()

        for candidate in candidates:
            rxcui = candidate.get("rxcui")
            if not rxcui or rxcui in seen_rxcuis:
                continue

            name = candidate.get("name")
            if not name:
                continue

            seen_rxcuis.add(rxcui)
            results.append(
                RxNormMedication(
                    rxcui=rxcui,
                    name=name,
                    term_type=candidate.get("tty", ""),
                )
            )
            if len(results) == limit:
                break

        return results

    def get(self, rxcui: str) -> RxNormMedication:
        payload = self._get_json(f"/rxcui/{rxcui}/properties.json")
        properties = payload.get("properties")
        if not properties or not properties.get("rxcui") or not properties.get("name"):
            raise RxNormUnavailable("The selected US medication is unavailable.")

        return RxNormMedication(
            rxcui=properties["rxcui"],
            name=properties["name"],
            term_type=properties.get("tty", ""),
        )
