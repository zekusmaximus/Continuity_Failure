"""FastAPI application entry point.

Run from the ``backend/`` directory:

    uvicorn app.main:app --reload

The deterministic engine is the source of truth for all state changes; this
layer only routes requests and serializes results.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import campaigns as campaigns_api
from app.schemas import api as schemas
from engine import seed_data

app = FastAPI(
    title="Continuity Failure",
    description=(
        "Orchestration layer for the Northbridge Water Failure MVP. "
        "AI integration is intentionally not implemented in this slice."
    ),
    version="0.1.0",
)

# Permissive CORS for the Vite dev server. Tighten for deployment.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", response_model=schemas.HealthModel, tags=["meta"])
def health():
    return schemas.HealthModel(
        status="ok",
        service="continuity-failure-backend",
        scenario=seed_data.SCENARIO_ID,
    )


app.include_router(campaigns_api.router)
