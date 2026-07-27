from __future__ import annotations

from django.http import HttpRequest


def is_htmx(request: HttpRequest) -> bool:
    """Return True when the request was sent by HTMX."""
    return request.headers.get("HX-Request", "").lower() == "true"
