#!/bin/bash
# =============================================================================
# run_checks.sh — Runs all four core assessment parts in sequence.
#
# Requirements:
#   - Do not remove set -euo pipefail
#   - Each section must print its banner
#   - The script must exit non-zero if any part fails
#   - Make executable before running: chmod +x run_checks.sh
# =============================================================================

set -euo pipefail

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

section() {
  echo ""
  echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
  echo -e "${YELLOW}  $1${NC}"
  echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
  echo ""
}

# Load .env if present
if [ -f .env ]; then
  set -o allexport
  # shellcheck disable=SC1091
  source .env
  set +o allexport
else
  echo "WARNING: .env not found. Copy .env.example to .env and fill in the values."
fi

mkdir -p reports/screenshots

# =============================================================================
section "Part B — pytest Unit Tests"

python3 -m pytest tests/unit/ -v --tb=short --html=reports/unit_report.html --self-contained-html

# =============================================================================
section "Part A — Bruno API Contract Tests"

# bru (v4 CLI) must be invoked with its cwd at the collection root (where
# bruno.json lives) — `bru run collections/dummyjson/` from the project
# root errors with "You can run only at the root of a collection". Running
# in a subshell keeps this cd from leaking into the rest of the script, and
# -r recurses into the auth/ and products/ subfolders.
(
  cd collections/dummyjson
  bru run . -r --env local --output ../../reports/bruno_report.json
)

# =============================================================================
section "Part C — Playwright UI Tests"

python3 -m pytest tests/ui/ -v --browser chromium --browser firefox --html=reports/ui_report.html --self-contained-html

# =============================================================================
section "Part D — CloudFormation Validation (cfn-lint)"

# cfn-lint's own exit code is a bitmask (0=clean, 2=error, 4=warning, ...)
# that conflates "warnings only" with "failed". Instead of trusting the
# raw exit code, capture the JSON findings and branch on their actual
# Level so ERROR fails the build and WARNING only prints and continues,
# per this section's requirement.
set +e
CFN_LINT_JSON=$(cfn-lint infra/canary-stack.yaml --format json)
set -e

python3 - "$CFN_LINT_JSON" <<'PYEOF'
import json
import sys

raw = sys.argv[1].strip()
findings = json.loads(raw) if raw else []

errors = [f for f in findings if f.get("Level") == "Error"]
warnings = [f for f in findings if f.get("Level") == "Warning"]

for w in warnings:
    print(f"  WARN  {w['Rule']['Id']}: {w['Message']}")
for e in errors:
    print(f"  ERROR {e['Rule']['Id']}: {e['Message']}")

if errors:
    print(f"\ncfn-lint found {len(errors)} error(s).")
    sys.exit(1)
elif warnings:
    print(f"\ncfn-lint found {len(warnings)} warning(s) — continuing.")
else:
    print("cfn-lint: clean, no findings.")
PYEOF

# =============================================================================
echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}  All checks passed.${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
