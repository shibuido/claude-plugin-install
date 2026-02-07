#!/usr/bin/env bash
set -euo pipefail

# Test: 04-dry-run
# Description: Verify --dry-run (-n) mode previews without creating settings files
#
# The install flow requires:
# 1. A known marketplace in known_marketplaces.json
# 2. A plugin cache directory
# 3. An installed_plugins.json
# We set these up, then run with -n (dry-run) and verify no settings file is created.

source /workspace/testing/lib/assertions.sh

SCRIPT="claude-plugin-install"
PLUGIN="superpowers"
MARKETPLACE="superpowers-marketplace"
export XDG_CACHE_HOME=/tmp/test-cache

echo "Test: 04-dry-run -- Dry run creates no settings file"

# Set up a test git repo
REPO_DIR="/tmp/test-repo-04"
rm -rf "$REPO_DIR"
mkdir -p "$REPO_DIR"
git init "$REPO_DIR" >/dev/null 2>&1

# Set up the Claude plugin infrastructure the tool expects
mkdir -p ~/.claude/plugins/cache/${MARKETPLACE}/${PLUGIN}/1.0.0
echo '{}' > ~/.claude/plugins/installed_plugins.json
echo "{\"${MARKETPLACE}\": {\"url\": \"https://example.com\"}}" > ~/.claude/plugins/known_marketplaces.json

# Run in dry-run mode
OUTPUT=$($SCRIPT -p ${PLUGIN}@${MARKETPLACE} -d "$REPO_DIR" -n -y 2>&1) || true

# Verify no settings file was created
assert_file_not_exists "no settings.local.json created" "$REPO_DIR/.claude/settings.local.json"
assert_contains "output mentions DRY RUN" "$OUTPUT" "DRY RUN"

print_summary
