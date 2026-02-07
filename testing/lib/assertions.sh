#!/usr/bin/env bash
# assertions.sh -- Shared test assertion functions for E2E tests
#
# Source this file from each test.sh:
#   source /workspace/testing/lib/assertions.sh
#
# Provides: assert_eq, assert_contains, assert_not_contains,
#           assert_file_exists, assert_file_not_exists, assert_json_has_key,
#           assert_json_not_has_key, assert_exit_code, assert_exit_code_not,
#           print_summary
#
# All assertion functions are safe under `set -euo pipefail`:
#   - ((PASS++)) and ((FAIL++)) use `|| true` to avoid false exits
#   - grep pipes use `|| true` to prevent pipefail from killing the script

PASS=0
FAIL=0

assert_eq() {
    local label="$1" expected="$2" actual="$3"
    if [[ "$expected" == "$actual" ]]; then
        echo "  PASS: $label"
        ((PASS++)) || true
    else
        echo "  FAIL: $label (expected='$expected', actual='$actual')"
        ((FAIL++)) || true
    fi
}

assert_contains() {
    local label="$1" haystack="$2" needle="$3"
    local found=0
    echo "$haystack" | grep -qi "$needle" && found=1 || true
    if [[ $found -eq 1 ]]; then
        echo "  PASS: $label"
        ((PASS++)) || true
    else
        echo "  FAIL: $label (output does not contain '$needle')"
        echo "  --- actual output (first 20 lines) ---"
        echo "$haystack" | head -20
        echo "  --- end ---"
        ((FAIL++)) || true
    fi
}

assert_not_contains() {
    local label="$1" haystack="$2" needle="$3"
    local found=0
    echo "$haystack" | grep -qi "$needle" && found=1 || true
    if [[ $found -eq 0 ]]; then
        echo "  PASS: $label"
        ((PASS++)) || true
    else
        echo "  FAIL: $label (output unexpectedly contains '$needle')"
        ((FAIL++)) || true
    fi
}

assert_file_exists() {
    local label="$1" filepath="$2"
    if [[ -f "$filepath" ]]; then
        echo "  PASS: $label"
        ((PASS++)) || true
    else
        echo "  FAIL: $label (file not found: $filepath)"
        ((FAIL++)) || true
    fi
}

assert_file_not_exists() {
    local label="$1" filepath="$2"
    if [[ ! -f "$filepath" ]]; then
        echo "  PASS: $label"
        ((PASS++)) || true
    else
        echo "  FAIL: $label (file should not exist: $filepath)"
        ((FAIL++)) || true
    fi
}

assert_json_has_key() {
    local label="$1" filepath="$2" key="$3"
    local rc=0
    python3 -c "
import json, sys
with open('$filepath') as f:
    d = json.load(f)
sys.exit(0 if '$key' in str(d) else 1)
" 2>/dev/null || rc=$?
    if [[ $rc -eq 0 ]]; then
        echo "  PASS: $label"
        ((PASS++)) || true
    else
        echo "  FAIL: $label (key '$key' not in $filepath)"
        ((FAIL++)) || true
    fi
}

assert_json_not_has_key() {
    local label="$1" filepath="$2" key="$3"
    local rc=0
    python3 -c "
import json, sys
with open('$filepath') as f:
    d = json.load(f)
sys.exit(0 if '$key' not in str(d) else 1)
" 2>/dev/null || rc=$?
    if [[ $rc -eq 0 ]]; then
        echo "  PASS: $label"
        ((PASS++)) || true
    else
        echo "  FAIL: $label (key '$key' unexpectedly found in $filepath)"
        ((FAIL++)) || true
    fi
}

assert_exit_code() {
    local label="$1" expected="$2" actual="$3"
    if [[ "$expected" -eq "$actual" ]]; then
        echo "  PASS: $label"
        ((PASS++)) || true
    else
        echo "  FAIL: $label (expected exit code $expected, got $actual)"
        ((FAIL++)) || true
    fi
}

assert_exit_code_not() {
    local label="$1" not_expected="$2" actual="$3"
    if [[ "$not_expected" -ne "$actual" ]]; then
        echo "  PASS: $label"
        ((PASS++)) || true
    else
        echo "  FAIL: $label (exit code should not be $not_expected)"
        ((FAIL++)) || true
    fi
}

# Print test summary and exit with appropriate code
print_summary() {
    echo ""
    echo "Results: $PASS passed, $FAIL failed"
    [[ $FAIL -eq 0 ]] && exit 0 || exit 1
}
