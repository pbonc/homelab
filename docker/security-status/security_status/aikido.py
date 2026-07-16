from __future__ import annotations

import base64
import json
from collections.abc import Mapping
from urllib.parse import urlencode
from urllib.request import Request, urlopen


TOKEN_URL = "https://app.aikido.dev/api/oauth/token"
ISSUES_URL = "https://app.aikido.dev/api/public/v1/issues/export"
SEVERITIES = ("critical", "high", "medium", "low")


class AikidoError(RuntimeError):
    pass


def issue_items(payload: object) -> list[Mapping[str, object]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, Mapping)]
    if isinstance(payload, Mapping):
        for key in ("data", "items", "results", "issue_groups"):
            value = payload.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, Mapping)]
    raise AikidoError("Aikido returned an unsupported issue-list shape")


def issue_severity(issue: Mapping[str, object]) -> str | None:
    for key in ("severity", "severity_label", "severityLabel"):
        value = issue.get(key)
        if isinstance(value, str) and value.lower() in SEVERITIES:
            return value.lower()
    severity = issue.get("severity")
    if isinstance(severity, Mapping):
        for key in ("name", "label", "value"):
            value = severity.get(key)
            if isinstance(value, str) and value.lower() in SEVERITIES:
                return value.lower()
    return None


def severity_counts(items: list[Mapping[str, object]]) -> dict[str, int]:
    counts = {severity: 0 for severity in SEVERITIES}
    for item in items:
        severity = issue_severity(item)
        if severity:
            counts[severity] += 1
    return counts


def state_for(counts: Mapping[str, int]) -> str:
    if counts["critical"]:
        return "critical"
    if counts["high"]:
        return "high"
    if counts["medium"] or counts["low"]:
        return "low_medium"
    return "clear"


class AikidoClient:
    def __init__(self, client_id: str, client_secret: str, timeout: float = 15) -> None:
        self.client_id = client_id
        self.client_secret = client_secret
        self.timeout = timeout

    def _token(self) -> str:
        encoded = base64.b64encode(f"{self.client_id}:{self.client_secret}".encode()).decode()
        body = urlencode({"grant_type": "client_credentials"}).encode()
        request = Request(
            TOKEN_URL,
            data=body,
            headers={
                "Authorization": f"Basic {encoded}",
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
            },
        )
        with urlopen(request, timeout=self.timeout) as response:
            payload = json.load(response)
        token = payload.get("access_token") if isinstance(payload, Mapping) else None
        if not isinstance(token, str) or not token:
            raise AikidoError("Aikido token response did not contain an access token")
        return token

    def open_issue_counts(self) -> dict[str, int]:
        token = self._token()
        query = urlencode(
            {
                "format": "json",
                "per_page": 5000,
                "filter_status": "open",
            }
        )
        request = Request(
            f"{ISSUES_URL}?{query}",
            headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
        )
        with urlopen(request, timeout=self.timeout) as response:
            payload = json.load(response)
        return severity_counts(issue_items(payload))
