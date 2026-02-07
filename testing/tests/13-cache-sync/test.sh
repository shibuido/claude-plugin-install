#!/usr/bin/env bash
set -euo pipefail

# Test: 13-cache-sync
# Description: Test cache sync imports plugins from marketplace.json

source /workspace/testing/lib/assertions.sh

SCRIPT="claude-plugin-install"
MARKETPLACE="test-marketplace"
export XDG_CACHE_HOME=/tmp/test-cache-13

echo "Test: 13-cache-sync -- Cache sync imports plugins from marketplace"

# Clean state
rm -rf "$XDG_CACHE_HOME"

# Set up a fake marketplace with marketplace.json
MARKETPLACE_DIR="/tmp/fake-marketplace-13"
rm -rf "$MARKETPLACE_DIR"
mkdir -p "$MARKETPLACE_DIR/.claude-plugin"

cat > "$MARKETPLACE_DIR/.claude-plugin/marketplace.json" <<'MKJSON'
{
  "name": "test-marketplace",
  "plugins": [
    {
      "name": "alpha-plugin",
      "description": "First test plugin for alpha testing",
      "version": "1.0.0"
    },
    {
      "name": "beta-plugin",
      "description": "Second test plugin for beta testing",
      "version": "2.3.1"
    },
    {
      "name": "gamma-plugin",
      "description": "Third test plugin for gamma testing",
      "version": "0.5.0"
    }
  ]
}
MKJSON

# Set up known_marketplaces.json pointing to our fake marketplace
cat > ~/.claude/plugins/known_marketplaces.json <<KMJSON
{
  "${MARKETPLACE}": {
    "source": {"source": "github", "repo": "test/test-marketplace"},
    "installLocation": "${MARKETPLACE_DIR}"
  }
}
KMJSON

echo '{}' > ~/.claude/plugins/installed_plugins.json

# --- Test 1: Sync specific marketplace ---
echo ""
echo "--- Step 1: Sync specific marketplace ---"
SYNC_OUTPUT=$($SCRIPT cache sync "$MARKETPLACE" 2>&1) || true
assert_contains "sync reports success" "$SYNC_OUTPUT" "Synced"
assert_contains "sync reports 3 plugins" "$SYNC_OUTPUT" "3"

# --- Test 2: Verify cache list shows synced plugins with descriptions ---
echo ""
echo "--- Step 2: Verify cache list ---"
CACHE_LIST=$($SCRIPT cache list 2>&1) || true
assert_contains "alpha-plugin in cache" "$CACHE_LIST" "alpha-plugin@${MARKETPLACE}"
assert_contains "beta-plugin in cache" "$CACHE_LIST" "beta-plugin@${MARKETPLACE}"
assert_contains "gamma-plugin in cache" "$CACHE_LIST" "gamma-plugin@${MARKETPLACE}"
assert_contains "alpha description shown" "$CACHE_LIST" "First test plugin"
assert_contains "beta version shown" "$CACHE_LIST" "v2.3.1"

# --- Test 3: Re-sync is idempotent (0 new when nothing changed) ---
echo ""
echo "--- Step 3: Idempotent re-sync ---"
RESYNC_OUTPUT=$($SCRIPT cache sync "$MARKETPLACE" 2>&1) || true
assert_contains "re-sync reports 0 added" "$RESYNC_OUTPUT" "0"

# --- Test 4: Sync all marketplaces ---
echo ""
echo "--- Step 4: Sync all marketplaces ---"
# Clear cache first
$SCRIPT cache clear >/dev/null 2>&1 || true
SYNC_ALL=$($SCRIPT cache sync 2>&1) || true
assert_contains "sync all reports marketplace name" "$SYNC_ALL" "$MARKETPLACE"
assert_contains "sync all reports plugins count" "$SYNC_ALL" "3"

print_summary
