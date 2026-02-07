#!/usr/bin/env bash
set -euo pipefail

# Test: 02-invalid-format
# Description: Verify that a plugin argument without @ is rejected

source /workspace/testing/lib/assertions.sh

SCRIPT="claude-plugin-install"
export XDG_CACHE_HOME=/tmp/test-cache

echo "Test: 02-invalid-format -- Reject plugin without @marketplace"

# Run with invalid format (no @)
OUTPUT=$($SCRIPT -p superpowers -y 2>&1) || true
EXIT_CODE=0
$SCRIPT -p superpowers -y >/dev/null 2>&1 || EXIT_CODE=$?

assert_exit_code_not "exit code is non-zero" 0 "$EXIT_CODE"
assert_contains "error mentions plugin@marketplace format" "$OUTPUT" "plugin@marketplace"

print_summary
