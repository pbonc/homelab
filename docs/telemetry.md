# Telemetry Platform

## Purpose

The Telemetry Platform is the homelab's shared ingestion, storage, query, and visualization layer. Ecowitt weather data is its first source, but weather-specific behavior remains inside an Ecowitt handler so ADS-B, Docker, CI, radio, power, and application sources can use the same platform contracts.

## Initial architecture

```text
Ecowitt gateway
    │ HTTP form POST /data/report/
    ▼
Telemetry Collector
    ├── source registry
    ├── Ecowitt handler
    ├── normalized telemetry envelope
    ├── current/history REST API
    └── InfluxDB writer
             │
             ├── Grafana dashboards
             ├── Homepage summaries
             └── labctl telemetry
```

The collector owns ingestion and normalization. InfluxDB owns durable time-series history. Consumers use the collector API or a provisioned InfluxDB datasource rather than coupling themselves to Ecowitt field names.

## Source plugin contract

A source handler:

1. Declares a stable handler name and public source name.
2. Determines a non-secret device identifier from the source payload or configuration.
3. Parses the source timestamp or deliberately falls back to receipt time.
4. Converts known values into the normalized measurement catalog.
5. Preserves unknown, non-secret values under `extra_fields`.
6. Never logs or stores credentials such as Ecowitt `PASSKEY`.
7. Returns a versioned `TelemetryEnvelope` or a specific validation error.

Adding a source means implementing this interface and registering its ingestion route. Core storage and consumer code must not branch on weather-specific field names.

## Normalized envelope

```json
{
  "schema_version": "1",
  "source": "weather",
  "handler": "ecowitt",
  "device_id": "GW2000A",
  "observed_at": "2026-07-15T18:30:00+00:00",
  "received_at": "2026-07-15T18:30:02+00:00",
  "measurements": {
    "outdoor_temperature": {"value": 76.0, "unit": "degF"},
    "outdoor_humidity": {"value": 61, "unit": "percent"}
  },
  "extra_fields": {
    "runtime": "12345"
  }
}
```

Timestamps are UTC ISO 8601 values. `observed_at` is the device timestamp when valid; `received_at` is assigned by the collector. Measurement keys and units are stable API contracts.

## Initial measurement catalog

| Measurement | Unit | Typical Ecowitt field |
| --- | --- | --- |
| `outdoor_temperature` | `degF` | `tempf` |
| `indoor_temperature` | `degF` | `tempinf` |
| `outdoor_humidity` | `percent` | `humidity` |
| `indoor_humidity` | `percent` | `humidityin` |
| `relative_pressure` | `inHg` | `baromrelin` |
| `absolute_pressure` | `inHg` | `baromabsin` |
| `wind_speed` | `mph` | `windspeedmph` |
| `wind_gust` | `mph` | `windgustmph` |
| `wind_direction` | `degree` | `winddir` |
| `rain_rate` | `in/h` | `rainratein` |
| `rain_event`, `rain_hourly`, `rain_daily`, `rain_weekly`, `rain_monthly`, `rain_yearly` | `in` | corresponding `*rainin` field |
| `uv_index` | `index` | `uv` |
| `solar_radiation` | `W/m2` | `solarradiation` |

Battery fields vary by sensor and remain source-specific initially. They are preserved with a `battery_` normalized key when numeric and retained in `extra_fields` when their semantics are unknown.

## API conventions

- Health is always `GET /api/health`.
- Current values are `GET /api/current/{source}` and include explicit `current`, `stale`, or `empty` state plus age in seconds.
- History is `GET /api/history/{source}` with timezone-aware `start` and `stop`, a maximum 31-day range, and a `limit` from 1 through 1,000.
- Source names are stable lowercase slugs such as `weather`, `adsb`, and `docker`.
- Successful responses include `schema_version`, `source`, data, and freshness metadata.
- Empty data is a successful response with an explicit empty/stale state; dependency failures use non-2xx responses with a stable error code.

## Configuration and secrets

Runtime configuration is supplied through environment variables. A committed `.env.example` documents required values; the real `.env` file is ignored by Git and stored only on `brain`.

Planned variables:

| Variable | Purpose |
| --- | --- |
| `TELEMETRY_LOG_LEVEL` | Collector logging level |
| `TELEMETRY_STALE_AFTER_SECONDS` | Freshness threshold |
| `INFLUXDB_URL` | Internal InfluxDB endpoint |
| `INFLUXDB_ORG` | InfluxDB organization |
| `INFLUXDB_BUCKET` | Telemetry bucket |
| `INFLUXDB_TOKEN` | Collector write/query token; secret |
| `INFLUXDB_TOKEN_FILE` | Preferred Docker secret-file path for the token |
| `GRAFANA_ADMIN_USER` | Initial Grafana administrator; secret |
| `GRAFANA_ADMIN_PASSWORD` | Initial Grafana password; secret |

Secrets must not appear in Compose YAML, fixtures, logs, API responses, dashboards, or release metadata.

## Storage contract

The initial InfluxDB measurement is `telemetry`. Tags identify `source`, `handler`, and `device_id`; normalized values become numeric fields. Source-specific extras use a `raw_` prefix so they cannot collide with normalized fields. A redacted serialized envelope supports lossless API reconstruction. Device observation time is the point timestamp and receipt time is retained for delay/freshness calculations.

## Container runtime

`docker/telemetry/compose.yaml` defines InfluxDB 2.9.1, the collector, and Grafana OSS 12.4.0. Upstream images and the collector base image are digest-pinned. InfluxDB and Grafana use named volumes. InfluxDB setup creates the `homelab` organization and a configurable `telemetry` bucket. The example environment starts with a 30-day retention period; production retention should be chosen per data lifecycle, with long-lived buckets used for data worth preserving.

Run `make telemetry-secrets` once on the deployment host to create the ignored `.env` and Docker secret files. Existing configuration and secrets are never overwritten. The secrets directory is host-private (`0700`); individual files are readable by the non-root container users only when bind-mounted. Validate the resolved model with `make telemetry-config`.

## Extension points

- Source handlers live under `telemetry_collector/sources/` and register through the source registry.
- InfluxDB translation is isolated behind a storage interface.
- API routes address generic source slugs.
- Grafana provisioning uses one file per datasource or dashboard.
- Homepage consumes stable collector APIs, not Ecowitt payloads.

Deployment, operations, Ecowitt gateway configuration, dashboards, and troubleshooting will be completed as their implementation slices land.

## Local development

Install the pinned development dependencies in a virtual environment, run the tests, and start the API:

```bash
python -m pip install -r docker/telemetry-collector/requirements-dev.txt
make telemetry-test
make telemetry-run
```

The local collector listens on `http://127.0.0.1:8000`. In-memory current data is intentionally temporary in this first vertical slice; InfluxDB becomes the durable source of truth in the storage slice.
