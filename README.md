# QA Assessment — Senior QA Automation Developer

A four-part QA automation submission covering API contract testing, unit
testing, browser automation, and an AWS reliability/monitoring layer, tied
together by a single orchestration script.

## 1. Project Overview

This repository monitors and tests two independent public systems:

- **[DummyJSON](https://dummyjson.com)** — a fake REST API, exercised by both
  a hand-written Bruno contract-test collection (Part A) and a Lambda
  synthetic canary (Part D).
- **[Sauce Demo](https://www.saucedemo.com)** — a demo e-commerce UI,
  exercised by a Playwright + Page Object Model test suite (Part C).

Plus a pure-Python unit test suite (Part B) for `src/api_checker.py`, the
response-validation utilities the canary uses before publishing metrics.

Everything is wired together by `run_checks.sh`, a single script that runs
all four parts and fails loudly — non-zero exit code — the moment anything
breaks.

## 2. Problem Statement

Testing a real system rarely means "write some tests" in one tool, once.
This assessment is built around the layers a production QA/SDET role
actually touches:

- **Contract testing** at the API boundary (Part A) — does the API's actual
  behavior match what every consumer of it assumes?
- **Unit testing** of pure logic (Part B) — validation/parsing code with no
  network dependency, so it must be provably correct in isolation.
- **UI/E2E automation** (Part C) — does the product work the way a real
  user experiences it, across browsers?
- **Production reliability monitoring** (Part D) — once something ships,
  how do you find out it broke *before* a user tells you?

Each part uses the tool that's actually right for the job, rather than one
framework stretched to cover everything.

## 3. Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  Part A: Bruno (.bru files)   ──HTTP──▶  dummyjson.com            │
│  Part B: pytest                ──(no network, pure functions)──▶  │
│                                           src/api_checker.py       │
│  Part C: Playwright (POM)     ──browser──▶  saucedemo.com          │
└─────────────────────────────────────────────────────────────────┘
                              │  (all three feed into)
                              ▼
                     run_checks.sh (orchestrator)
                              │
                              ▼
                     reports/ (HTML/JSON — gitignored contents)

┌─────────────────────────────────────────────────────────────────┐
│  Part D: AWS Reliability Layer (code-only deliverable — see §17)  │
│                                                                     │
│  EventBridge Scheduler (rate(5 min), created DISABLED)            │
│         │ invokes                                                  │
│         ▼                                                          │
│  Lambda Canary (src/canary/handler.py)                            │
│         │ calls                        │ writes                   │
│         ▼                              ▼                           │
│  DummyJSON API              CloudWatch Logs (structured JSON)      │
│         │ publishes metrics to                                    │
│         ▼                                                          │
│  CloudWatch (namespace QA/DummyJSON: Availability,                │
│               ProductsLatencyMs, AuthLatencyMs)                   │
│         │ evaluated by                                            │
│         ▼                                                          │
│  CloudWatch Alarms (AvailabilityAlarm, LatencyAlarm)               │
│         │ on breach, publish to                                   │
│         ▼                                                          │
│  SNS Topic (CanaryAlertTopic)                                     │
│         │ subscribed by                                           │
│         ▼                                                          │
│  Email (CanaryAlertEmail parameter)                                │
└─────────────────────────────────────────────────────────────────┘
```

## 4. Repository Structure

```
qa-assessment/
├── src/
│   ├── api_checker.py            # Provided — unmodified (Part B target)
│   └── canary/handler.py         # Part D — Lambda canary
├── collections/dummyjson/        # Part A — Bruno collection
│   ├── bruno.json                # provided manifest
│   ├── environments/local.bru    # provided — reads from .env
│   ├── auth/                     # login-valid (provided) + 2 negative cases
│   ├── products/                 # 6 request files
│   └── carts/                    # scaffolded, unused — see §16
├── tests/
│   ├── unit/test_api_checker.py  # Part B — 46 tests
│   └── ui/
│       ├── conftest.py           # screenshot-on-failure hook + login fixture
│       ├── pages/                # LoginPage, InventoryPage, CartPage, CheckoutPage
│       └── test_*.py             # 8 scenarios × 2 browsers = 16 tests
├── infra/
│   ├── canary-stack.yaml         # Part D — CloudFormation
│   └── logs-insights-queries.md  # Part D — 2 Logs Insights queries
├── reports/                      # generated by run_checks.sh — gitignored contents
│   └── screenshots/
├── docs/ai-sessions/             # Part E — conversation logs
├── run_checks.sh                 # orchestrates all four parts
├── AI_USAGE.md                   # Part E
├── .env.example                  # copy to .env
└── README.md
```

## 5. Technologies

| Layer | Tool |
|---|---|
| API contract tests | Bruno CLI (`@usebruno/cli`) |
| Unit tests | pytest, pytest-html |
| UI automation | Playwright (Python, sync API), pytest-playwright |
| AWS reliability | AWS Lambda (Python 3.12), boto3, CloudFormation |
| Template validation | cfn-lint |
| Orchestration | bash |

## 6. Prerequisites

- Python 3.12
- Node.js 18+ (for the Bruno CLI)
- `git`

## 7. Installation

```bash
pip install pytest pytest-html pytest-playwright cfn-lint boto3
playwright install chromium firefox
npm install -g @usebruno/cli
```

## 8. Environment Setup

```bash
cp .env.example .env
```

The DummyJSON credentials in `.env.example` are already filled in
(`emilys` / `emilyspass` — DummyJSON's own published test account). No
values need to be changed to run Parts A, B, or C.

The two AWS-related values (`AWS_DEFAULT_REGION`, `CANARY_ALERT_EMAIL`)
are informational defaults only — nothing in `run_checks.sh` or the
CloudFormation deploy flow reads `.env` for AWS configuration. Region and
identity come from your AWS CLI profile (§18); the alarm email is passed
explicitly via `--parameter-overrides CanaryAlertEmail=...` at deploy
time, not sourced from this file. Deliberately not wired together —
CloudFormation parameters passed explicitly on the command line are more
portable across developers/accounts than a shared `.env` value would be.

## 9. Running Part A — Bruno

```bash
cd collections/dummyjson
bru run . -r --env local --output ../../reports/bruno_report.json
```

**Note:** the assessment's documented invocation
(`bru run collections/dummyjson/ --env local ...` from the project root)
does not work with Bruno CLI v4.0.0 as installed — it errors with
`You can run only at the root of a collection`. This CLI version requires
its **working directory** to be the collection root (where `bruno.json`
lives), with `-r` to recurse into the `auth/` and `products/` subfolders.
`run_checks.sh` runs it this way automatically (`cd`'d inside a subshell,
so it doesn't affect the rest of the script).

**Result:** 9 requests, 27/27 tests, 3/3 assertions passing.

**Note on `environments/local.bru`:** running the collection causes the
Bruno CLI to rewrite this file's `accessToken` line on disk with the
freshly-issued token — this is triggered by the **provided**
`login-valid.bru`'s own `bru.setEnvVar("accessToken", ...)` script, not by
anything added in this submission, and happens even running that one file
in isolation. It's disclosed here rather than silently reverted-and-hidden:
after any local run, `git diff` will show `accessToken`'s value changed
(harmless — it's a fresh 30-minute JWT each time). Verified this doesn't
happen for anything added to the collection: `products/list-all.bru` needed
to hand its `total` value to `products/list-paginated.bru`, and does so
with `bru.setVar()` (run-scoped, in-memory) rather than `bru.setEnvVar()`
specifically because the latter was confirmed to persist to this file.

## 10. Running Part B — pytest

```bash
python3 -m pytest tests/unit/ -v --tb=short --html=reports/unit_report.html --self-contained-html
```

**Result:** 46/46 tests passing. No network access required — every input
is constructed inline in the test file.

## 11. Running Part C — Playwright

```bash
python3 -m pytest tests/ui/ -v --browser chromium --browser firefox --html=reports/ui_report.html --self-contained-html
```

**Result:** 16/16 tests passing (8 scenarios × 2 browsers). Runs headless
by default (pytest-playwright's default). On any failure, a full-page
screenshot is written to `reports/screenshots/{test_name}.png` — verified
by deliberately forcing a test failure during development and confirming
the file was written before removing the temporary test.

## 12. Validating Part D

The Lambda code and CloudFormation template are the deliverable — the
assessment explicitly does not require a live AWS deployment. What *was*
validated locally:

- `src/canary/handler.py` invoked directly (`handler({}, None)`) against
  the real DummyJSON API — confirmed both the success path (200/200,
  metrics attempted) and multiple failure paths (connection error, non-2xx,
  metrics-publish failure when no AWS credentials are present) all return
  a well-formed summary dict without raising.
- `infra/canary-stack.yaml` validated with `cfn-lint` (§13).
- The Logs Insights queries (`infra/logs-insights-queries.md`) were written
  against the exact JSON keys the handler actually emits, but **could not
  be executed against a real CloudWatch Logs Insights console** — that
  requires a deployed Lambda that has actually produced log data. See §16.

## 13. cfn-lint

```bash
cfn-lint infra/canary-stack.yaml
```

**Result:** exit code 0, no findings.

## 14. run_checks.sh

```bash
chmod +x run_checks.sh
./run_checks.sh
```

Runs Part B → Part A → Part C → cfn-lint, in that order, and stops
immediately (non-zero exit) at the first failure — verified during
development by deliberately breaking a unit test (script stopped at
Part B, never reached Part A) and by introducing a real cfn-lint error
via a deprecated Lambda runtime (correctly classified as `Level: Error`
and would fail the build; warnings-only findings are printed but do not
fail it, per the assessment's requirement).

cfn-lint's own exit code is a bitmask that conflates "warnings only" with
"failed" — the script captures its JSON output and branches on each
finding's actual `Level` instead of trusting the raw exit code.

## 15. Reports

Generated by `run_checks.sh` (or by running each part's command
individually):

- `reports/unit_report.html` — Part B
- `reports/bruno_report.json` — Part A
- `reports/ui_report.html` — Part C
- `reports/screenshots/*.png` — Part C, failure only

All are gitignored (generated at runtime) except the `reports/` and
`reports/screenshots/` directory structure itself.

## 16. Screenshots (Part C)

Captured automatically via a `pytest_runtest_makereport` hook in
`tests/ui/conftest.py` on any test failure — full-page, saved to
`reports/screenshots/{test_name}.png`. Since tests are parametrized across
two browsers, `{test_name}` includes the browser (e.g.
`test_foo[chromium]`), so failures in both browsers don't overwrite each
other.

## 17. AWS Architecture

See §3 diagram. Key design decisions, in the order an interviewer is
likely to ask about them:

- **`cloudwatch:PutMetricData` uses `Resource: "*"`** in the IAM policy —
  not a wildcard-permissions shortcut. This action has no resource-level
  ARN in IAM at all (AWS does not support scoping it by resource); the
  actual least-privilege control is the `Condition: cloudwatch:namespace
  == QA/DummyJSON`, restricting the role to publishing only this canary's
  metrics.
- **A second IAM role (`CanarySchedulerInvocationRole`) exists solely for
  EventBridge Scheduler** to invoke the Lambda — distinct from the
  Lambda's own execution role, because `AWS::Scheduler::Schedule` targets
  need their own assumed role.
- **The schedule is created `DISABLED`** per the assessment — deploying
  this template does not start incurring invocations or alarm evaluations
  until someone deliberately flips it on.
- **`TreatMissingData` differs between the two alarms**: `breaching` for
  `AvailabilityAlarm` (no data usually means the canary itself stopped
  running, which is itself a problem worth paging on), `notBreaching` for
  `LatencyAlarm` (a single missing datapoint against `EvaluationPeriods: 1`
  shouldn't page on a gap rather than a real spike).
- **The Lambda handler was found to need an explicit `User-Agent` header.**
  DummyJSON's edge (Cloudflare) returns `403 Forbidden` for requests with
  no `User-Agent` — which is exactly what Python's `urllib` sends by
  default. Confirmed locally: an identical request succeeds with the
  header set and fails without it. Without this fix, the deployed canary
  would report `Availability: 0` on every invocation — not because the
  API is down, but because of client fingerprinting. This would be a
  constant false page to whoever is subscribed to `CanaryAlertTopic`.

## 18. AWS Setup

Not executed in the current environment — no AWS account/credentials are
available here (see §19). The steps below are the documented path for
**any** developer to deploy this stack into **their own** AWS account.

Nothing in this repository is tied to a specific AWS account, region, or
identity. `src/canary/handler.py` calls `boto3.client("cloudwatch")` with
no explicit region, profile, or credentials — it relies entirely on
boto3's standard credential/region resolution (environment variables →
shared config/credentials files → IAM role, in the usual order).
`infra/canary-stack.yaml` never hard-codes an account ID or ARN; every
cross-resource reference uses `!Ref`, `!GetAtt`, or `!Sub` with
CloudFormation pseudo parameters (`${AWS::AccountId}`, `${AWS::Region}`,
`${AWS::StackName}`), and the Lambda's own IAM role is created *by* the
stack — nothing pre-existing is assumed. Two developers can deploy the
identical template into two different AWS accounts, each using their own
credentials, with zero code changes — only their own `--parameter-overrides`
and AWS CLI profile/region differ.

### 1. Install the AWS CLI

```bash
# macOS
brew install awscli
# Linux
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip" && unzip awscliv2.zip && sudo ./aws/install
# Windows (PowerShell)
msiexec.exe /i https://awscli.amazonaws.com/AWSCLIV2.msi
```

### 2. Configure your own credentials

Never paste credentials into this repository. Use the AWS CLI's own
config flow, which stores them outside the project (`~/.aws/credentials`
on macOS/Linux, `%USERPROFILE%\.aws\credentials` on Windows):

```bash
aws configure --profile qa-assessment
# prompts for Access Key ID, Secret Access Key, default region, output format
```

IAM Identity Center / SSO users can use `aws configure sso --profile
qa-assessment` instead. Either way, credentials never touch this repo.

### 3. Select your profile and region for this shell session

```bash
# macOS / Linux
export AWS_PROFILE=qa-assessment
export AWS_REGION=us-east-1        # any region you have access to — not fixed by the assessment

# Windows (PowerShell)
$env:AWS_PROFILE = "qa-assessment"
$env:AWS_REGION = "us-east-1"
```

### 4. Verify which identity/account you're about to deploy into

```bash
aws sts get-caller-identity
```

This prints the account ID, user/role ARN, and identity that every
subsequent command in this section will act as — confirm it's the
account you intend before deploying anything.

### 5. Package and deploy

This is a plain CloudFormation template (not SAM), so Lambda source is
referenced from S3 rather than inlined:

```bash
cd src && zip -r ../canary.zip canary/ && cd ..
aws s3 cp canary.zip s3://your-own-build-bucket/canary.zip   # bucket must already exist in your account

aws cloudformation deploy \
  --template-file infra/canary-stack.yaml \
  --stack-name qa-canary \
  --capabilities CAPABILITY_IAM \
  --parameter-overrides CanaryAlertEmail=your-own-email@example.com \
                         LambdaCodeS3Bucket=your-own-build-bucket \
                         LambdaCodeS3Key=canary.zip
```

`LambdaCodeS3Bucket`/`LambdaCodeS3Key`/`CanaryAlertEmail` default to
obvious placeholder values (not a real bucket or personal email) so the
template is syntactically valid and passes `cfn-lint` out of the box —
all three must be overridden with your own values for a real deploy.

### 6. Confirm the SNS email subscription

AWS sends a confirmation email to whatever address you passed as
`CanaryAlertEmail` immediately after the stack creates the subscription.
**No alarm notification is delivered until that confirmation link is
clicked** — this is SNS's own behavior, not something this stack can skip.

### 7. Verify the deployed resources

```bash
# Lambda exists and is configured as expected
aws lambda get-function --function-name qa-canary-canary

# Invoke it once manually (the EventBridge schedule is DISABLED by design — see §17)
aws lambda invoke --function-name qa-canary-canary --payload '{}' /tmp/canary-response.json --cli-binary-format raw-in-base64-out
cat /tmp/canary-response.json

# CloudWatch Logs — the structured JSON lines the handler printed
aws logs tail /aws/lambda/qa-canary-canary --since 5m

# CloudWatch metrics actually published
aws cloudwatch get-metric-statistics \
  --namespace QA/DummyJSON --metric-name Availability \
  --start-time "$(date -u -v-1H +%Y-%m-%dT%H:%M:%S 2>/dev/null || date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S)" \
  --end-time "$(date -u +%Y-%m-%dT%H:%M:%S)" \
  --period 300 --statistics Average

# Alarm state
aws cloudwatch describe-alarms --alarm-names qa-canary-AvailabilityAlarm qa-canary-LatencyAlarm
```

### 8. Clean up

CloudFormation should be the only thing that removes what it created —
don't manually delete individual resources:

```bash
aws cloudformation delete-stack --stack-name qa-canary
aws cloudformation wait stack-delete-complete --stack-name qa-canary   # optional, blocks until fully gone
```

Confirm nothing was left behind (the stack owns everything it created —
Lambda, both IAM roles, the log group, both alarms, the SNS topic and
subscription — so a successful `delete-stack` should leave no residual
billable resources).

### Optional: `demo_aws_live.sh`

Not part of the graded deliverable — Part D's requirement is the code and
template, not a deployment. This script exists purely as a narrated,
step-by-step walkthrough of the stack actually running in a real AWS
account (resources → schedule state → live Lambda invoke → logs →
metrics → alarms → SNS), pausing between each step for live narration.
Requires the stack already deployed per the steps above:

```bash
chmod +x demo_aws_live.sh
./demo_aws_live.sh
```

## 19. Known Limitations

- **No live AWS deployment.** The stack was validated with `cfn-lint` and
  the handler was validated by direct local invocation against the real
  DummyJSON API — but end-to-end behavior (actual metric publication,
  actual alarm evaluation, actual SNS email delivery) has not been
  observed in a running AWS account. This environment has no AWS
  credentials.
- **The Logs Insights queries are unexecuted** for the same reason — they
  were written to match the handler's actual log schema, but there's no
  deployed Lambda generating real log data to query against.
- **Bruno CLI v4 requires a working-directory quirk** — see §9. Documented
  rather than silently worked around without disclosure.
- **This dev machine's Python install initially failed SSL verification**
  against `dummyjson.com` (missing local CA bundle, a known Python.org-on-macOS
  issue unrelated to the handler code) — worked around locally with
  `certifi` purely for testing; not a change to the shipped handler.

## 20. DummyJSON Mocked Write-Operation Behavior

`POST /products/add` (used in both Part A's `products/add.bru` and
implicitly relevant to Part D's write-path reasoning) is **mocked** by
DummyJSON: it returns a plausible response — the submitted fields echoed
back plus a generated `id` — but nothing persists server-side. A follow-up
`GET /products/{new id}` would 404. Both the Bruno test and this README
treat this as a response-contract check only; no test in this repository
asserts persistence across requests for a write endpoint.

## 21. AI Usage

See [`AI_USAGE.md`](AI_USAGE.md) and [`docs/ai-sessions/`](docs/ai-sessions/)
for the full accounting of AI-assisted work on this submission, including
concrete decisions accepted/rejected and one genuine AI-produced defect
(the missing `User-Agent` header discussed in §17) that was caught by
actually running the code against the live API, not by inspection alone.

## 22. CI/CD

Not yet implemented in this snapshot of the repository. Planned as the
first optional stretch goal (GitHub Actions running `run_checks.sh` on
every push) — this section will be updated once that lands.

## 23. Optional Stretch Goals

Not yet implemented. Only Locust, a Slack alert Lambda, and Schemathesis
remain unaddressed after GitHub Actions — all are explicitly optional,
discussion-starter items per the assessment, not graded.
