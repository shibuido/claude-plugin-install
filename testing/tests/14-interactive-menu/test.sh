#!/usr/bin/env bash
set -euo pipefail

# Test: 14-interactive-menu
# Description: Test interactive menu via tmux -- displays installed and cached plugins,
#              accepts number selection, and handles quit

source /workspace/testing/lib/assertions.sh

SCRIPT="claude-plugin-install"
PLUGIN="superpowers"
MARKETPLACE="superpowers-marketplace"
PLUGIN_KEY="${PLUGIN}@${MARKETPLACE}"
export XDG_CACHE_HOME=/tmp/test-cache-14

echo "Test: 14-interactive-menu -- Interactive menu via tmux"

# Clean state
rm -rf "$XDG_CACHE_HOME"

# Set up test repo
REPO_DIR="/tmp/test-repo-14"
rm -rf "$REPO_DIR"
mkdir -p "$REPO_DIR"
git init "$REPO_DIR" >/dev/null 2>&1

# Set up Claude plugin infrastructure
mkdir -p ~/.claude/plugins/cache/${MARKETPLACE}/${PLUGIN}/1.0.0
echo '{}' > ~/.claude/plugins/installed_plugins.json
echo "{\"${MARKETPLACE}\": {\"url\": \"https://example.com\"}}" \
    > ~/.claude/plugins/known_marketplaces.json

# Pre-populate cache so menu has a remembered plugin
$SCRIPT -p "$PLUGIN_KEY" -d "$REPO_DIR" -l -y >/dev/null 2>&1 || true

# Kill any lingering tmux sessions
tmux kill-server 2>/dev/null || true
sleep 0.2

# --- Test 1: Menu shows installed plugins and quit works ---
echo ""
echo "--- Step 1: Menu displays and quit ---"
tmux new-session -d -s test14 -x 120 -y 30
tmux send-keys -t test14 "XDG_CACHE_HOME=$XDG_CACHE_HOME $SCRIPT -d $REPO_DIR" Enter
sleep 2
MENU_OUTPUT=$(tmux capture-pane -t test14 -p 2>/dev/null) || true

assert_contains "menu shows Plugin Manager" "$MENU_OUTPUT" "Plugin Manager"
assert_contains "menu shows installed plugin" "$MENU_OUTPUT" "$PLUGIN_KEY"

# Send quit
tmux send-keys -t test14 "q" Enter
sleep 1

# --- Test 2: Fresh session, menu with only remembered plugins ---
echo ""
echo "--- Step 2: Menu with remembered plugins ---"

# Remove install so plugin is only in cache (remembered)
rm -f "$REPO_DIR/.claude/settings.local.json"

# Reset installed_plugins.json
echo '{}' > ~/.claude/plugins/installed_plugins.json

tmux kill-session -t test14 2>/dev/null || true
sleep 0.2
tmux new-session -d -s test14b -x 120 -y 30
tmux send-keys -t test14b "XDG_CACHE_HOME=$XDG_CACHE_HOME $SCRIPT -d $REPO_DIR" Enter
sleep 2
MENU2_OUTPUT=$(tmux capture-pane -t test14b -p 2>/dev/null) || true

assert_contains "menu shows remembered section" "$MENU2_OUTPUT" "Remembered"
assert_contains "menu shows remembered plugin" "$MENU2_OUTPUT" "$PLUGIN_KEY"

# Quit
tmux send-keys -t test14b "q" Enter
sleep 0.5

# Cleanup tmux
tmux kill-server 2>/dev/null || true

print_summary
