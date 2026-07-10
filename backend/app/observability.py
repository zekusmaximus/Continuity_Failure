"""Request identity and structured request logging.

Every API request carries a request id: a valid inbound ``X-Request-ID`` is
adopted, anything else is replaced with a generated one. The id is echoed on the
response and attached to a single structured log line per request.

The log line is a fixed, allow-listed set of fields. Advice memo text, prompts,
secrets, and complete model inputs/outputs are never part of it — handlers may
only contribute the identifiers and outcomes declared in ``_BINDABLE_FIELDS``.
"""

from __future__ import annotations

import json
import logging
import re
import time
import uuid
from contextvars import ContextVar
from typing import Any, Dict, Optional

REQUEST_ID_HEADER = "x-request-id"
REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]{8,128}$")

logger = logging.getLogger("continuity_failure.request")

# Fields a route or service may attach to the current request's log line.
# Anything else is ignored, so no caller can widen the log surface by accident.
_BINDABLE_FIELDS = frozenset(
    {"campaign_id", "turn_number", "expected_turn", "idempotency"}
)

_request_id: ContextVar[Optional[str]] = ContextVar("cf_request_id", default=None)
_log_fields: ContextVar[Optional[Dict[str, Any]]] = ContextVar(
    "cf_log_fields", default=None
)


def configure_request_logging(level: int = logging.INFO) -> None:
    """Make the request log actually emit under uvicorn.

    Uvicorn configures only its own loggers, so without this the INFO lines
    would fall through to logging's ``lastResort`` handler (WARNING and above)
    and vanish. Propagation stays on so an operator's own root configuration —
    or pytest's capture — still sees every record.
    """
    logger.setLevel(level)
    if not logger.handlers and not logging.getLogger().handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(message)s"))
        logger.addHandler(handler)


def normalize_request_id(raw: Optional[str]) -> str:
    """Adopt a well-formed inbound id, otherwise mint a fresh one."""
    if raw is not None and REQUEST_ID_PATTERN.match(raw):
        return raw
    return uuid.uuid4().hex


def get_request_id() -> Optional[str]:
    return _request_id.get()


def bind_log_fields(**fields: Any) -> None:
    """Attach allow-listed identifiers/outcomes to this request's log line."""
    current = _log_fields.get()
    if current is None:
        return
    for key, value in fields.items():
        if key in _BINDABLE_FIELDS:
            current[key] = value


class IdempotencyOutcome:
    """How a turn-resolution request interacted with the idempotency record."""

    RESOLVED = "resolved"        # new key; the turn was resolved and committed
    REPLAYED = "replayed"        # same key + same request; original response returned
    KEY_CONFLICT = "key_conflict"  # same key, different request payload
    STALE_TURN = "stale_turn"    # expected turn no longer matches the campaign
    TERMINAL = "terminal"        # campaign already completed or failed
    REJECTED = "rejected"        # request failed validation before resolution
    NOT_APPLICABLE = "not_applicable"  # route does not resolve turns


class RequestContextMiddleware:
    """Pure ASGI middleware: request id in, structured log line out.

    Implemented at the ASGI layer rather than as ``BaseHTTPMiddleware`` so the
    context variables are set in the same task that runs the endpoint, which is
    what makes ``bind_log_fields`` visible to route handlers and the service.
    """

    def __init__(self, app) -> None:
        self.app = app
        self._routes: Optional[Dict[Any, str]] = None

    def _route_template(self, scope) -> str:
        """Prefer the route template so log routes stay low-cardinality."""
        # Starlette sets the matched route on the scope once routing has run;
        # its ``path`` is the template ("/api/campaigns/{campaign_id}/advice").
        route = scope.get("route")
        template = getattr(route, "path", None)
        if template:
            return str(template)
        # Older Starlette versions only expose the endpoint; map it back to the
        # declaring route's template.
        endpoint = scope.get("endpoint")
        if endpoint is not None:
            if self._routes is None:
                self._routes = {
                    route.endpoint: route.path
                    for route in scope.get("app").routes
                    if hasattr(route, "endpoint") and hasattr(route, "path")
                }
            template = self._routes.get(endpoint)
            if template:
                return template
        return str(scope.get("path", ""))

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = {key.decode("latin-1").lower(): value.decode("latin-1") for key, value in scope["headers"]}
        request_id = normalize_request_id(headers.get(REQUEST_ID_HEADER))
        id_token = _request_id.set(request_id)
        fields_token = _log_fields.set({"idempotency": IdempotencyOutcome.NOT_APPLICABLE})
        started = time.perf_counter()
        status_code = 500

        async def send_with_request_id(message):
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
                message.setdefault("headers", [])
                message["headers"] = [
                    *message["headers"],
                    (b"x-request-id", request_id.encode("latin-1")),
                ]
            await send(message)

        try:
            await self.app(scope, receive, send_with_request_id)
        finally:
            duration_ms = round((time.perf_counter() - started) * 1000, 3)
            bound = _log_fields.get() or {}
            # A request rejected by schema validation never reaches a handler, so
            # fall back to the routed path param to keep 422s attributable.
            campaign_id = bound.get("campaign_id") or scope.get("path_params", {}).get(
                "campaign_id"
            )
            record = {
                "event": "http_request",
                "request_id": request_id,
                "method": scope.get("method", ""),
                "route": self._route_template(scope),
                "status": status_code,
                "duration_ms": duration_ms,
                "campaign_id": campaign_id,
                "turn_number": bound.get("turn_number"),
                "expected_turn": bound.get("expected_turn"),
                "idempotency": bound.get("idempotency"),
            }
            logger.info(
                json.dumps(record, sort_keys=True),
                extra={"structured": record},
            )
            _log_fields.reset(fields_token)
            _request_id.reset(id_token)
