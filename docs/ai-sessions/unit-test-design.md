# AI Session Notes — Unit Test Design (Part B)

Tool: Claude (Sonnet 5) via Claude Code. Task: design and implement
`tests/unit/test_api_checker.py` against `src/api_checker.py`, which the
assessment explicitly prohibits modifying.

## Approach

Rather than working only from the assessment's "Required Coverage"
bullet list, the actual source of `src/api_checker.py` was read line by
line first — the docstrings describe intended behavior, but the source is
what actually executes, and the two aren't guaranteed to be identical
(they weren't, in one case — see below).

## Key reasoning during design

**The bool/int trap.** The assessment calls out `id is True (Python bool)
→ treated as invalid — read the docstring to understand why`. Reading the
source directly (not just the docstring) shows exactly why:
`isinstance(product["id"], int)` is `True` for `True`/`False` in Python,
because `bool` is a subclass of `int`. Without the explicit
`isinstance(product["id"], bool)` guard the source includes, a product
with `"id": True` would silently pass the positive-integer check (since
`True == 1`). This pattern repeats for `stock` and (in
`calculate_cart_total`) `quantity` — all three got a dedicated
bool-rejection test, not just the one the assessment explicitly named for
`id`.

**Whether the NaN branch is reachable.** `validate_product`'s price check
is an `elif` chain: not-a-number → `price <= 0` → `price > MAX` → `price
!= price` (the NaN check). Initial read: since NaN fails ordinary
comparisons, it looked plausible that `price <= 0` might catch it first
by some quirk and make the last branch dead code. Actually verifying this
(both by reasoning through Python's NaN comparison semantics — `nan <= 0`
is `False`, not an error and not `True` — and then by writing
`test_price_nan_is_invalid` and running it) confirmed the branch is very
much reachable and correctly triggers "price must be a finite number".
Documented as an explicit test rather than left as an assumption.

**Which exception type, precisely.** The assessment's coverage table
distinguishes `TypeError` vs `KeyError` vs `ValueError` per function. Each
test asserts the *specific* exception type via `pytest.raises(ExactType)`,
not a broad `Exception`, and several also assert on the exception message
content (`match=`) where the source's error messages are meant to be
diagnostic — e.g. `"index 1"` for a cart product missing its price field,
`"got 2"` for a two-segment JWT.

**Extra edge cases beyond the assessment's list.** The module's own
docstring instructs: "at least one boundary/edge case per function that is
NOT explicitly described in the docstrings." Added: `quantity` and `stock`
as booleans (documented pattern above), and a test confirming
`parse_auth_response` ignores unrelated fields in a realistic DummyJSON
auth response (`refreshToken`, `id`, `username`) rather than only testing
against a minimal `{"accessToken": ...}` dict.

## Verification

Ran `python3 -m pytest tests/unit/ -v --tb=short` after first draft — all
46 tests passed on the first run, no fix cycle was needed. Re-verified
with the HTML reporter (`--html=reports/unit_report.html`) as part of the
final `run_checks.sh` run.
