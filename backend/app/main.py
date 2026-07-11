"""FastAPI application entry point.

Run from the ``backend/`` directory:

    uvicorn app.main:app --reload

The deterministic engine is the source of truth for all state changes; this
layer only routes requests and serializes results.
"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import campaigns as campaigns_api
from app.observability import (
    RequestContextMiddleware,
    configure_request_logging,
    get_request_id,
)
from app.schemas import api as schemas
from engine import seed_data
from memory.persistence import CorruptRecordError, RepositoryBusyError

app = FastAPI(
    title="Continuity Failure",
    description=(
        "Orchestration layer for the Northbridge Water Failure MVP. The "
        "deterministic engine owns all state; a dormant, off-by-default "
        "AI-assist layer (memo drafter + ModelRun logging) is present and "
        "validation-gated, degrading to deterministic fallback when AI is off "
        "or a model call fails."
    ),
    version="0.1.0",
)

# Permissive CORS for the Vite dev server. Tighten for deployment.
# ``X-Request-ID`` is exposed so a browser client can quote it when reporting a
# failure, and accepted inbound so a caller-supplied trace id survives the hop.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID", "Idempotent-Replay"],
)

# Added last, so it wraps every other middleware: the request id exists before
# any handler runs and the structured log line is emitted after all of them.
app.add_middleware(RequestContextMiddleware)
configure_request_logging()


@app.exception_handler(CorruptRecordError)
def corrupt_record_handler(_request: Request, _exc: CorruptRecordError):
    # The underlying message can name tables, columns, and record paths. Clients
    # get a stable code and the request id; operators correlate via the logs.
    return JSONResponse(
        status_code=500,
        content={
            "detail": {
                "error": "corrupt_record",
                "message": (
                    "A stored record for this engagement could not be read. "
                    "The engagement may be damaged."
                ),
                "request_id": get_request_id(),
            }
        },
    )


@app.exception_handler(RepositoryBusyError)
def repository_busy_handler(_request: Request, _exc: RepositoryBusyError):
    # The write lock timed out before any statement was applied. Retrying the
    # identical request (same idempotency key) is safe and is the right advice.
    return JSONResponse(
        status_code=503,
        content={
            "detail": {
                "error": "repository_busy",
                "message": (
                    "The engagement record is busy. Retry this submission "
                    "unchanged; it has not been applied."
                ),
                "request_id": get_request_id(),
            }
        },
        headers={"Retry-After": "1"},
    )


@app.get("/health", response_model=schemas.HealthModel, tags=["meta"])
def health():
    return schemas.HealthModel(
        status="ok",
        service="continuity-failure-backend",
        scenario=seed_data.SCENARIO_ID,
    )


app.include_router(campaigns_api.router)
app.include_router(campaigns_api.scenarios_router)
