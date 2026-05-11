#!/usr/bin/env bash
# audit_oss_delivery.sh — verify MedHarness OSS build hygiene
# Exit non-zero on any violation.  Run from repo root.
set -euo pipefail

FAIL=0
TOTAL=0

pass()  { TOTAL=$((TOTAL+1)); echo "  PASS: $1"; }
fail()  { TOTAL=$((TOTAL+1)); FAIL=$((FAIL+1)); echo "  FAIL: $1"; }

die_if_missing() {
  for cmd in "$@"; do
    command -v "$cmd" >/dev/null || { echo "ERROR: required tool not found — $cmd"; exit 2; }
  done
}

PYTHON_BIN="${PYTHON_BIN:-}"
if [ -z "$PYTHON_BIN" ]; then
  if [ -x ".venv/bin/python" ]; then
    PYTHON_BIN=".venv/bin/python"
  else
    PYTHON_BIN="$(command -v python)"
  fi
fi

# ---------------------------------------------------------------------------
echo "=== 1. SOURCE-TREE DENYLIST ==="

die_if_missing find rg

BANNED_FILES=(
  "medharness/policy.py"
  "medharness/report_generator.py"
  "medharness/submission.py"
  "medharness/domain/compliance.py"
)
for f in "${BANNED_FILES[@]}"; do
  if [ -f "$f" ]; then
    fail "banned file present in source: $f"
  else
    pass "banned file absent: $f"
  fi
done

BANNED_DIRS=("medharness/data/")
for d in "${BANNED_DIRS[@]}"; do
  if [ -d "$d" ] && [ "$(ls -A "$d" 2>/dev/null)" ]; then
    fail "banned directory present: $d"
  else
    pass "banned directory absent or empty: $d"
  fi
done

BANNED_STRINGS=(
  "ci compliance-check"
  "validate compliance"
  "report compliance"
  "dhf-release-artifacts"
  "DHF-*.zip"
  "data/dhf-template"
  "DHF_TEMPLATE_REPO"
  "MedHarness-DHF"
  "medharness.medharness-dhf"
)
for s in "${BANNED_STRINGS[@]}"; do
  if rg -q --include='*.py' --include='*.yml' --include='*.yaml' "$s" medharness/ 2>/dev/null; then
    fail "banned string in source: '$s'"
  else
    pass "banned string absent from source: '$s'"
  fi
done

# ---------------------------------------------------------------------------
echo "=== 2. WHEEL-CONTENT AUDIT ==="

die_if_missing "$PYTHON_BIN"

WHEEL_DIR="${WHEEL_DIR:-dist}"
rm -rf "$WHEEL_DIR" build
if "$PYTHON_BIN" -m build --version >/dev/null 2>&1; then
  "$PYTHON_BIN" -m build --wheel 2>/dev/null || { fail "wheel build failed"; }
else
  "$PYTHON_BIN" -m pip wheel . -w "$WHEEL_DIR" --no-deps --no-build-isolation >/dev/null 2>&1 || {
    fail "wheel build failed"
  }
fi
WHEEL=$(ls "$WHEEL_DIR"/*.whl 2>/dev/null | head -1)

if [ -z "$WHEEL" ]; then
  fail "no wheel produced"
else
  pass "wheel built: $WHEEL"

  "$PYTHON_BIN" -c "
import zipfile, sys
with zipfile.ZipFile('$WHEEL') as z:
    names = z.namelist()
banned = [n for n in names if
    'policy.py' in n or
    'report_generator.py' in n or
    'submission.py' in n or
    'domain/compliance.py' in n or
    '/data/' in n or
    'dhf-template' in n or
    'governance' in n or
    'templates/github/workflows/' in n
]
if banned:
    print('FAIL: banned files in wheel:')
    for b in banned: print(f'  {b}')
    sys.exit(1)
else:
    print('OK')
" && pass "wheel content clean" || fail "wheel contains banned files"
fi

# Both packages must be present in wheel
"$PYTHON_BIN" -c "
import zipfile, sys
with zipfile.ZipFile('$WHEEL') as z:
    names = z.namelist()
has_cf = any('medharness/' in n for n in names)
has_dhf = any('dhfkit/' in n for n in names)
has_templates = any('templates/' in n for n in names)
if has_cf and has_dhf:
    print('OK: both medharness and dhfkit in wheel')
else:
    if not has_cf: print('FAIL: medharness missing from wheel')
    if not has_dhf: print('FAIL: dhfkit missing from wheel')
    sys.exit(1)
if not has_templates:
    print('WARN: templates/ missing from wheel (init may fail on installed package)')
" && pass "wheel contains both packages" || fail "wheel missing packages"

# Workflow templates are no longer part of the release payload.
"$PYTHON_BIN" -c "
import zipfile, sys
with zipfile.ZipFile('$WHEEL') as z:
    names = z.namelist()
workflow_templates = [n for n in names if 'templates/github/workflows/' in n]
if workflow_templates:
    print('FAIL: workflow templates present in wheel:')
    for name in workflow_templates:
        print(f'  {name}')
    sys.exit(1)
print('OK: no workflow templates bundled in wheel')
" && pass "wheel excludes workflow templates" || fail "wheel still bundles workflow templates"

# ---------------------------------------------------------------------------
echo "=== 3. DEPENDENCY-CONTRACT AUDIT ==="

# dhfkit is now part of the same package — not an external dependency
if grep -A20 '^dependencies = \[' pyproject.toml 2>/dev/null | grep -q '"dhfkit"'; then
  fail "dhfkit should not be an external dependency — it's bundled"
else
  pass "dhfkit not listed as external dependency (bundled in same package)"
fi

# Init no longer does git clone or pip install -e dhf/
if rg -q "pip install -e dhf/" medharness/workflows/init.py 2>/dev/null; then
  fail "init still references pip install -e dhf/ (no longer needed)"
else
  pass "init does not reference separate dhfkit install"
fi

# Only medharness CLI entrypoint must be registered; dhf-util is retired
if grep -q 'medharness = "medharness.cli:main"' pyproject.toml 2>/dev/null; then
  pass "medharness CLI entrypoint registered"
else
  fail "missing medharness CLI entrypoint"
fi
if grep -q 'dhf-util = "dhfkit.cli:main"' pyproject.toml 2>/dev/null; then
  fail "dhf-util CLI entrypoint should NOT be registered (retired)"
else
  pass "dhf-util CLI entrypoint not registered (retired)"
fi

# Getting started is now part of README.md
if rg -q 'pip install' README.md 2>/dev/null; then
  pass "README includes pip install instructions"
else
  fail "README missing pip install instructions"
fi

# ---------------------------------------------------------------------------
echo "=== 4. SCAFFOLD-CONTRACT AUDIT ==="

# init must scaffold from local bundled templates, not remote fetch
if rg -q "_scaffold_dhf|scaffolds from" medharness/workflows/init.py 2>/dev/null; then
  pass "init scaffolds DHF from local templates"
else
  fail "init missing local scaffold logic"
fi

# init must NOT reference git clone or remote fetch
if rg -q "git clone|DHF_TEMPLATE_REPO|_fetch_dhf_template" medharness/workflows/init.py 2>/dev/null; then
  fail "init still references remote DHF fetch"
else
  pass "init has no remote DHF fetch logic"
fi

# Generated workflows: no compliance-check
if rg -q 'ci compliance-check' medharness/workflows/init.py 2>/dev/null; then
  fail "generated workflow references ci compliance-check"
else
  pass "generated workflows: no compliance-check references"
fi

# CLAUDE.md template points to existing docs
if rg -q 'README.md' medharness/workflows/init.py 2>/dev/null; then
  pass "CLAUDE.md template references README.md"
fi

# ---------------------------------------------------------------------------
echo "=== 5. DOCS AND WORKFLOW AUDIT ==="

DOC_TARGETS=("README.md")

# Boundary docs that mention removed commands as "not part of OSS" or
# "commercial" are allowed.  Only fail if presented as stable/OSS commands.
for doc in "${DOC_TARGETS[@]}"; do
  for s in "ci compliance-check" "validate compliance" "report compliance"; do
    matches=$(rg -n "$s" "$doc" 2>/dev/null || true)
    if [ -n "$matches" ]; then
      boundary=$(echo "$matches" | rg -c "Commercial|commercial|not part|available internally|future tier" || true)
      total=$(echo "$matches" | wc -l | tr -d ' ')
      if [ "${boundary:-0}" -lt "${total:-1}" ]; then
        fail "$doc: presents '$s' as OSS command"
      fi
    fi
  done
done

# No references to separate medharness-dhf clone
if rg -q "medharness-dhf|MedHarness-DHF" README.md 2>/dev/null; then
  fail "README references separate MedHarness-DHF repo"
else
  pass "README does not reference separate MedHarness-DHF repo"
fi

# WebTPS must not be primary framing
if head -30 README.md | rg -q "WebTPS" 2>/dev/null; then
  fail "README top-level mentions WebTPS"
else
  pass "WebTPS not in README top-level framing"
fi

# ---------------------------------------------------------------------------
echo "=== 6. RELEASE-WORKFLOW AUDIT ==="

RELEASE_YML=".github/workflows/release.yml"
RELEASE_BANNED=(
  "dhf-release-artifacts"
  "DHF-*.zip"
  "compliance report"
  "evidence-bundle"
  "assemble"
  "consume-release-artifact|consume_artifact"
)

for s in "${RELEASE_BANNED[@]}"; do
  if rg -q "$s" "$RELEASE_YML" 2>/dev/null; then
    fail "release.yml contains banned pattern: '$s'"
  fi
done

# Release must build + publish wheel only
if rg -q "build --wheel" "$RELEASE_YML" 2>/dev/null && \
   rg -q "action-gh-release" "$RELEASE_YML" 2>/dev/null; then
  pass "release.yml builds wheel and publishes via gh-release"
else
  fail "release.yml missing build + publish steps"
fi

# ---------------------------------------------------------------------------
echo "=== 7. CI-PIPELINE AUDIT ==="

CI_YML=".github/workflows/ci-pipeline.yml"
if [ -f "$CI_YML" ]; then
  if rg -q "ci compliance-check" "$CI_YML" 2>/dev/null; then
    fail "ci-pipeline.yml references ci compliance-check"
  else
    pass "ci-pipeline.yml free of compliance-check"
  fi

  # No separate DHF repo checkout — uses bundled dhfkit + example project
  if rg -q "medharness-dhf|MedHarness-DHF" "$CI_YML" 2>/dev/null; then
    fail "ci-pipeline.yml references separate MedHarness-DHF repo"
  else
    pass "ci-pipeline.yml uses bundled dhfkit (no separate clone)"
  fi

  # Has dhfkit test job
  if rg -q "tests-dhf-util|dhfkit/tests" "$CI_YML" 2>/dev/null; then
    pass "ci-pipeline.yml includes dhfkit tests"
  else
    fail "ci-pipeline.yml missing dhfkit test job"
  fi
else
  fail "ci-pipeline.yml not found"
fi

# ---------------------------------------------------------------------------
echo ""
echo "=============================="
if [ "$FAIL" -eq 0 ]; then
  echo "RESULT: ALL $TOTAL CHECKS PASSED"
  exit 0
else
  echo "RESULT: $FAIL/$TOTAL CHECKS FAILED"
  exit 1
fi
