#!/usr/bin/env bash
set -euo pipefail

# Test: 09-cache-operations
# Description: Test cache list, list-marketplaces, and remove operations

source /workspace/testing/lib/assertions.sh

SCRIPT="claude-plugin-install"
PLUGIN="superpowers"
MARKETPLACE="superpowers-marketplace"
PLUGIN_KEY="${PLUGIN}@${MARKETPLACE}"
export XDG_CACHE_HOME=/tmp/test-cache-09

echo "Test: 09-cache-operations -- Cache list, list-marketplaces, remove"

# Clean cache
rm -rf "$XDG_CACHE_HOME"

# Set up test repo
REPO_DIR="/tmp/test-repo-09"
rm -rf "$REPO_DIR"
mkdir -p "$REPO_DIR"
git init "$REPO_DIR" >/dev/null 2>&1

# Set up Claude plugin infrastructure
mkdir -p ~/.claude/plugins/cache/${MARKETPLACE}/${PLUGIN}/1.0.0
echo '{}' > ~/.claude/plugins/installed_plugins.json
echo "{\"${MARKETPLACE}\": {\"url\": \"https://example.com\"}}" > ~/.claude/plugins/known_marketplaces.json

# Install to populate cache
$SCRIPT -p "$PLUGIN_KEY" -d "$REPO_DIR" -l -y >/dev/null 2>&1 || true

# cache list -- should show the plugin
CACHE_LIST=$($SCRIPT cache list 2>&1) || true
assert_contains "cache list shows plugin" "$CACHE_LIST" "$PLUGIN_KEY"

# cache list-marketplaces -- should show the marketplace
MARKETPLACE_LIST=$($SCRIPT cache list-marketplaces 2>&1) || true
assert_contains "cache list-marketplaces shows marketplace" "$MARKETPLACE_LIST" "$MARKETPLACE"

# cache remove -- remove the plugin from memory
REMOVE_OUTPUT=$($SCRIPT cache remove "$PLUGIN_KEY" 2>&1) || true
assert_contains "cache remove confirms removal" "$REMOVE_OUTPUT" "Removed"

# Verify plugin is gone from cache
CACHE_LIST_AFTER=$($SCRIPT cache list 2>&1) || true
assert_not_contains "plugin no longer in cache list" "$CACHE_LIST_AFTER" "$PLUGIN_KEY"

print_summary
