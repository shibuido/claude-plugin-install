#!/usr/bin/env bash
set -euo pipefail

# Test: 11-verbosity
# Description: Verify verbosity levels produce expected log prefixes in stderr

source /workspace/testing/lib/assertions.sh

SCRIPT="claude-plugin-install"
PLUGIN="superpowers"
MARKETPLACE="superpowers-marketplace"
PLUGIN_KEY="${PLUGIN}@${MARKETPLACE}"
export XDG_CACHE_HOME=/tmp/test-cache-11

echo "Test: 11-verbosity -- Verbosity flag levels"

# Clean
rm -rf "$XDG_CACHE_HOME"

# Set up test repo
REPO_DIR="/tmp/test-repo-11"
rm -rf "$REPO_DIR"
mkdir -p "$REPO_DIR"
git init "$REPO_DIR" >/dev/null 2>&1

# Set up Claude plugin infrastructure
mkdir -p ~/.claude/plugins/cache/${MARKETPLACE}/${PLUGIN}/1.0.0
echo '{}' > ~/.claude/plugins/installed_plugins.json
echo "{\"${MARKETPLACE}\": {\"url\": \"https://example.com\"}}" > ~/.claude/plugins/known_marketplaces.json

# Run with -v, capture stderr
OUTPUT_V=$($SCRIPT -p "$PLUGIN_KEY" -d "$REPO_DIR" -l -y -n -v 2>&1) || true
assert_contains "-v produces INFO output" "$OUTPUT_V" "INFO:"

# Run with -vvv, capture stderr
OUTPUT_VVV=$($SCRIPT -p "$PLUGIN_KEY" -d "$REPO_DIR" -l -y -n -vvv 2>&1) || true
assert_contains "-vvv produces TRACE output" "$OUTPUT_VVV" "TRACE:"

print_summary
