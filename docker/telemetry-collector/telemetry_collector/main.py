from __future__ import annotations

from datetime import datetime, timezone
from urllib.parse import parse_qsl

from fastapi import FastAPI, HTTPException, Request

from telemetry_collector import __version__
from telemetry_collector.models import Scalar, TelemetryEnvelope
from telemetry_collector.registry import registry
from telemetry_collector.sources.ecowitt import EcowittPayloadError


app = FastAPI(title="Homelab Telemetry Collector", version=__version__)
latest: dict[str, TelemetryEnvelope] = {}


@app.get("/api/health")
def health() -> dict[str, object]:
    return {
        "status": "healthy",
        "version": __version__,
        "handlers": registry.names,
    }


@app.post("/data/report/", status_code=202)
async def ecowitt_report(request: Request) -> dict[str, object]:
    content_type = request.headers.get("content-type", "")
    if "application/x-www-form-urlencoded" not in content_type:
        raise HTTPException(status_code=415, detail="expected application/x-www-form-urlencoded")
    body = (await request.body()).decode("utf-8")
    payload: dict[str, Scalar] = dict(parse_qsl(body, keep_blank_values=True))
    try:
        envelope = registry.get("ecowitt").normalize(
            payload,
            received_at=datetime.now(timezone.utc),
        )
    except EcowittPayloadError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    latest[envelope.source] = envelope
    return {
        "status": "accepted",
        "source": envelope.source,
        "observed_at": envelope.observed_at.isoformat(),
        "measurement_count": len(envelope.measurements),
    }


@app.get("/api/current/{source}")
def current(source: str) -> dict[str, object]:
    envelope = latest.get(source)
    if envelope is None:
        raise HTTPException(status_code=404, detail=f"no telemetry available for source: {source}")
    return envelope.to_dict()
