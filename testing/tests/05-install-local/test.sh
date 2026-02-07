#!/usr/bin/env bash
set -euo pipefail

# Test: 05-install-local
# Description: Install a plugin with -l (project-local) scope and verify files

source /workspace/testing/lib/assertions.sh

SCRIPT="claude-plugin-install"
PLUGIN="superpowers"
MARKETPLACE="superpowers-marketplace"
PLUGIN_KEY="${PLUGIN}@${MARKETPLACE}"
export XDG_CACHE_HOME=/tmp/test-cache

echo "Test: 05-install-local -- Install plugin to project-local scope"

# Set up test repo
REPO_DIR="/tmp/test-repo-05"
rm -rf "$REPO_DIR"
mkdir -p "$REPO_DIR"
git init "$REPO_DIR" >/dev/null 2>&1

# Set up Claude plugin infrastructure
mkdir -p ~/.claude/plugins/cache/${MARKETPLACE}/${PLUGIN}/1.0.0
echo '{}' > ~/.claude/plugins/installed_plugins.json
echo "{\"${MARKETPLACE}\": {\"url\": \"https://example.com\"}}" > ~/.claude/plugins/known_marketplaces.json

# Run install with -l (project-local) -y (non-interactive)
OUTPUT=$($SCRIPT -p "$PLUGIN_KEY" -d "$REPO_DIR" -l -y 2>&1) || true

# Verify settings.local.json was created with plugin
SETTINGS_FILE="$REPO_DIR/.claude/settings.local.json"
assert_file_exists "settings.local.json exists" "$SETTINGS_FILE"
assert_json_has_key "settings has enabledPlugins" "$SETTINGS_FILE" "enabledPlugins"
assert_json_has_key "settings has plugin key" "$SETTINGS_FILE" "$PLUGIN_KEY"

# Verify installed_plugins.json was updated
INSTALLED_FILE="$HOME/.claude/plugins/installed_plugins.json"
assert_file_exists "installed_plugins.json exists" "$INSTALLED_FILE"
assert_json_has_key "installed_plugins has plugin" "$INSTALLED_FILE" "$PLUGIN_KEY"

print_summary
