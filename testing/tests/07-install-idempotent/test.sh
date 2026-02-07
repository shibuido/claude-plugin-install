#!/usr/bin/env bash
set -euo pipefail

# Test: 07-install-idempotent
# Description: Install the same plugin twice with -l -y, verify settings are
#              not corrupted (valid JSON, plugin present, no duplicates in enabledPlugins)

source /workspace/testing/lib/assertions.sh

SCRIPT="claude-plugin-install"
PLUGIN="superpowers"
MARKETPLACE="superpowers-marketplace"
PLUGIN_KEY="${PLUGIN}@${MARKETPLACE}"
export XDG_CACHE_HOME=/tmp/test-cache

echo "Test: 07-install-idempotent -- Double install does not corrupt settings"

# Set up test repo
REPO_DIR="/tmp/test-repo-07"
rm -rf "$REPO_DIR"
mkdir -p "$REPO_DIR"
git init "$REPO_DIR" >/dev/null 2>&1

# Set up Claude plugin infrastructure
mkdir -p ~/.claude/plugins/cache/${MARKETPLACE}/${PLUGIN}/1.0.0
echo '{}' > ~/.claude/plugins/installed_plugins.json
echo "{\"${MARKETPLACE}\": {\"url\": \"https://example.com\"}}" > ~/.claude/plugins/known_marketplaces.json

# First install
$SCRIPT -p "$PLUGIN_KEY" -d "$REPO_DIR" -l -y >/dev/null 2>&1 || true

# Second install (should succeed or gracefully handle)
OUTPUT=$($SCRIPT -p "$PLUGIN_KEY" -d "$REPO_DIR" -l -y 2>&1) || true

SETTINGS_FILE="$REPO_DIR/.claude/settings.local.json"

# Verify settings is still valid JSON
assert_file_exists "settings.local.json exists" "$SETTINGS_FILE"

# Verify the file is valid JSON
VALID_JSON=$(python3 -c "
import json, sys
try:
    with open('$SETTINGS_FILE') as f:
        json.load(f)
    print('yes')
except:
    print('no')
")
assert_eq "settings file is valid JSON" "yes" "$VALID_JSON"

# Verify plugin is present exactly once in enabledPlugins
PLUGIN_COUNT=$(python3 -c "
import json
with open('$SETTINGS_FILE') as f:
    d = json.load(f)
ep = d.get('enabledPlugins', {})
count = sum(1 for k in ep if k == '$PLUGIN_KEY')
print(count)
")
assert_eq "plugin appears exactly once in enabledPlugins" "1" "$PLUGIN_COUNT"

print_summary
