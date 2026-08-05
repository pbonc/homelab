from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Response:
    content_type: str
    body: str


@dataclass(frozen=True)
class Profile:
    title: str
    accent: str
    server_header: str
    routes: dict[str, Response]


def page(title: str, heading: str, copy: str, accent: str) -> Response:
    return Response(
        "text/html; charset=utf-8",
        f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title><style>
body{{margin:0;background:#f4f1e8;color:#243128;font:16px system-ui,sans-serif}}
main{{max-width:760px;margin:12vh auto;padding:2.5rem;border-top:8px solid {accent};background:#fff;box-shadow:0 12px 35px #2332}}
h1{{font-family:Georgia,serif;font-size:2.4rem;margin:.2rem 0}}p{{line-height:1.6}}small{{color:#657168}}
</style></head><body><main><small>Trailhead partner network</small><h1>{heading}</h1><p>{copy}</p></main></body></html>""",
    )


PROFILES = {
    "documentation": Profile(
        "Field Manual",
        "#b7652a",
        "FieldManual/2.4",
        {
            "/": page("Field Manual", "Outfitter field manual", "Operating notes for approved rental partners.", "#b7652a"),
            "/guides": page("Guides", "Equipment guides", "Current handling and fitting notes are available to partner staff.", "#b7652a"),
        },
    ),
    "status": Profile(
        "Trail Status",
        "#287271",
        "TrailWatch/1.8",
        {
            "/": page("Trail Status", "All systems operational", "Reservation and inventory services are responding normally.", "#287271"),
            "/api/status": Response("application/json", '{"reservation":"operational","inventory":"operational"}'),
        },
    ),
    "marketing": Profile(
        "Summit Weekends",
        "#8a4f7d",
        "SummitWeb/3.1",
        {
            "/": page("Summit Weekends", "Cabins made for long weekends", "Seasonal packages from a fictional Trailhead partner.", "#8a4f7d"),
            "/cabins": page("Cabins", "Three quiet basecamps", "Synthetic listings only. Reservations open next season.", "#8a4f7d"),
        },
    ),
    "inventory_api": Profile(
        "Gear Stock API",
        "#355caa",
        "StockroomAPI/1.2",
        {
            "/": Response("application/json", '{"service":"gear-stock","docs":"/api/inventory"}'),
            "/api/inventory": Response("application/json", '[{"sku":"PADDLE-DEMO","available":12},{"sku":"TENT-DEMO","available":7}]'),
        },
    ),
    "employee_login": Profile(
        "Crew Access",
        "#374537",
        "CrewGate/4.0",
        {
            "/": page("Crew Access", "Employee access", "Authorized staff use the protected identity provider.", "#374537"),
            "/login": page("Sign in", "Single sign-on required", "Local passwords are not accepted on this service.", "#374537"),
        },
    ),
    "maintenance": Profile(
        "Service Bench",
        "#a33d32",
        "ServiceBench/2.0",
        {
            "/": page("Service Bench", "Maintenance queue", "Work-order summaries require authenticated shop access.", "#a33d32"),
            "/work-orders": Response("application/json", '{"error":"authentication_required"}'),
        },
    ),
    "secure_catalog": Profile(
        "Outfitter Catalog",
        "#1d6d4f",
        "CatalogEdge/5.3",
        {
            "/": page("Outfitter Catalog", "Partner equipment catalog", "A small read-only catalog with intentionally minimal data.", "#1d6d4f"),
            "/api/catalog": Response("application/json", '[{"id":"demo-1","name":"Day Pack"},{"id":"demo-2","name":"Camp Chair"}]'),
        },
    ),
}
