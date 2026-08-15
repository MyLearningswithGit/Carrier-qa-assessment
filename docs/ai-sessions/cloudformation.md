# AI Session Notes — Lambda Handler & CloudFormation (Part D)

Tool: Claude (Sonnet 5) via Claude Code. Task: implement
`src/canary/handler.py` and `infra/canary-stack.yaml` per the assessment's
exact metric/alarm/IAM specification.

## Lambda handler

Implemented per spec: two HTTP calls (`GET /products?limit=1`, `POST
/auth/login`), wall-clock latency via `time.perf_counter()`, structured
JSON log line per check, three CloudWatch metrics, summary dict, and a
"never raises" guarantee built in two layers — each HTTP/metrics call
catches its own specific exceptions, plus an outer `try/except Exception`
in `handler()` as a last-resort net.

Deliberately used stdlib `urllib.request` instead of `requests` — see
`AI_USAGE.md` §3 for the reasoning (avoids needing a Lambda layer for two
calls).

## The real bug: 403 Forbidden from urllib's default User-Agent

After writing the first version, it was actually invoked locally against
the live API (`handler({}, None)` in a Python REPL) rather than just
reviewed. Both calls came back `403 Forbidden` — not the expected `200`.

Diagnosis, in order:
1. Confirmed `curl https://dummyjson.com/products?limit=1` works fine
   (200) — so the API itself wasn't down.
2. Reproduced the failure directly with a bare `urllib.request` call
   (no custom headers) — also 403, isolating the problem to something
   about the Python request itself, not the endpoint.
3. Retried the same call with an explicit `User-Agent` header — 200.

Conclusion: DummyJSON's edge (Cloudflare, based on the response
characteristics) blocks requests with no `User-Agent`, which is exactly
what `urllib.request.Request` sends by default when none is set
explicitly. Fixed by adding a constant `USER_AGENT` string and setting it
on both requests.

This mattered beyond "the test now passes" — undetected, a deployed
canary in this state would report `Availability: 0` on literally every
invocation, forever, which is a false page waiting to happen on a system
that was never actually down. Documented in the handler's own comments
and in `README.md` §17 so a reviewer doesn't have to rediscover it.

## CloudFormation

Built resource-by-resource against the assessment's exact table (IAM
role, Lambda, `AWS::Scheduler::Schedule`, two alarms, SNS topic +
subscription). Two design points worth flagging for the interview:

- **`cloudwatch:PutMetricData` needs `Resource: "*"`.** This isn't a
  wildcard-permissions shortcut — this specific action has no
  resource-level ARN support in IAM at all. The actual least-privilege
  control used is a `Condition: {"StringEquals": {"cloudwatch:namespace":
  "QA/DummyJSON"}}`, which *is* enforceable and scopes the role to only
  this canary's metric namespace.
- **EventBridge Scheduler needs its own invocation role.** A schedule's
  `Target.RoleArn` is assumed by the Scheduler service to call
  `lambda:InvokeFunction` — it is not the same as, and must not be
  confused with, the Lambda's own execution role (which is assumed by the
  Lambda service to run the function code).

## Verification

- `cfn-lint infra/canary-stack.yaml` — first run produced one `W1030`
  warning (the placeholder `LambdaCodeS3Bucket` default,
  `REPLACE_WITH_YOUR_BUILD_BUCKET`, didn't match S3's bucket-naming
  pattern — uppercase/underscores aren't valid in bucket names). Fixed by
  changing the placeholder to `replace-with-your-build-bucket` (still an
  obvious placeholder, now syntactically valid). Second run: exit 0, no
  findings.
- Deliberately reverted the runtime to `python2.7` to confirm cfn-lint
  actually classifies a real problem as `Level: Error` (it does) before
  wiring that distinction into `run_checks.sh`'s pass/warn/fail logic —
  then reverted the change.
- No live `aws cloudformation deploy` was run — no AWS credentials are
  available in this environment. See `README.md` §18–19 for what was and
  wasn't validated.
