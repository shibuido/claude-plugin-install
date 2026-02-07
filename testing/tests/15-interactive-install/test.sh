#!/usr/bin/env bash
set -euo pipefail

# Test: 15-interactive-install
# Description: Test interactive install confirmation flow via tmux --
#              responds to prompts and verifies plugin gets installed

source /workspace/testing/lib/assertions.sh

SCRIPT="claude-plugin-install"
PLUGIN="superpowers"
MARKETPLACE="superpowers-marketplace"
PLUGIN_KEY="${PLUGIN}@${MARKETPLACE}"
export XDG_CACHE_HOME=/tmp/test-cache-15

echo "Test: 15-interactive-install -- Interactive install confirmation via tmux"

# Clean state
rm -rf "$XDG_CACHE_HOME"

# Set up test repo
REPO_DIR="/tmp/test-repo-15"
rm -rf "$REPO_DIR"
mkdir -p "$REPO_DIR"
git init "$REPO_DIR" >/dev/null 2>&1

# Set up Claude plugin infrastructure
mkdir -p ~/.claude/plugins/cache/${MARKETPLACE}/${PLUGIN}/1.0.0
echo '{}' > ~/.claude/plugins/installed_plugins.json
echo "{\"${MARKETPLACE}\": {\"url\": \"https://example.com\"}}" \
    > ~/.claude/plugins/known_marketplaces.json

# Kill any lingering tmux sessions
tmux kill-server 2>/dev/null || true
sleep 0.2

SETTINGS_FILE="$REPO_DIR/.claude/settings.local.json"

# --- Test 1: Interactive install answering 'y' to all prompts ---
echo ""
echo "--- Step 1: Interactive install with confirmation ---"
tmux new-session -d -s test15 -x 120 -y 40
tmux send-keys -t test15 "XDG_CACHE_HOME=$XDG_CACHE_HOME $SCRIPT -p $PLUGIN_KEY -d $REPO_DIR -l" Enter

# Wait for first prompt: "Have you closed Claude Code?"
sleep 2
tmux send-keys -t test15 "y" Enter

# Wait for second prompt: "Proceed with modifications?"
sleep 2
tmux send-keys -t test15 "y" Enter

# Wait for install to complete
sleep 2

INSTALL_OUTPUT=$(tmux capture-pane -t test15 -p 2>/dev/null) || true

assert_contains "shows success message" "$INSTALL_OUTPUT" "SUCCESS"
assert_file_exists "settings.local.json created" "$SETTINGS_FILE"
assert_json_has_key "plugin in settings" "$SETTINGS_FILE" "$PLUGIN_KEY"

# --- Test 2: Interactive install declining at first prompt ---
echo ""
echo "--- Step 2: Interactive install with decline ---"

# Clean up for second test
rm -f "$SETTINGS_FILE"
echo '{}' > ~/.claude/plugins/installed_plugins.json

tmux kill-session -t test15 2>/dev/null || true
sleep 0.2

REPO_DIR2="/tmp/test-repo-15b"
rm -rf "$REPO_DIR2"
mkdir -p "$REPO_DIR2"
git init "$REPO_DIR2" >/dev/null 2>&1

tmux new-session -d -s test15b -x 120 -y 40
tmux send-keys -t test15b "XDG_CACHE_HOME=$XDG_CACHE_HOME $SCRIPT -p $PLUGIN_KEY -d $REPO_DIR2 -l" Enter

# Wait for first prompt, answer 'n'
sleep 2
tmux send-keys -t test15b "n" Enter
sleep 1

DECLINE_OUTPUT=$(tmux capture-pane -t test15b -p 2>/dev/null) || true
SETTINGS_FILE2="$REPO_DIR2/.claude/settings.local.json"

assert_contains "shows close message" "$DECLINE_OUTPUT" "close Claude Code"
assert_file_not_exists "no settings created on decline" "$SETTINGS_FILE2"

# Cleanup tmux
tmux kill-server 2>/dev/null || true

print_summary
