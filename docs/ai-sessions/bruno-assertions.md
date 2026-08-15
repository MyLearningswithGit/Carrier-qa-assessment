# AI Session Notes — Bruno Collection & Assertion Strategy (Part A)

Tool: Claude (Sonnet 5) via Claude Code. Task: add the 8 required `.bru`
request files with meaningful `tests {}` assertions (not status-code-only
checks), per the assessment's table.

## Principle: probe the real API before writing assertions

Rather than writing assertions from assumptions about DummyJSON's shape,
every endpoint was queried directly with `curl`/Python first, and the
actual response was read before deciding what to assert. This surfaced
two things that would have produced either a wrong assertion or a
misleadingly shallow one:

### 1. The `/products/search?q=phone` case is a substring trick, not a title match

Fetching `GET /products/search?q=phone` and printing every result's title
showed most matches — Samsung Galaxy S10, Oppo A57, Realme X, etc. — have
no "phone" substring in the *title* at all. Checking the full description
text revealed the actual mechanism: DummyJSON's search does a
case-insensitive substring match, and nearly every result's *description*
contains the word "smartphone" — which contains "phone" as a substring
(`"smartphone".find("phone") == 5`). A handful (iPhone-named products) do
match via the title.

Verified computationally, not just by inspection: wrote a one-off script
that lower-cased every result's `title + " " + description` and confirmed
all 23 results contain "phone" that way. The Bruno assertion checks
`title + " " + description`, and the `.bru` file's `docs {}` block
explains *why* — a reviewer reading only the assertion would otherwise
reasonably wonder why it's not checking title alone.

### 2. Pagination "total consistency" needed a real cross-request check

The assessment requires `list-paginated.bru` (`?limit=5&skip=10`) to
assert "total is consistent with an unskipped call" — which means two
separate requests need to agree with each other, not just each be
internally sane. Implemented by having `list-all.bru` (seq: 1) save
`res.body.total` into an environment variable
(`bru.setEnvVar("unskippedTotal", ...)`) in its `script:post-response`
block, and `list-paginated.bru` (seq: 2) read it back via
`bru.getEnvVar()` and assert equality. This depends on Bruno's
within-folder `seq` ordering, which was confirmed empirically (not
assumed) when the full collection was run — `list-all` executes before
`list-paginated` and the value is available.

## A real tooling discrepancy, not a code bug

The assessment's documented run command
(`bru run collections/dummyjson/ --env local --output reports/bruno_report.json`
from the project root) fails immediately with `You can run only at the
root of a collection` under the installed Bruno CLI (v4.0.0) — confirmed
by running the exact documented command verbatim before concluding it was
actually broken, not a typo on this end. Root-caused by testing several
invocation shapes: the CLI requires its working directory to *be* the
collection root, and needs `-r` to recurse into `auth/`/`products/`. Fixed
in `run_checks.sh` (a subshell `cd`) and disclosed explicitly in
`README.md` §9 rather than silently changing the documented command
without a note.

## Verification

Full collection run (`bru run . -r --env local`) from the collection
root: 9/9 requests passed, 27/27 `tests{}` assertions passed, 3/3 raw
`assert{}` block assertions passed (from the provided `login-valid.bru`).
Re-verified as part of the final `run_checks.sh` run.
