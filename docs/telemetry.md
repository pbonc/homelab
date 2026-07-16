# Telemetry Platform

## Purpose

The Telemetry Platform is the homelab's shared ingestion, storage, query, and visualization layer. Ecowitt weather data is the first source, but weather-specific parsing remains inside an Ecowitt handler so later ADS-B, Docker, CI, radio, power, and application sources can reuse the platform contracts.

## Architecture

```text
Ecowitt gateway
    │ HTTP form POST /data/report/
    ▼
Telemetry Collector (:8000)
    ├── source registry and Ecowitt handler
    ├── normalized, versioned telemetry envelope
    ├── current/history/health REST APIs
    └── scoped InfluxDB writer
             │
             ▼
        InfluxDB (:8086)
             │
             ├── Grafana dashboard (:3001)
             ├── Homepage weather strip (:3000)
             └── labctl telemetry
```

The collector owns ingestion, validation, normalization, redaction, and freshness. InfluxDB owns durable time-series history. Consumers use the collector API or the provisioned read-only Grafana datasource rather than coupling themselves to Ecowitt field names.

## Source-handler contract

A source handler implements `telemetry_collector.sources.base.SourceHandler` and:

1. Declares stable `handler_name` and `source_name` values.
2. Determines a non-secret device identifier.
3. Parses the source timestamp or deliberately uses receipt time.
4. Converts known values into stable measurement names and units.
5. Preserves unknown, non-secret values under `extra_fields`.
6. Never logs or stores credentials such as Ecowitt `PASSKEY`.
7. Returns a versioned `TelemetryEnvelope` or a source-specific validation error.

The global registry rejects duplicate handler names and exposes configured public source names to health reporting. Ingestion routes select a registered handler; storage and query code remain source-neutral.

## Normalized envelope

```json
{
  "schema_version": "1",
  "source": "weather",
  "handler": "ecowitt",
  "device_id": "EasyWeatherPro_V5.2.7",
  "observed_at": "2026-07-16T20:05:04+00:00",
  "received_at": "2026-07-16T20:05:04.061202+00:00",
  "measurements": {
    "outdoor_temperature": {"value": 91.9, "unit": "degF"},
    "outdoor_humidity": {"value": 58.0, "unit": "percent"},
    "rain_rate": {"value": 0.0, "unit": "in/h"}
  },
  "extra_fields": {
    "runtime": "12345"
  }
}
```

Timestamps are timezone-aware ISO 8601 values. `observed_at` comes from the device when valid; `received_at` is assigned by the collector. Numeric measurements are written to InfluxDB as floats so whole-number readings cannot create field-type conflicts.

## Weather measurement catalog

| Measurement | Unit | Ecowitt fields |
| --- | --- | --- |
| `outdoor_temperature`, `indoor_temperature` | `degF` | `tempf`, `tempinf` |
| `outdoor_humidity`, `indoor_humidity` | `percent` | `humidity`, `humidityin` |
| `relative_pressure`, `absolute_pressure` | `inHg` | `baromrelin`, `baromabsin` |
| `wind_speed`, `wind_gust` | `mph` | `windspeedmph`, `windgustmph` |
| `wind_direction` | `degree` | `winddir` |
| `rain_rate` | `in/h` | `rainratein` or `rrain_piezo` |
| `rain_event`, `rain_hourly`, `rain_daily`, `rain_weekly`, `rain_monthly`, `rain_yearly` | `in` | conventional `*rainin` or WS90 `*rain_piezo` fields |
| `uv_index` | `index` | `uv` |
| `solar_radiation` | `W/m2` | `solarradiation` |
| `battery_*` | source-native | numeric fields containing `batt` |

Unknown values such as firmware, capacitor voltage, calibration gains, VPD, runtime, and heap data remain in `extra_fields` until their semantics are promoted into the normalized catalog. Secret-like fields are excluded.

## REST API

Interactive OpenAPI documentation is available at `http://192.168.1.23:8000/docs`.

| Method and path | Purpose | Important behavior |
| --- | --- | --- |
| `POST /data/report/` | Ecowitt form ingestion | Requires `application/x-www-form-urlencoded`; returns `202` after durable storage |
| `GET /api/health` | Platform and source health | Reports storage state, handlers, configured/active sources, count, and latest receipt time |
| `GET /api/current/{source}` | Latest source envelope | Returns explicit `current`, `stale`, or `empty` status and `age_seconds` |
| `GET /api/history/{source}` | Bounded history | Defaults to 24 hours; accepts timezone-aware `start`, `stop`, and `limit` |

History ranges cannot exceed 31 days and `limit` must be from 1 through 1,000. Source names must be lowercase slugs. Empty datasets return HTTP 200 with an explicit empty state. Validation failures use HTTP 415 or 422. Storage dependency failures return HTTP 503 with `{"code":"storage_unavailable"}`.

Examples:

```bash
curl -fsS http://127.0.0.1:8000/api/health
curl -fsS http://127.0.0.1:8000/api/current/weather
curl -fsS 'http://127.0.0.1:8000/api/history/weather?limit=10'
```

## Configuration and secrets

The committed `docker/telemetry/.env.example` documents runtime variables. The real `.env` and `docker/telemetry/secrets/` directory are ignored and exist only on `brain`.

| Variable | Purpose |
| --- | --- |
| `TELEMETRY_LOG_LEVEL` | Collector logging level |
| `TELEMETRY_STALE_AFTER_SECONDS` | Age at which current data becomes stale |
| `TELEMETRY_STORAGE_BACKEND` | `memory` for development or `influxdb` for deployment |
| `TELEMETRY_ALLOWED_ORIGINS` | Explicit Homepage origins allowed to read the collector API |
| `INFLUXDB_URL` | Internal InfluxDB URL |
| `INFLUXDB_ORG` | InfluxDB organization |
| `INFLUXDB_BUCKET` | Telemetry bucket |
| `INFLUXDB_RETENTION` | Initial bucket retention duration |
| `INFLUXDB_TOKEN_FILE` | Container path for a scoped token |
| `GRAFANA_ADMIN_USER` | Initial Grafana administrator username |

Secret files have distinct responsibilities:

| File | Access |
| --- | --- |
| `influxdb_admin_password.txt` | InfluxDB initialization only |
| `influxdb_admin_token.txt` | Authorization management only |
| `influxdb_collector_token.txt` | Read/write on the telemetry bucket |
| `influxdb_grafana_token.txt` | Read-only on the telemetry bucket |
| `grafana_admin_password.txt` | Grafana administrator login |

The secrets directory is host-private (`0700`). Individual files use `0644` because Compose file-backed secrets retain host permissions and the containers run as non-root users. The directory boundary prevents other host users from traversing to those files. Never print tokens in logs or command output.

Run `make telemetry-secrets` only for first-time initialization; it never overwrites existing files. Scoped InfluxDB tokens must be issued by InfluxDB after setup rather than generated as random strings.

## Deployment and Ecowitt setup

On `brain`:

```bash
cd /home/dar/git/homelab
make telemetry-secrets
make telemetry-config
docker compose --env-file docker/telemetry/.env \
  --file docker/telemetry/compose.yaml up -d --build
```

Configure EasyWeatherPro custom upload as follows:

| Setting | Value |
| --- | --- |
| Customized | Enable |
| Protocol Type Same As | Ecowitt |
| Server IP / Hostname | `192.168.1.23` |
| Path | `/data/report/` |
| Port | `8000` |
| Upload Interval | `60` seconds |

Do not include `:8000` in the hostname field while leaving Port set to 80. A successful report appears in collector logs as `POST /data/report/ ... 202 Accepted`.

## Grafana

Grafana provisions its InfluxDB datasource and `Homelab / Local Weather` dashboard from `docker/telemetry/grafana/`. The dashboard covers current conditions, temperature, humidity, wind, pressure, UV, solar radiation, battery voltage, report frequency, rain rate, and daily precipitation.

LAN users can view the dashboard anonymously with the `Viewer` role:

```text
http://192.168.1.23:3001/d/homelab-weather/local-weather
```

The administrator account remains available for configuration, and public sign-up is disabled. Grafana receives a read-only bucket token; an anonymous Viewer cannot write telemetry. Do not port-forward Grafana to the internet.

To extend dashboards, add or update a provisioned JSON file, retain the datasource UID `influxdb-telemetry`, use normalized measurement fields, filter the intended source/device, choose explicit units, and validate the JSON before deployment. Grafana's file provider reloads dashboard changes automatically.

## Homepage integration

Homepage contains cards for the Telemetry Collector, InfluxDB, Grafana, and Weather. Cards remain compact and use supported site-monitor checks. Detailed platform status stays in `labctl telemetry` rather than an expanded card.

The top weather strip reads `GET /api/current/weather` from the browser every five minutes and shows the most recent temperature, humidity, wind, rain rate, pressure, UV index, and observation time. Collector CORS is restricted to the configured Homepage origins. The strip links to Grafana for detailed history.

## Operations

Check the stack:

```bash
cd /home/dar/git/homelab
docker compose --env-file docker/telemetry/.env \
  --file docker/telemetry/compose.yaml ps
python3 -m labctl telemetry
curl -fsS http://127.0.0.1:8000/api/health
```

Inspect recent ingestion:

```bash
docker logs --since 10m telemetry-collector
curl -fsS http://127.0.0.1:8000/api/current/weather
```

Restart without deleting data:

```bash
docker compose --env-file docker/telemetry/.env \
  --file docker/telemetry/compose.yaml restart telemetry-collector influxdb grafana
```

Named volumes preserve InfluxDB and Grafana data. Do not use `down --volumes` during routine operations. The example retention is 30 days; production retention should be selected per data lifecycle, with separate long-lived buckets for data worth preserving.

Credential rotation is an administrative operation: issue replacement scoped authorizations, update the ignored secret files without printing values, recreate the dependent containers, verify read/write boundaries, and only then revoke superseded authorizations. Grafana's token must fail write attempts; the collector token must accept station reports.

## Troubleshooting

### Data is stale or the report counter stops

Check `/api/current/weather`, then inspect collector logs for the station IP. No request indicates a gateway/network problem. Repeated HTTP 503 responses indicate storage writes are failing even if the lightweight InfluxDB ping remains healthy.

### InfluxDB field-type conflict

InfluxDB fixes a field's type on first write. The collector therefore serializes all normalized numeric measurements as floats. A log or exception containing `field type conflict` means old incompatible data or a new handler violated that contract. Fix the serializer/handler first; do not repeatedly retry malformed writes. Deleting historical measurements is destructive and requires explicit approval.

### Collector cannot read a secret

`PermissionError: /run/secrets/...` means the host file is not readable by the non-root container. Confirm the secrets directory is `0700` and required file-backed secrets are `0644`, then recreate the affected container.

### Grafana shows no data

Confirm the datasource health endpoint reports success, the scoped Grafana token still has bucket read access, the dashboard uses UID `influxdb-telemetry`, and the query field exists in recent InfluxDB points. A newly normalized field has history only from the deployment that introduced it.

### Homepage weather is unavailable

Open the collector current endpoint directly, verify `access-control-allow-origin` matches the Homepage origin, and confirm the deployed `custom.js` uses the correct collector address. Hard-refresh the browser after a Homepage release.

### Grafana password and secret differ

Grafana's password file initializes a new database but does not automatically replace a password stored in an existing Grafana volume. Use the Grafana administrative CLI to synchronize the persisted admin account, then verify authenticated API access without printing the password.

## Adding the next telemetry source

The extension audit for Sprint 3 confirmed these seams:

1. Implement a handler under `telemetry_collector/sources/` using `SourceHandler`.
2. Register it in `telemetry_collector/registry.py`; duplicate handler names fail immediately.
3. Add a narrow ingestion route that validates the source transport and calls the registered handler.
4. Reuse `TelemetryEnvelope`, the `TelemetryStore` protocol, InfluxDB serialization, freshness calculation, and generic `/api/current/{source}` and `/api/history/{source}` routes.
5. Add fixtures and tests for normalization, secret redaction, unknown-field preservation, invalid payloads, and numeric field consistency.
6. Add a provisioned Grafana dashboard using normalized fields and the existing read-only datasource.
7. Add a compact Homepage summary only when it provides value without coupling Homepage to the source payload.
8. Update this catalog and operational runbook before live rollout.

Storage does not branch on source type. Health automatically discovers registered public source names. Query routes already accept safe generic source slugs. Grafana dashboards are independently provisioned files. Homepage integrations consume stable collector APIs. The only deliberately source-specific pieces are transport ingestion and normalization.

## Local development and validation

```bash
python -m pip install -r docker/telemetry-collector/requirements-dev.txt
make telemetry-test
make telemetry-run
```

The local collector listens on `http://127.0.0.1:8000` and defaults to in-memory storage unless configured otherwise. Before deployment, run the complete repository test suite, validate Compose with `make telemetry-config`, and verify the live stack with `python3 -m labctl telemetry`.
