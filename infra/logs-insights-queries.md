# CloudWatch Logs Insights Queries
# Part D — infra/logs-insights-queries.md
#
# Log group: /aws/lambda/<stack-name>-canary
#
# Both queries below operate on the exact structured JSON log line emitted
# by src/canary/handler.py's `_log()` helper, once per check per invocation:
#
#   { "level": "INFO", "check": "products", "status_code": 200,
#     "latency_ms": 142, "timestamp": "2026-05-10T09:00:00Z" }
#
# CloudWatch Logs Insights parses top-level JSON fields automatically, so
# `latency_ms`, `check`, and `status_code` are queryable directly — no
# custom parse statement needed.

## Query 1 — Slow invocations (latency_ms > 500, last 1 hour)

```
fields @timestamp, check, latency_ms
| filter latency_ms > 500
| sort latency_ms desc
```

Run with the Logs Insights time range set to **Last 1 hour** (the query
itself doesn't encode a time window — that's a property of the query
execution request, set via the console time picker or the `startTime` /
`endTime` arguments to `StartQuery` in the CLI/SDK).

CLI equivalent:

```bash
aws logs start-query \
  --log-group-name "/aws/lambda/qa-canary-canary" \
  --start-time "$(date -u -v-1H +%s)" \
  --end-time "$(date -u +%s)" \
  --query-string 'fields @timestamp, check, latency_ms | filter latency_ms > 500 | sort latency_ms desc'
```

## Query 2 — Success vs failure count per hour (last 24 hours)

```
fields @timestamp, status_code
| filter ispresent(status_code)
| stats
    sum(status_code == 200) as successCount,
    sum(status_code != 200) as failureCount
  by bin(1h)
| sort bin(1h) asc
```

Run with the time range set to **Last 24 hours**.

`filter ispresent(status_code)` excludes the one log line the handler can
emit without a numeric status_code — the outer `"check": "canary", "level":
"ERROR"` safety-net line logged when an unexpected exception is caught in
`handler()` (status_code is null there, since no HTTP response was ever
received). That line is worth finding separately (see note below), but it
would otherwise inflate `failureCount` incorrectly since `null != 200` is
true.

Note: a non-2xx `status_code` (e.g. 400, 403, 500) and a `null` status_code
(connection/timeout failure, no response at all) are both "failed checks"
in the business sense, but they are distinguishable in the raw logs by
whether `status_code` is present — worth knowing if a future query needs to
separate "API responded with an error" from "API didn't respond at all".

CLI equivalent:

```bash
aws logs start-query \
  --log-group-name "/aws/lambda/qa-canary-canary" \
  --start-time "$(date -u -v-24H +%s)" \
  --end-time "$(date -u +%s)" \
  --query-string 'fields @timestamp, status_code | filter ispresent(status_code) | stats sum(status_code == 200) as successCount, sum(status_code != 200) as failureCount by bin(1h) | sort bin(1h) asc'
```
