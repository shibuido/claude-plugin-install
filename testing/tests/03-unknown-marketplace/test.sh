#!/usr/bin/env bash
set -euo pipefail

# Test: 03-unknown-marketplace
# Description: Verify that a plugin with an unknown marketplace is rejected
#
# Note: The tool checks known_marketplaces.json. In our Docker environment,
# there are no known marketplaces, so the known list is empty.
# When the known list is empty, the tool skips marketplace validation.
# We need to create a known_marketplaces.json with at least one entry
# so the "not found" check triggers.

source /workspace/testing/lib/assertions.sh

SCRIPT="claude-plugin-install"
export XDG_CACHE_HOME=/tmp/test-cache

echo "Test: 03-unknown-marketplace -- Reject unknown marketplace"

# Create a known_marketplaces.json with a valid marketplace
# so the tool can detect that 'nonexistent' is not valid
mkdir -p ~/.claude/plugins
echo '{"real-marketplace": {"url": "https://example.com"}}' > ~/.claude/plugins/known_marketplaces.json

OUTPUT=$($SCRIPT -p plugin@nonexistent -y 2>&1) || true
EXIT_CODE=0
$SCRIPT -p plugin@nonexistent -y >/dev/null 2>&1 || EXIT_CODE=$?

assert_exit_code_not "exit code is non-zero" 0 "$EXIT_CODE"
assert_contains "error mentions not found" "$OUTPUT" "not found"

print_summary
