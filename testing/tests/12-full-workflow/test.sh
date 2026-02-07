#!/usr/bin/env bash
set -euo pipefail

# Test: 12-full-workflow
# Description: Full user story: install -> verify cache -> verify log ->
#              uninstall -> verify memory preserved -> cache remove -> verify forgotten

source /workspace/testing/lib/assertions.sh

SCRIPT="claude-plugin-install"
PLUGIN="superpowers"
MARKETPLACE="superpowers-marketplace"
PLUGIN_KEY="${PLUGIN}@${MARKETPLACE}"
export XDG_CACHE_HOME=/tmp/test-cache-12

echo "Test: 12-full-workflow -- Complete install/uninstall/cache lifecycle"

# Clean state
rm -rf "$XDG_CACHE_HOME"

# Set up test repo
REPO_DIR="/tmp/test-repo-12"
rm -rf "$REPO_DIR"
mkdir -p "$REPO_DIR"
git init "$REPO_DIR" >/dev/null 2>&1

# Set up Claude plugin infrastructure
mkdir -p ~/.claude/plugins/cache/${MARKETPLACE}/${PLUGIN}/1.0.0
echo '{}' > ~/.claude/plugins/installed_plugins.json
echo "{\"${MARKETPLACE}\": {\"url\": \"https://example.com\"}}" > ~/.claude/plugins/known_marketplaces.json

SETTINGS_FILE="$REPO_DIR/.claude/settings.local.json"

# --- Step 1: Install ---
echo ""
echo "--- Step 1: Install ---"
$SCRIPT -p "$PLUGIN_KEY" -d "$REPO_DIR" -l -y >/dev/null 2>&1 || true
assert_file_exists "settings file created after install" "$SETTINGS_FILE"
assert_json_has_key "plugin present in settings" "$SETTINGS_FILE" "$PLUGIN_KEY"

# --- Step 2: Verify cache has the plugin ---
echo ""
echo "--- Step 2: Verify cache ---"
CACHE_LIST=$($SCRIPT cache list 2>&1) || true
assert_contains "cache remembers plugin" "$CACHE_LIST" "$PLUGIN_KEY"

# --- Step 3: Verify log has an entry ---
echo ""
echo "--- Step 3: Verify log ---"
LOG_OUTPUT=$($SCRIPT log show --last 5 2>&1) || true
assert_contains "log has install entry" "$LOG_OUTPUT" "install"

# --- Step 4: Uninstall ---
echo ""
echo "--- Step 4: Uninstall ---"
$SCRIPT uninstall "$PLUGIN_KEY" -d "$REPO_DIR" -l -y >/dev/null 2>&1 || true
PLUGIN_PRESENT=$(python3 -c "
import json
with open('$SETTINGS_FILE') as f:
    d = json.load(f)
ep = d.get('enabledPlugins', {})
print('yes' if '$PLUGIN_KEY' in ep else 'no')
")
assert_eq "plugin removed from settings after uninstall" "no" "$PLUGIN_PRESENT"

# --- Step 5: Verify memory preserved after uninstall ---
echo ""
echo "--- Step 5: Verify memory preserved ---"
CACHE_AFTER_UNINSTALL=$($SCRIPT cache list 2>&1) || true
assert_contains "cache still remembers plugin after uninstall" "$CACHE_AFTER_UNINSTALL" "$PLUGIN_KEY"

# --- Step 6: Cache remove ---
echo ""
echo "--- Step 6: Cache remove ---"
$SCRIPT cache remove "$PLUGIN_KEY" >/dev/null 2>&1 || true
CACHE_AFTER_REMOVE=$($SCRIPT cache list 2>&1) || true
assert_not_contains "plugin forgotten after cache remove" "$CACHE_AFTER_REMOVE" "$PLUGIN_KEY"

print_summary
