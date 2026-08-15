# AI Usage Documentation

This document is a truthful account of how AI assistance was used to build
this submission. It describes what actually happened in this session, not
an idealized version of it.

## Section 1 — Tools Used

**Claude (Sonnet 5, model id `claude-sonnet-5`), via Claude Code (CLI/IDE
agent)** — the only AI tool used for this submission. Used for essentially
the entire implementation across all four core parts, working directly in
an agentic coding environment with file read/write/edit and shell-execution
tools, driven by two long, explicit, requirement-by-requirement prompts
from the candidate (the second of which directed full autonomous
implementation through to a submission-ready state).

This was not "autocomplete while I typed" usage — it was direct
AI-authored implementation of every deliverable file, verified by actually
running each part (pytest, `bru run`, Playwright against real browsers,
`cfn-lint`, and direct local invocation of the Lambda handler against the
live DummyJSON API) rather than by inspection alone. Approximate influence
per file:

| File | Influence | Notes |
|---|---|---|
| `tests/unit/test_api_checker.py` | ~95% | AI-authored from the assessment's coverage spec + reading `src/api_checker.py`'s source directly (not just docstrings) to get exact error strings and branch behavior right. |
| `collections/dummyjson/*.bru` | ~90% | AI-authored, but every assertion was written only after probing the real DummyJSON API with `curl`/Python first — see `docs/ai-sessions/bruno-assertions.md`. |
| `tests/ui/pages/*.py`, `tests/ui/test_*.py`, `conftest.py` | ~95% | AI-authored after driving the real Sauce Demo site with Playwright to extract actual `data-test` locators, error text, and the checkout flow — not from memorized assumptions about the site. |
| `src/canary/handler.py` | ~90% | AI-authored, then AI-debugged after a genuine defect was found by execution — see Section 4. |
| `infra/canary-stack.yaml` | ~95% | AI-authored against the assessment's exact resource/threshold spec; iterated once in response to a real `cfn-lint` warning. |
| `run_checks.sh`, `README.md`, `infra/logs-insights-queries.md` | ~90% | AI-authored. |

The candidate's role in this session: supplied the assessment document and
starter repository, set explicit constraints (do not modify
`src/api_checker.py`, do not fabricate results, run everything for real),
and directed the overall sequencing. Per the assessment's own instruction
("Be ready to explain every line of every file during the interview"),
reviewing and internalizing this AI-authored code before the interview is
the candidate's responsibility going forward — this document is the honest
record of how it was produced, not a claim that review has already
happened.

## Section 2 — Conversation Logs

Three session-note files in `docs/ai-sessions/`, each a distilled but
truthful record of the actual reasoning and verification steps taken
during this session (not a fabricated transcript):

- [`docs/ai-sessions/unit-test-design.md`](docs/ai-sessions/unit-test-design.md)
- [`docs/ai-sessions/cloudformation.md`](docs/ai-sessions/cloudformation.md)
- [`docs/ai-sessions/bruno-assertions.md`](docs/ai-sessions/bruno-assertions.md)

## Section 3 — Decisions Made vs. Rejected

1. **Proposed:** use the `requests` library for the Lambda's two HTTP
   calls. **Rejected** in favor of the standard library's `urllib.request`
   — `requests` isn't included in the default Lambda Python runtime image,
   so using it would require packaging a dependency layer for what is
   otherwise a two-call function. Not worth the deployment overhead for
   this canary.

2. **Proposed:** in the Playwright checkout test, assert the order summary
   price against a hardcoded literal (`"$29.99"`). **Rejected** in favor of
   capturing the price from the inventory page first and asserting the
   checkout summary matches *that* value — a hardcoded literal only proves
   the price hasn't changed since the test was written; capturing it
   dynamically actually proves cross-page consistency, which is what the
   assessment's requirement ("verify order summary shows correct product
   and price") is really asking for.

3. **Proposed:** round the Lambda's structured-log `latency_ms` to 2
   decimal places, matching the precision published to CloudWatch.
   **Rejected** in favor of rounding to a whole number in the log line
   only — the assessment's own example (`"latency_ms": 142`) shows an
   integer, and matching that exactly avoids a reviewer wondering whether
   `142.35` in a log line was intentional or a formatting slip. Full float
   precision is still published to the CloudWatch metric itself, where the
   extra precision has actual value (alarm math).

4. **Proposed:** write a formal pytest suite for `src/canary/handler.py`
   itself. **Rejected** — the assessment's unit-testing requirement (Part
   B) targets `api_checker.py` specifically, and the handler is explicitly
   a "you do not need to deploy it" deliverable. Added a formal test suite
   for a file the assessment doesn't ask to be tested that way, on top of
   everything else already required, and it would have been scope creep.
   Validated instead by direct local invocation against the real API
   (documented in `docs/ai-sessions/cloudformation.md`), which is enough
   to prove the handler's actual behavior without inventing an
   unrequested deliverable.

## Section 4 — Things AI Got Wrong

**A "do not modify" file was mutated and committed without noticing.**
`collections/dummyjson/environments/local.bru` is explicitly marked
"provided — do not modify" in the assessment. Running the Bruno collection
repeatedly during development, before the first git commit, caused the
Bruno CLI to rewrite this file on disk twice over: once from the
*provided* `login-valid.bru`'s own `bru.setEnvVar("accessToken", ...)`
call (unavoidable — confirmed by running that file in total isolation),
and once from this submission's own `list-all.bru`, which used
`bru.setEnvVar("unskippedTotal", ...)` to pass a value to
`list-paginated.bru`. That second mutation was avoidable and was the
actual mistake: the file that got committed in the Part A commit was the
mutated version, with an extra variable line, not the original. This
wasn't caught by any test — it was caught by actually reading `git diff`
during a final audit pass instead of assuming a clean `git status` meant
everything was fine. Fixed by switching to `bru.setVar()` (confirmed
empirically to be run-scoped and not persisted to disk), restoring the
file to its original content, and committing the correction separately
rather than rewriting history. See
`docs/ai-sessions/bruno-assertions.md` for the full diagnosis.

**The Lambda handler's first working version returned false negatives
against the real API.** The initial implementation used `urllib.request`
with no explicit `User-Agent` header. When actually invoked against the
live DummyJSON API (not just read/reviewed), both calls came back `403
Forbidden`. Root cause, found by comparing a `curl` request (succeeds)
against an equivalent Python `urllib` request (fails) with and without an
explicit `User-Agent`: DummyJSON's edge (Cloudflare) blocks requests with
no `User-Agent` header, which is exactly what `urllib` sends by default.
Fixed by setting an explicit `User-Agent` on both requests. This was not a
cosmetic bug — an undetected version of this would have made the deployed
canary report `Availability: 0` on every single invocation, a constant
false page to whoever is subscribed to `CanaryAlertTopic`, for a problem
that doesn't actually exist. It was only caught because the handler was
executed against the real network instead of trusted on inspection alone.

**Smaller case:** during the initial risk-assessment pass (before writing
any tests), a note was made that the `price != price` (NaN) check inside
`validate_product`'s `elif` chain might be unreachable, based on a quick
read of the branch order. That assumption was wrong — NaN comparisons
(`nan <= 0`, `nan > MAX`) are always `False` in Python, so the chain
correctly falls through to the explicit NaN check. Caught by actually
writing `test_price_nan_is_invalid` and running it rather than trusting
the initial read of the code.
