from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qsl

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from telemetry_collector import __version__
from telemetry_collector.config import Settings
from telemetry_collector.models import Scalar, TelemetryEnvelope
from telemetry_collector.registry import registry
from telemetry_collector.sources.ecowitt import EcowittPayloadError
from telemetry_collector.storage.base import MemoryTelemetryStore, StorageUnavailable, TelemetryStore


MAX_HISTORY_RANGE = timedelta(days=31)
SOURCE_PATTERN = re.compile(r"^[a-z][a-z0-9_-]{0,31}$")


def _build_store(settings: Settings) -> TelemetryStore:
    if settings.storage_backend == "influxdb":
        from telemetry_collector.storage.influxdb import InfluxDBTelemetryStore

        return InfluxDBTelemetryStore(settings)
    return MemoryTelemetryStore()


def _source_slug(source: str) -> str:
    if not SOURCE_PATTERN.fullmatch(source):
        raise HTTPException(status_code=422, detail="source must be a lowercase slug")
    return source


def _freshness(envelope: TelemetryEnvelope, settings: Settings) -> tuple[bool, float]:
    age = max(0.0, (datetime.now(timezone.utc) - envelope.received_at).total_seconds())
    return age > settings.stale_after_seconds, round(age, 3)


def create_app(
    *,
    store: TelemetryStore | None = None,
    settings: Settings | None = None,
) -> FastAPI:
    active_settings = settings or Settings.from_environment()
    active_store = store or _build_store(active_settings)
    application = FastAPI(title="Homelab Telemetry Collector", version=__version__)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=list(active_settings.allowed_origins),
        allow_methods=["GET"],
        allow_headers=["*"],
    )
    application.state.store = active_store
    application.state.settings = active_settings

    @application.get("/api/health")
    def health() -> JSONResponse:
        storage_healthy = active_store.healthy()
        latest_by_source: dict[str, str] = {}
        if storage_healthy:
            for source in registry.source_names:
                try:
                    latest = active_store.current(source)
                except StorageUnavailable:
                    storage_healthy = False
                    break
                if latest is not None:
                    latest_by_source[source] = latest.received_at.isoformat()
        return JSONResponse(
            status_code=200 if storage_healthy else 503,
            content={
                "status": "healthy" if storage_healthy else "degraded",
                "version": __version__,
                "handlers": registry.names,
                "configured_sources": registry.source_names,
                "active_sources": sorted(latest_by_source),
                "active_source_count": len(latest_by_source),
                "last_received_at": max(latest_by_source.values(), default=None),
                "storage": {
                    "backend": active_settings.storage_backend,
                    "status": "healthy" if storage_healthy else "unavailable",
                },
            },
        )

    @application.post("/data/report/", status_code=202)
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
            active_store.write(envelope)
        except EcowittPayloadError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except StorageUnavailable as exc:
            raise HTTPException(status_code=503, detail={"code": "storage_unavailable"}) from exc
        return {
            "status": "accepted",
            "source": envelope.source,
            "observed_at": envelope.observed_at.isoformat(),
            "measurement_count": len(envelope.measurements),
        }

    @application.get("/api/current/{source}")
    def current(source: str) -> dict[str, object]:
        source = _source_slug(source)
        try:
            envelope = active_store.current(source)
        except StorageUnavailable as exc:
            raise HTTPException(status_code=503, detail={"code": "storage_unavailable"}) from exc
        if envelope is None:
            return {
                "schema_version": "1",
                "source": source,
                "status": "empty",
                "stale": True,
                "age_seconds": None,
                "data": None,
            }
        stale, age = _freshness(envelope, active_settings)
        return {
            "schema_version": "1",
            "source": source,
            "status": "stale" if stale else "current",
            "stale": stale,
            "age_seconds": age,
            "data": envelope.to_dict(),
        }

    @application.get("/api/history/{source}")
    def history(
        source: str,
        start: datetime | None = None,
        stop: datetime | None = None,
        limit: int = Query(default=100, ge=1, le=1000),
    ) -> dict[str, object]:
        source = _source_slug(source)
        stop = stop or datetime.now(timezone.utc)
        start = start or stop - timedelta(hours=24)
        if start.tzinfo is None or stop.tzinfo is None:
            raise HTTPException(status_code=422, detail="start and stop must include a timezone")
        if start >= stop:
            raise HTTPException(status_code=422, detail="start must be before stop")
        if stop - start > MAX_HISTORY_RANGE:
            raise HTTPException(status_code=422, detail="history range cannot exceed 31 days")
        try:
            records = active_store.history(source, start=start, stop=stop, limit=limit)
        except StorageUnavailable as exc:
            raise HTTPException(status_code=503, detail={"code": "storage_unavailable"}) from exc
        return {
            "schema_version": "1",
            "source": source,
            "status": "ok" if records else "empty",
            "count": len(records),
            "start": start.isoformat(),
            "stop": stop.isoformat(),
            "limit": limit,
            "data": [record.to_dict() for record in records],
        }

    return application


app = create_app()
