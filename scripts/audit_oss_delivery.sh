#!/usr/bin/env bash
# audit_oss_delivery.sh — verify CompliantFlow OSS build hygiene
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

# ---------------------------------------------------------------------------
echo "=== 1. SOURCE-TREE DENYLIST ==="

die_if_missing find rg

BANNED_FILES=(
  "compliantflow/policy.py"
  "compliantflow/report_generator.py"
  "compliantflow/submission.py"
  "compliantflow/domain/compliance.py"
)
for f in "${BANNED_FILES[@]}"; do
  if [ -f "$f" ]; then
    fail "banned file present in source: $f"
  else
    pass "banned file absent: $f"
  fi
done

BANNED_DIRS=("compliantflow/data/")
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
)
for s in "${BANNED_STRINGS[@]}"; do
  if rg -q --include='*.py' --include='*.yml' --include='*.yaml' "$s" compliantflow/ 2>/dev/null; then
    fail "banned string in source: '$s'"
  else
    pass "banned string absent from source: '$s'"
  fi
done

# ---------------------------------------------------------------------------
echo "=== 2. WHEEL-CONTENT AUDIT ==="

die_if_missing python3

WHEEL_DIR="${WHEEL_DIR:-dist}"
rm -rf "$WHEEL_DIR"
python3 -m build --wheel 2>/dev/null || { fail "wheel build failed"; }
WHEEL=$(ls "$WHEEL_DIR"/*.whl 2>/dev/null | head -1)

if [ -z "$WHEEL" ]; then
  fail "no wheel produced"
else
  pass "wheel built: $WHEEL"

  python3 -c "
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
    'governance' in n
]
if banned:
    print('FAIL: banned files in wheel:')
    for b in banned: print(f'  {b}')
    sys.exit(1)
else:
    print('OK')
" && pass "wheel content clean" || fail "wheel contains banned files"
fi

# ---------------------------------------------------------------------------
echo "=== 3. DEPENDENCY-CONTRACT AUDIT ==="

if ! grep -q '"dhf_util"' pyproject.toml; then
  fail "dhf_util not in dependencies"
else
  pass "dhf_util present in dependencies"
fi

# Generated workflow: dhf install before compliantflow
INSTALL_ORDER_OK=true
if rg -q 'pip install -e dhf/' compliantflow/init_cmd.py 2>/dev/null; then
  pass "init installs dhf before CompliantFlow (pip install -e dhf/ found)"
else
  fail "init missing pip install -e dhf/ step"
fi

# Docs must mention dhf_util prerequisite for wheel install
if rg -q 'dhf_util' GETTING_STARTED.md 2>/dev/null; then
  pass "GETTING_STARTED mentions dhf_util"
else
  fail "GETTING_STARTED missing dhf_util prerequisite"
fi

# ---------------------------------------------------------------------------
echo "=== 4. SCAFFOLD-CONTRACT AUDIT ==="

# init must fetch from remote, not read local data/
if rg -q "_fetch_dhf_template" compliantflow/init_cmd.py 2>/dev/null; then
  pass "init fetches DHF template from remote"
else
  fail "init missing remote DHF fetch logic"
fi

if rg -q 'TEMPLATE_DIR\|data\s*/\s*"dhf-template"' compliantflow/init_cmd.py 2>/dev/null; then
  fail "init still references local data/ template"
else
  pass "init has no local template references"
fi

# Fetch copies installable DHF content
for name in DHF .github dhf_util pyproject.toml README.md; do
  if rg -q "\"$name\"" compliantflow/init_cmd.py 2>/dev/null; then
    pass "init copies $name from fetched repo"
  else
    fail "init missing $name in fetch copy list"
  fi
done

# Generated workflows: no compliance-check
for f in compliantflow/init_cmd.py; do
  if rg -q 'ci compliance-check' "$f" 2>/dev/null; then
    fail "generated workflow references ci compliance-check"
    INSTALL_ORDER_OK=false
  fi
done
if $INSTALL_ORDER_OK; then
  pass "generated workflows: no compliance-check references"
fi

# CLAUDE.md template points to existing docs
if rg -q 'README.md' compliantflow/init_cmd.py 2>/dev/null; then
  pass "CLAUDE.md template references README.md"
fi

# ---------------------------------------------------------------------------
echo "=== 5. DOCS AND WORKFLOW AUDIT ==="

DOC_BANNED=(
  "ci compliance-check"
  "validate compliance"
  "report compliance"
  "wheel + DHF"
  "compliance reports"
)
DOC_TARGETS=("README.md" "GETTING_STARTED.md" "ARCHITECTURE.md" "PROJECT_STATUS.md")

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

# Install contract: wheel docs must require dhf_util
if rg -A8 "Released package install" GETTING_STARTED.md 2>/dev/null | rg -q "compliantflow-dhf"; then
  pass "wheel install doc includes dhf_util prerequisite"
else
  fail "wheel install doc missing dhf_util prerequisite"
fi

# WebTPS must not be primary framing
if head -30 README.md | rg -q "WebTPS" 2>/dev/null; then
  fail "README top-level mentions WebTPS"
else
  pass "WebTPS not in README top-level framing"
fi

# Install docs must not present standalone wheel install without dhf_util
if rg -A2 "Released package install" GETTING_STARTED.md | rg -q "git clone.*compliantflow-dhf"; then
  pass "wheel install doc includes dhf_util prerequisite"
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
  "consume-release-artifact\|consume_artifact"
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
