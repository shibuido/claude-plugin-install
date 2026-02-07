#!/usr/bin/env bash
set -euo pipefail

# Test: 01-help
# Description: Verify --help flag outputs usage info and exits 0

source /workspace/testing/lib/assertions.sh

SCRIPT="claude-plugin-install"

echo "Test: 01-help -- Verify --help output"

# Run --help and capture output
OUTPUT=$($SCRIPT --help 2>&1) || true
EXIT_CODE=0
$SCRIPT --help >/dev/null 2>&1 || EXIT_CODE=$?

assert_exit_code "exit code is 0" 0 "$EXIT_CODE"
assert_contains "output contains PLUGIN@MARKETPLACE" "$OUTPUT" "PLUGIN@MARKETPLACE"
assert_contains "output contains usage info" "$OUTPUT" "install"

print_summary
