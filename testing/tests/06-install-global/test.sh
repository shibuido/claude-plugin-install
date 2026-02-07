#!/usr/bin/env bash
set -euo pipefail

# Test: 06-install-global
# Description: Install a plugin with -g (user/global) scope and verify files

source /workspace/testing/lib/assertions.sh

SCRIPT="claude-plugin-install"
PLUGIN="superpowers"
MARKETPLACE="superpowers-marketplace"
PLUGIN_KEY="${PLUGIN}@${MARKETPLACE}"
export XDG_CACHE_HOME=/tmp/test-cache

echo "Test: 06-install-global -- Install plugin to user/global scope"

# Set up test repo (still needed as working directory context)
REPO_DIR="/tmp/test-repo-06"
rm -rf "$REPO_DIR"
mkdir -p "$REPO_DIR"
git init "$REPO_DIR" >/dev/null 2>&1

# Set up Claude plugin infrastructure
mkdir -p ~/.claude/plugins/cache/${MARKETPLACE}/${PLUGIN}/1.0.0
echo '{}' > ~/.claude/plugins/installed_plugins.json
echo "{\"${MARKETPLACE}\": {\"url\": \"https://example.com\"}}" > ~/.claude/plugins/known_marketplaces.json

# Ensure no pre-existing global settings
rm -f ~/.claude/settings.json

# Run install with -g (global/user) -y (non-interactive)
OUTPUT=$($SCRIPT -p "$PLUGIN_KEY" -d "$REPO_DIR" -g -y 2>&1) || true

# Verify ~/.claude/settings.json was created with plugin
GLOBAL_SETTINGS="$HOME/.claude/settings.json"
assert_file_exists "global settings.json exists" "$GLOBAL_SETTINGS"
assert_json_has_key "global settings has enabledPlugins" "$GLOBAL_SETTINGS" "enabledPlugins"
assert_json_has_key "global settings has plugin key" "$GLOBAL_SETTINGS" "$PLUGIN_KEY"

print_summary
