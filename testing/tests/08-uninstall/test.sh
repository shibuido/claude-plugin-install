#!/usr/bin/env bash
set -euo pipefail

# Test: 08-uninstall
# Description: Install then uninstall a plugin with -l -y, verify plugin removed from settings

source /workspace/testing/lib/assertions.sh

SCRIPT="claude-plugin-install"
PLUGIN="superpowers"
MARKETPLACE="superpowers-marketplace"
PLUGIN_KEY="${PLUGIN}@${MARKETPLACE}"
export XDG_CACHE_HOME=/tmp/test-cache

echo "Test: 08-uninstall -- Install then uninstall removes plugin"

# Set up test repo
REPO_DIR="/tmp/test-repo-08"
rm -rf "$REPO_DIR"
mkdir -p "$REPO_DIR"
git init "$REPO_DIR" >/dev/null 2>&1

# Set up Claude plugin infrastructure
mkdir -p ~/.claude/plugins/cache/${MARKETPLACE}/${PLUGIN}/1.0.0
echo '{}' > ~/.claude/plugins/installed_plugins.json
echo "{\"${MARKETPLACE}\": {\"url\": \"https://example.com\"}}" > ~/.claude/plugins/known_marketplaces.json

# Install
$SCRIPT -p "$PLUGIN_KEY" -d "$REPO_DIR" -l -y >/dev/null 2>&1 || true

SETTINGS_FILE="$REPO_DIR/.claude/settings.local.json"
assert_file_exists "settings exists after install" "$SETTINGS_FILE"
assert_json_has_key "plugin present after install" "$SETTINGS_FILE" "$PLUGIN_KEY"

# Uninstall
OUTPUT=$($SCRIPT uninstall "$PLUGIN_KEY" -d "$REPO_DIR" -l -y 2>&1) || true

# Verify plugin removed
PLUGIN_PRESENT=$(python3 -c "
import json, sys
try:
    with open('$SETTINGS_FILE') as f:
        d = json.load(f)
    ep = d.get('enabledPlugins', {})
    print('yes' if '$PLUGIN_KEY' in ep else 'no')
except:
    print('no')
")
assert_eq "plugin removed from enabledPlugins" "no" "$PLUGIN_PRESENT"

print_summary
