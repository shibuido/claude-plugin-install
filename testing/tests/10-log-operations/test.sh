#!/usr/bin/env bash
set -euo pipefail

# Test: 10-log-operations
# Description: Test log show and log trim operations

source /workspace/testing/lib/assertions.sh

SCRIPT="claude-plugin-install"
PLUGIN="superpowers"
MARKETPLACE="superpowers-marketplace"
PLUGIN_KEY="${PLUGIN}@${MARKETPLACE}"
export XDG_CACHE_HOME=/tmp/test-cache-10

echo "Test: 10-log-operations -- Log show and trim"

# Clean cache
rm -rf "$XDG_CACHE_HOME"

# Set up test repo
REPO_DIR="/tmp/test-repo-10"
rm -rf "$REPO_DIR"
mkdir -p "$REPO_DIR"
git init "$REPO_DIR" >/dev/null 2>&1

# Set up Claude plugin infrastructure
mkdir -p ~/.claude/plugins/cache/${MARKETPLACE}/${PLUGIN}/1.0.0
echo '{}' > ~/.claude/plugins/installed_plugins.json
echo "{\"${MARKETPLACE}\": {\"url\": \"https://example.com\"}}" > ~/.claude/plugins/known_marketplaces.json

# Install to create a log entry
$SCRIPT -p "$PLUGIN_KEY" -d "$REPO_DIR" -l -y >/dev/null 2>&1 || true

# log show --last 1 -- should show the entry
LOG_OUTPUT=$($SCRIPT log show --last 1 2>&1) || true
assert_contains "log show displays entry" "$LOG_OUTPUT" "install"

# log trim --keep 1 -- should trim successfully
TRIM_OUTPUT=$($SCRIPT log trim --keep 1 2>&1) || true
assert_contains "log trim confirms action" "$TRIM_OUTPUT" "Trimmed"

# log show should still show at least 1 entry after trim
LOG_AFTER=$($SCRIPT log show --last 10 2>&1) || true
assert_contains "log still has entries after trim" "$LOG_AFTER" "install"

print_summary
