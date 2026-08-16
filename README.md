# QA Assessment — Senior QA Automation Developer

A four-part QA automation submission covering API contract testing, unit
testing, browser automation, and an AWS reliability/monitoring layer, tied
together by a single orchestration script — plus a fifth part documenting
how AI tools were used to build it.

**Fastest path to verifying this submission:**

```bash
git clone <this-repo-url> && cd qa-assessment
pip install pytest pytest-html pytest-playwright cfn-lint boto3
playwright install chromium firefox
npm install -g @usebruno/cli
cp .env.example .env
chmod +x run_checks.sh
./run_checks.sh
```

That single script runs every part the assessment requires (pytest, Bruno,
Playwright, cfn-lint) and exits non-zero the instant anything fails. Full
detail on every step below.

## Table of Contents

1. [Requirements Compliance Checklist](#1-requirements-compliance-checklist) — the fastest way to confirm this matches `Candidate_Assessment.pdf`
2. [Project Overview](#2-project-overview)
3. [Problem Statement](#3-problem-statement)
4. [Architecture](#4-architecture)
5. [Repository Structure](#5-repository-structure)
6. [Technologies](#6-technologies)
7. [Prerequisites](#7-prerequisites)
8. [Installation](#8-installation)
9. [Environment Setup](#9-environment-setup)
10. [Running Part A — Bruno](#10-running-part-a--bruno)
11. [Running Part B — pytest](#11-running-part-b--pytest)
12. [Running Part C — Playwright](#12-running-part-c--playwright)
13. [Part D — Local Validation](#13-part-d--local-validation)
14. [Part D — Live AWS Validation](#14-part-d--live-aws-validation)
15. [cfn-lint](#15-cfn-lint)
16. [run_checks.sh](#16-run_checkssh)
17. [Reports](#17-reports)
18. [Screenshots (Part C)](#18-screenshots-part-c)
19. [AWS Architecture — Design Decisions](#19-aws-architecture--design-decisions)
20. [AWS Setup — Deploy Into Your Own Account](#20-aws-setup--deploy-into-your-own-account)
21. [Known Limitations](#21-known-limitations)
22. [DummyJSON Mocked Write-Operation Behavior](#22-dummyjson-mocked-write-operation-behavior)
23. [AI Usage](#23-ai-usage)
24. [CI/CD](#24-cicd)
25. [Optional Stretch Goals](#25-optional-stretch-goals)

---

## 1. Requirements Compliance Checklist

Every row below maps directly to a requirement in `Candidate_Assessment.pdf`
— file to open, and the exact command that proves it. This is the fastest
way to confirm the submission matches the assessment without reading
anything else first.

### Part A — Bruno API Contract Tests

| Requirement | File | Verify |
|---|---|---|
| Wrong password → 400 + `message` | `collections/dummyjson/auth/login-wrong-password.bru` | [§10](#10-running-part-a--bruno) |
| Missing `username` field → 400 | `collections/dummyjson/auth/login-missing-field.bru` | [§10](#10-running-part-a--bruno) |
| `GET /products` — array, total>0, per-item contract | `collections/dummyjson/products/list-all.bru` | [§10](#10-running-part-a--bruno) |
| `GET /products?limit=5&skip=10` — exact count + total consistency | `collections/dummyjson/products/list-paginated.bru` | [§10](#10-running-part-a--bruno) |
| `GET /products/1` — 200, id/price/rating checks | `collections/dummyjson/products/get-by-id.bru` | [§10](#10-running-part-a--bruno) |
| `GET /products/9999999` — 404 + `message` | `collections/dummyjson/products/get-not-found.bru` | [§10](#10-running-part-a--bruno) |
| Case-insensitive search | `collections/dummyjson/products/search.bru` | [§10](#10-running-part-a--bruno) |
| Mocked add endpoint, response-contract only | `collections/dummyjson/products/add.bru` | [§10](#10-running-part-a--bruno) |
| `login-valid.bru` reviewed, not duplicated | `collections/dummyjson/auth/login-valid.bru` (provided, untouched) | `git log --follow` shows no diff |

### Part B — Python Unit Tests

| Requirement | File | Verify |
|---|---|---|
| `validate_product` — valid/invalid/boundary/type coverage | `tests/unit/test_api_checker.py::TestValidateProduct` (24 cases) | [§11](#11-running-part-b--pytest) |
| `calculate_cart_total` — same | `tests/unit/test_api_checker.py::TestCalculateCartTotal` (13 cases) | [§11](#11-running-part-b--pytest) |
| `parse_auth_response` — same | `tests/unit/test_api_checker.py::TestParseAuthResponse` (9 cases) | [§11](#11-running-part-b--pytest) |
| At least one `@pytest.mark.parametrize` group | 3 parametrized groups (invalid ids, invalid prices, invalid quantities) | `grep -c parametrize tests/unit/test_api_checker.py` |
| `src/api_checker.py` unmodified | Same file, byte-identical to the starter | `git log --follow -- src/api_checker.py` |

### Part C — Playwright UI Automation

| Requirement | File | Verify |
|---|---|---|
| Page Object Model, min. 3 classes | `tests/ui/pages/{login_page,inventory_page,cart_page,checkout_page}.py` (4 classes) | [§12](#12-running-part-c--playwright) |
| Standard login → inventory, title check | `tests/ui/test_auth.py` | [§12](#12-running-part-c--playwright) |
| Locked-out user, exact message | `tests/ui/test_auth.py` | [§12](#12-running-part-c--playwright) |
| Empty credentials, error shown | `tests/ui/test_auth.py` | [§12](#12-running-part-c--playwright) |
| All 6 products visible | `tests/ui/test_inventory.py` | [§12](#12-running-part-c--playwright) |
| Add two by name → badge | `tests/ui/test_cart.py` | [§12](#12-running-part-c--playwright) |
| Remove by name → badge + list update | `tests/ui/test_cart.py` | [§12](#12-running-part-c--playwright) |
| End-to-end checkout | `tests/ui/test_checkout.py` | [§12](#12-running-part-c--playwright) |
| Performance-glitch timing, monotonic clock | `tests/ui/test_performance.py` | [§12](#12-running-part-c--playwright) |
| Chromium + Firefox, headless | `pytest-playwright --browser` ×2 | [§12](#12-running-part-c--playwright) |
| Screenshot on failure | `tests/ui/conftest.py` | [§18](#18-screenshots-part-c) |

### Part D — AWS Reliability Layer

| Requirement | File | Verify |
|---|---|---|
| Lambda: 2 checks, latency, 3 metrics, structured logs, safe summary | `src/canary/handler.py` | [§13](#13-part-d--local-validation), [§14](#14-part-d--live-aws-validation) |
| CloudFormation: IAM least-privilege, Lambda, Scheduler, alarms, SNS | `infra/canary-stack.yaml` | [§15](#15-cfn-lint), [§19](#19-aws-architecture--design-decisions) |
| EventBridge Schedule, `rate(5 minutes)`, `DISABLED` | `infra/canary-stack.yaml` (`CanarySchedule`) | [§14](#14-part-d--live-aws-validation) |
| `AvailabilityAlarm` — Avg, 300s, 2 periods, <99 | `infra/canary-stack.yaml` | [§19](#19-aws-architecture--design-decisions) |
| `LatencyAlarm` — p90, 300s, 1 period, >1000ms | `infra/canary-stack.yaml` | [§19](#19-aws-architecture--design-decisions) |
| SNS topic + email subscription | `infra/canary-stack.yaml` | [§14](#14-part-d--live-aws-validation) |
| 2 Logs Insights queries | `infra/logs-insights-queries.md` | [§14](#14-part-d--live-aws-validation) |

### Orchestration, Docs, and Part E

| Requirement | File | Verify |
|---|---|---|
| `run_checks.sh` — 4 chained checks, fail-fast | `run_checks.sh` | [§16](#16-run_checkssh) |
| `AI_USAGE.md` — 4 required sections | `AI_USAGE.md` | [§23](#23-ai-usage) |
| 3 named AI session logs | `docs/ai-sessions/{unit-test-design,cloudformation,bruno-assertions}.md` | [§23](#23-ai-usage) |
| Reports from at least one full run of each part | `reports/` (generated — run `./run_checks.sh` to populate) | [§17](#17-reports) |

---

## 2. Project Overview

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

## 3. Problem Statement

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

## 4. Architecture

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
│  Part D: AWS Reliability Layer — deployed and validated, see [§14](#14-part-d--live-aws-validation)  │
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

## 5. Repository Structure

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
│   └── carts/                    # scaffolded, unused — see [§21](#21-known-limitations)
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
├── demo_aws_live.sh              # optional — narrated live AWS demo, see [§20](#20-aws-setup--deploy-into-your-own-account)
├── AI_USAGE.md                   # Part E
├── .env.example                  # copy to .env
└── README.md
```

## 6. Technologies

| Layer | Tool |
|---|---|
| API contract tests | Bruno CLI (`@usebruno/cli`) |
| Unit tests | pytest, pytest-html |
| UI automation | Playwright (Python, sync API), pytest-playwright |
| AWS reliability | AWS Lambda (Python 3.12), boto3, CloudFormation |
| Template validation | cfn-lint |
| Orchestration | bash |

## 7. Prerequisites

- Python 3.12
- Node.js 18+ (for the Bruno CLI)
- `git`
- AWS CLI (only if you intend to actually deploy Part D — see [§20](#20-aws-setup--deploy-into-your-own-account))

## 8. Installation

```bash
pip install pytest pytest-html pytest-playwright cfn-lint boto3
playwright install chromium firefox
npm install -g @usebruno/cli
```

## 9. Environment Setup

```bash
cp .env.example .env
```

The DummyJSON credentials in `.env.example` are already filled in
(`emilys` / `emilyspass` — DummyJSON's own published test account). No
values need to be changed to run Parts A, B, or C.

The two AWS-related values (`AWS_DEFAULT_REGION`, `CANARY_ALERT_EMAIL`)
are informational defaults only — nothing in `run_checks.sh` or the
CloudFormation deploy flow reads `.env` for AWS configuration. Region and
identity come from your AWS CLI profile ([§20](#20-aws-setup--deploy-into-your-own-account)); the alarm email is passed
explicitly via `--parameter-overrides CanaryAlertEmail=...` at deploy
time, not sourced from this file. Deliberately not wired together —
CloudFormation parameters passed explicitly on the command line are more
portable across developers/accounts than a shared `.env` value would be.

## 10. Running Part A — Bruno

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

**Using the Bruno Desktop app instead of the CLI:** select the **`local`**
environment from the dropdown top-right — it defaults to "No Environment,"
which causes every request to fail with `getaddrinfo ENOTFOUND {{baseUrl}}`
(there's nothing to resolve the template against). If it still fails after
selecting `local`, the app was likely launched without `.env` loaded —
`environments/local.bru` reads `{{process.env.DUMMYJSON_URL}}`, an actual
OS-level environment variable, which the CLI gets from `source .env`
but a GUI app launched from Finder/Dock never sees. Launch it from a
terminal that already has `.env` sourced instead:
```bash
set -o allexport && source .env && set +o allexport && open -a Bruno
```

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

## 11. Running Part B — pytest

```bash
python3 -m pytest tests/unit/ -v --tb=short --html=reports/unit_report.html --self-contained-html
```

**Result:** 46/46 tests passing. No network access required — every input
is constructed inline in the test file.

## 12. Running Part C — Playwright

```bash
python3 -m pytest tests/ui/ -v --browser chromium --browser firefox --html=reports/ui_report.html --self-contained-html
```

**Result:** 16/16 tests passing (8 scenarios × 2 browsers). Runs headless
by default (pytest-playwright's default). On any failure, a full-page
screenshot is written to `reports/screenshots/{test_name}.png` — verified
by deliberately forcing a test failure during development and confirming
the file was written before removing the temporary test.

## 13. Part D — Local Validation

The Lambda code and CloudFormation template are the deliverable — the
assessment explicitly does not require a live AWS deployment. What *was*
validated locally, without any AWS account:

- `src/canary/handler.py` invoked directly (`handler({}, None)`) against
  the real DummyJSON API — confirmed both the success path (200/200,
  metrics attempted) and multiple failure paths (connection error, non-2xx,
  metrics-publish failure when no AWS credentials are present) all return
  a well-formed summary dict without raising.
- `infra/canary-stack.yaml` validated with `cfn-lint` ([§15](#15-cfn-lint)).

## 14. Part D — Live AWS Validation

Beyond what the assessment requires: this stack was actually **deployed
into a real AWS account** and fully exercised end-to-end, then torn down
afterward to avoid unnecessary cost. It is not currently deployed — the
commands below reproduce exactly what was done and verified.

| Step | Result observed |
|---|---|
| `aws cloudformation deploy` | `CREATE_COMPLETE`, all 9 resources |
| EventBridge Schedule state | Confirmed `DISABLED`, as designed |
| Manual Lambda invoke | `{"healthy": true, "checks": [{"name": "products", "status_code": 200, ...}, {"name": "auth", "status_code": 200, ...}], "errors": []}` |
| CloudWatch Logs | Exact structured JSON lines, matching the assessment's required format |
| CloudWatch Metrics | All 3 published with real values: `Availability=100.0`, `ProductsLatencyMs≈433ms`, `AuthLatencyMs≈40ms` |
| CloudWatch Alarms | Both observed — `LatencyAlarm` stayed `OK`; `AvailabilityAlarm` briefly went to `ALARM` because the schedule was disabled and only sparse manual invocations existed, exactly matching its deliberate `TreatMissingData: Breaching` design, then self-corrected |
| SNS subscription | Confirmed (`SubscriptionArn` resolved to a real ARN, not `PendingConfirmation`) |
| `aws cloudformation delete-stack` | Confirmed fully removed afterward |

**One real bug was found and fixed during this process**: the first
packaging attempt zipped `src/canary/` from inside `src/`, producing
`canary/handler.py` at the zip root — but the template's
`Handler: src/canary/handler.handler` requires `src/canary/handler.py`.
`cfn-lint` cannot catch this; it's a packaging problem, not a template
problem. The corrected command is used throughout [§20](#20-aws-setup--deploy-into-your-own-account) below. See
[`AI_USAGE.md` §4](AI_USAGE.md#section-4--things-ai-got-wrong) for the full diagnosis.

**To reproduce:** see [§20](#20-aws-setup--deploy-into-your-own-account) for the full deploy → verify → clean-up cycle,
and `demo_aws_live.sh` for a narrated, step-by-step version of the
verification stage.

## 15. cfn-lint

```bash
cfn-lint infra/canary-stack.yaml
```

**Result:** exit code 0, no findings.

## 16. run_checks.sh

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

Note: `run_checks.sh` intentionally never touches AWS — Part D's local
validation there is `cfn-lint` only (static). The live AWS deployment in
[§14](#14-part-d--live-aws-validation) is separate, additional verification beyond what's required or what
this script performs.

## 17. Reports

Generated by `run_checks.sh` (or by running each part's command
individually):

- `reports/unit_report.html` — Part B
- `reports/bruno_report.json` — Part A
- `reports/ui_report.html` — Part C
- `reports/screenshots/*.png` — Part C, failure only

All are gitignored (generated at runtime) except the `reports/` and
`reports/screenshots/` directory structure itself. Both HTML reports show
real captured output for every test, not just failures — see
`AI_USAGE.md` if curious why that wasn't the case in an earlier version.

## 18. Screenshots (Part C)

Captured automatically via a `pytest_runtest_makereport` hook in
`tests/ui/conftest.py` on any test failure — full-page, saved to
`reports/screenshots/{test_name}.png`. Since tests are parametrized across
two browsers, `{test_name}` includes the browser (e.g.
`test_foo[chromium]`), so failures in both browsers don't overwrite each
other.

## 19. AWS Architecture — Design Decisions

See [§4](#4-architecture) for the diagram. Key decisions, in the order an interviewer is
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
  running, which is itself a problem worth paging on — observed live, see
  [§14](#14-part-d--live-aws-validation)), `notBreaching` for `LatencyAlarm` (a single missing datapoint
  against `EvaluationPeriods: 1` shouldn't page on a gap rather than a
  real spike).
- **The Lambda handler needs an explicit `User-Agent` header.** DummyJSON's
  edge (Cloudflare) returns `403 Forbidden` for requests with no
  `User-Agent` — which is exactly what Python's `urllib` sends by default.
  Confirmed locally and in the live deployment: an identical request
  succeeds with the header set and fails without it. Without this fix, the
  deployed canary would report `Availability: 0` on every invocation — not
  because the API is down, but because of client fingerprinting. This
  would be a constant false page to whoever is subscribed to
  `CanaryAlertTopic`.

## 20. AWS Setup — Deploy Into Your Own Account

This stack has already been deployed and fully verified once ([§14](#14-part-d--live-aws-validation)) and
then torn down to avoid unnecessary cost. The steps below let **any**
developer — you, or an interviewer with their own AWS account — repeat
that exact cycle.

Nothing in this repository is tied to a specific AWS account, region, or
identity. `src/canary/handler.py` calls `boto3.client("cloudwatch")` with
no explicit region, profile, or credentials — it relies entirely on
boto3's standard credential/region resolution (environment variables →
shared config/credentials files → IAM role, in the usual order).
`infra/canary-stack.yaml` never hard-codes an account ID or ARN; every
cross-resource reference uses `!Ref`, `!GetAtt`, or `!Sub` with
CloudFormation pseudo parameters (`${AWS::AccountId}`, `${AWS::Region}`,
`${AWS::StackName}`), and the Lambda's own IAM role is created *by* the
stack — nothing pre-existing is assumed.

### 1. Install the AWS CLI

```bash
# macOS
brew install awscli
# Linux
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip" && unzip awscliv2.zip && sudo ./aws/install
# Windows (PowerShell)
msiexec.exe /i https://awscli.amazonaws.com/AWSCLIV2.msi
```

Commands below are written to work with **both AWS CLI v1 and v2** where
they differ (noted inline) — this environment used v1.

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
referenced from S3 rather than inlined. **Zip from the project root**,
not from inside `src/` — the template's `Handler: src/canary/handler.handler`
requires `src/canary/handler.py` at that exact path inside the archive
(a real packaging bug hit during this project's own validation — see [§14](#14-part-d--live-aws-validation)):

```bash
zip -r canary.zip src/canary/
aws s3 mb s3://your-own-build-bucket --region us-east-1   # skip if it already exists
aws s3 cp canary.zip s3://your-own-build-bucket/canary.zip

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

If the subscription shows `SubscriptionArn: "Deleted"` instead of a real
ARN or `"PendingConfirmation"`, the link was likely auto-visited by a
mail-security scanner before it could be manually confirmed (observed
once during this project's own validation, with Gmail). Fix: request a
fresh subscription and confirm it immediately —

```bash
aws sns subscribe --topic-arn <CanaryAlertTopicArn-from-stack-outputs> \
  --protocol email --notification-endpoint your-own-email@example.com
```

### 7. Verify the deployed resources

```bash
# Lambda exists and is configured as expected
aws lambda get-function --function-name qa-canary-canary

# Invoke it once manually (the EventBridge schedule is DISABLED by design)
# v1: aws lambda invoke --function-name qa-canary-canary --payload '{}' /tmp/canary-response.json
# v2: add --cli-binary-format raw-in-base64-out
aws lambda invoke --function-name qa-canary-canary --payload '{}' /tmp/canary-response.json
cat /tmp/canary-response.json

# CloudWatch Logs — the structured JSON lines the handler printed
# (v1 has no `aws logs tail`; filter-log-events works on both v1 and v2)
START_MS=$(($(date +%s) * 1000 - 600000))
aws logs filter-log-events --log-group-name /aws/lambda/qa-canary-canary \
  --start-time "$START_MS" --query 'events[].message' --output text

# CloudWatch metrics actually published
aws cloudwatch get-metric-statistics \
  --namespace QA/DummyJSON --metric-name Availability \
  --start-time "$(date -u -v-1H +%Y-%m-%dT%H:%M:%S 2>/dev/null || date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S)" \
  --end-time "$(date -u +%Y-%m-%dT%H:%M:%S)" \
  --period 300 --statistics Average

# Alarm state
aws cloudwatch describe-alarms --alarm-names qa-canary-AvailabilityAlarm qa-canary-LatencyAlarm
```

Or run `./demo_aws_live.sh` (§ below) for a narrated version of this exact
verification sequence, with pauses for live commentary.

### 8. Clean up

CloudFormation should be the only thing that removes what it created —
don't manually delete individual resources:

```bash
aws cloudformation delete-stack --stack-name qa-canary
aws cloudformation wait stack-delete-complete --stack-name qa-canary   # optional, blocks until fully gone
aws s3 rm s3://your-own-build-bucket/canary.zip   # not stack-owned, clean up separately
aws s3 rb s3://your-own-build-bucket
```

Confirm nothing was left behind (the stack owns everything it created —
Lambda, both IAM roles, the log group, both alarms, the SNS topic and
subscription — so a successful `delete-stack` should leave no residual
billable resources; verify with `aws cloudformation describe-stacks
--stack-name qa-canary`, which should return a `ValidationError: does not
exist` once fully gone).

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

## 21. Known Limitations

- **The stack is not currently deployed.** It was deployed once, fully
  verified end-to-end ([§14](#14-part-d--live-aws-validation)), and torn down afterward to avoid unnecessary
  AWS cost — that's a deliberate operational choice, not a gap. Redeploy
  with [§20](#20-aws-setup--deploy-into-your-own-account) to see it live again.
- **The Logs Insights queries** (`infra/logs-insights-queries.md`) were
  written against the exact JSON keys the handler emits, and the
  underlying log format was directly confirmed live ([§14](#14-part-d--live-aws-validation)) — but the saved
  queries themselves were not run through the CloudWatch Logs Insights
  console UI specifically, since that benefits from a longer accumulation
  of log data than a short verification cycle produces.
- **Bruno CLI v4 requires a working-directory quirk** — see [§10](#10-running-part-a--bruno). Documented
  rather than silently worked around without disclosure.
- **This dev machine's Python install initially failed SSL verification**
  against `dummyjson.com` (missing local CA bundle, a known Python.org-on-macOS
  issue unrelated to the handler code) — worked around locally with
  `certifi` purely for testing; not a change to the shipped handler.

## 22. DummyJSON Mocked Write-Operation Behavior

`POST /products/add` (used in both Part A's `products/add.bru` and
implicitly relevant to Part D's write-path reasoning) is **mocked** by
DummyJSON: it returns a plausible response — the submitted fields echoed
back plus a generated `id` — but nothing persists server-side. A follow-up
`GET /products/{new id}` would 404. Both the Bruno test and this README
treat this as a response-contract check only; no test in this repository
asserts persistence across requests for a write endpoint.

## 23. AI Usage

See [`AI_USAGE.md`](AI_USAGE.md) and [`docs/ai-sessions/`](docs/ai-sessions/)
for the full accounting of AI-assisted work on this submission, including
concrete decisions accepted/rejected and genuine AI-produced defects
(the missing `User-Agent` header, and the zip-packaging path mismatch
discussed in [§14](#14-part-d--live-aws-validation)) that were each caught by actually running the code
against real systems, not by inspection alone.

## 24. CI/CD

Not yet implemented in this snapshot of the repository. Planned as the
first optional stretch goal (GitHub Actions running `run_checks.sh` on
every push) — this section will be updated once that lands.

## 25. Optional Stretch Goals

Not yet implemented. Only Locust, a Slack alert Lambda, and Schemathesis
remain unaddressed after GitHub Actions — all are explicitly optional,
discussion-starter items per the assessment, not graded.
