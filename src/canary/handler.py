"""
src/canary/handler.py — Part D
================================
Lambda canary that monitors the DummyJSON API on a schedule.

The handler:
  1. Calls GET /products?limit=1 and POST /auth/login and measures the
     wall-clock latency of each in milliseconds.
  2. Publishes three CloudWatch metrics to the namespace QA/DummyJSON:
       - Availability      (Percent)      100 if both calls succeed, else 0
       - ProductsLatencyMs (Milliseconds)
       - AuthLatencyMs     (Milliseconds)
  3. Emits one structured JSON log line to stdout per check.
  4. Returns a summary dict — never raises an unhandled exception.

Uses only the Python standard library for the HTTP calls (urllib) plus
boto3, which ships with every AWS Lambda Python runtime image. Pulling in
`requests` would mean shipping a deployment package/layer for a single
GET and a single POST — not worth the packaging overhead for this canary.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from typing import Any

import boto3

DUMMYJSON_BASE_URL = "https://dummyjson.com"
NAMESPACE = "QA/DummyJSON"
REQUEST_TIMEOUT_SECONDS = 10

# DummyJSON's documented test credentials (see .env.example / assessment
# Part A). The canary is a read-only synthetic client — these are not
# secrets, they're the API's own published sample login.
AUTH_USERNAME = "emilys"
AUTH_PASSWORD = "emilyspass"

# DummyJSON's edge (Cloudflare) returns 403 Forbidden for requests with no
# User-Agent header — which is exactly what Python's urllib sends by
# default. Confirmed locally: identical request succeeds with this header
# set and fails without it. Without this, the canary would report
# Availability: 0 on every single invocation, not because the API is down,
# but because of client fingerprinting — a false positive that would page
# whoever is on the other end of CanaryAlertTopic for no real outage.
USER_AGENT = "qa-dummyjson-canary/1.0 (+synthetic-monitoring)"

_cloudwatch = None


def _cloudwatch_client():
    global _cloudwatch
    if _cloudwatch is None:
        _cloudwatch = boto3.client("cloudwatch")
    return _cloudwatch


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _log(check: str, status_code: int | None, latency_ms: float,
          level: str = "INFO", error: str | None = None) -> None:
    record: dict[str, Any] = {
        "level": level,
        "check": check,
        "status_code": status_code,
        "latency_ms": round(latency_ms),
        "timestamp": _now_iso(),
    }
    if error is not None:
        record["error"] = error
    print(json.dumps(record))


def _http_call(url: str, *, method: str, body: bytes | None = None,
                 required_field: str) -> tuple[int | None, float, str | None]:
    """Perform one HTTP call and classify the outcome.

    Returns (status_code, latency_ms, error). error is None on success;
    on any failure it is a human-readable string and status_code may be
    None (connection-level failure) or a non-2xx code (HTTP-level failure).
    """
    headers = {"User-Agent": USER_AGENT}
    if body is not None:
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=body, method=method, headers=headers)

    start = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            raw_body = response.read()
            latency_ms = (time.perf_counter() - start) * 1000
            status_code = response.status
    except urllib.error.HTTPError as exc:
        # A non-2xx response still carries a real status code and latency.
        latency_ms = (time.perf_counter() - start) * 1000
        return exc.code, latency_ms, f"HTTP {exc.code}: {exc.reason}"
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        # DNS failure, connection refused, timeout, etc. — no status code.
        latency_ms = (time.perf_counter() - start) * 1000
        return None, latency_ms, f"connection error: {exc}"

    try:
        parsed = json.loads(raw_body)
    except json.JSONDecodeError as exc:
        return status_code, latency_ms, f"malformed JSON response: {exc}"

    if not isinstance(parsed, dict) or required_field not in parsed:
        return status_code, latency_ms, f"response missing '{required_field}' field"

    return status_code, latency_ms, None


def _call_products() -> tuple[int | None, float, str | None]:
    return _http_call(
        f"{DUMMYJSON_BASE_URL}/products?limit=1",
        method="GET",
        required_field="products",
    )


def _call_auth() -> tuple[int | None, float, str | None]:
    payload = json.dumps({
        "username": AUTH_USERNAME,
        "password": AUTH_PASSWORD,
        "expiresInMins": 5,
    }).encode("utf-8")
    return _http_call(
        f"{DUMMYJSON_BASE_URL}/auth/login",
        method="POST",
        body=payload,
        required_field="accessToken",
    )


def _publish_metrics(availability: float, products_latency_ms: float,
                       auth_latency_ms: float) -> str | None:
    """Publish the three required metrics. Returns an error string on
    failure instead of raising — a metrics outage must not crash the
    canary or hide the fact that the checks themselves already ran."""
    try:
        _cloudwatch_client().put_metric_data(
            Namespace=NAMESPACE,
            MetricData=[
                {"MetricName": "Availability", "Value": availability, "Unit": "Percent"},
                {"MetricName": "ProductsLatencyMs", "Value": products_latency_ms, "Unit": "Milliseconds"},
                {"MetricName": "AuthLatencyMs", "Value": auth_latency_ms, "Unit": "Milliseconds"},
            ],
        )
        return None
    except Exception as exc:  # noqa: BLE001 — intentionally broad: any
        # boto3/network/permissions failure here must degrade gracefully.
        return f"failed to publish metrics: {exc}"


def _run_checks() -> dict[str, Any]:
    errors: list[str] = []

    products_status, products_latency_ms, products_error = _call_products()
    _log("products", products_status, products_latency_ms, error=products_error)
    if products_error:
        errors.append(f"products: {products_error}")

    auth_status, auth_latency_ms, auth_error = _call_auth()
    _log("auth", auth_status, auth_latency_ms, error=auth_error)
    if auth_error:
        errors.append(f"auth: {auth_error}")

    products_ok = products_error is None and products_status is not None and 200 <= products_status < 300
    auth_ok = auth_error is None and auth_status is not None and 200 <= auth_status < 300
    availability = 100.0 if (products_ok and auth_ok) else 0.0

    metrics_error = _publish_metrics(availability, products_latency_ms, auth_latency_ms)
    if metrics_error:
        errors.append(metrics_error)

    return {
        "healthy": availability == 100.0 and not errors,
        "checks": [
            {"name": "products", "status_code": products_status, "latency_ms": round(products_latency_ms, 2)},
            {"name": "auth", "status_code": auth_status, "latency_ms": round(auth_latency_ms, 2)},
        ],
        "errors": errors,
    }


def handler(event, context):
    """Lambda entry point. Every code path inside _run_checks() already
    catches its own exceptions; this outer guard is the last-resort net
    so a bug we didn't anticipate still returns a summary instead of
    crashing the invocation."""
    try:
        return _run_checks()
    except Exception as exc:  # noqa: BLE001 — required: the canary must never raise
        _log("canary", None, 0.0, level="ERROR", error=str(exc))
        return {
            "healthy": False,
            "checks": [],
            "errors": [f"unexpected canary failure: {exc}"],
        }
