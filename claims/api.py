"""Thin FastAPI service. Routes validate, delegate, map errors. Logic lives in agent/runner/db."""
from __future__ import annotations

from typing import Literal
from uuid import UUID

from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict

from . import db
from .agent import run_agent
from .data import default_catalogue
from .errors import (AgentError, InfrastructureError, ProviderTimeout, sanitize)
from .models import AgentInput, AgentOutput
from .provider import make_provider
from .runner import run_split

app = FastAPI(title="Claim extraction & classification agent")


class ClassifyRequest(AgentInput):
    agent_version: Literal["v1", "v2"]


class RunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    agent_version: Literal["v1", "v2"]
    split: Literal["development", "check"]


def get_provider():
    """Dependency returns a FACTORY so validation (422/404) happens before any key/DB is needed."""
    return make_provider


def get_connect():
    return db.connect


def err(status: int, type_: str, message: str) -> JSONResponse:
    return JSONResponse(status_code=status, content={"error": {"type": type_, "message": sanitize(message)}})


@app.exception_handler(RequestValidationError)
async def _validation(_: Request, exc: RequestValidationError):
    # report field locations + error types only; never echo the submitted text
    msg = "; ".join(f"{'.'.join(str(x) for x in e['loc'])}: {e['type']}" for e in exc.errors()[:5])
    return err(422, "validation_error", msg)


@app.exception_handler(InfrastructureError)
async def _infra(_: Request, exc: InfrastructureError):
    return err(502, "infrastructure_error", str(exc))


@app.post("/classify", response_model=AgentOutput)
def classify(req: ClassifyRequest, make_provider=Depends(get_provider)):
    if req.brand_id not in default_catalogue().brands:
        return err(404, "unknown_brand", "primary brand not found")
    inp = AgentInput(**req.model_dump(exclude={"agent_version"}))
    try:
        return run_agent(inp, make_provider(), req.agent_version)
    except ProviderTimeout as e:
        return err(504, e.type, e.message)
    except AgentError as e:
        return err(502, e.type, e.message)


@app.post("/evaluation-runs", status_code=201)
def create_run(req: RunRequest, make_provider=Depends(get_provider), connect=Depends(get_connect)):
    run = run_split(req.agent_version, req.split, make_provider())
    with connect() as conn:
        db.save_run(conn, run)
    return {"run_id": run["run_id"], "status": run["status"], "agent_version": run["agent_version"],
            "split": run["split"], "counts": run["counts"], "metrics": run["metrics"]}


@app.get("/evaluation-runs/{run_id}")
def get_run(run_id: UUID, connect=Depends(get_connect)):
    with connect() as conn:
        run = db.load_run(conn, str(run_id))
    return run if run else err(404, "not_found", "run not found")
