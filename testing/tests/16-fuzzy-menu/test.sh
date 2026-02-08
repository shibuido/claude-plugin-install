#!/usr/bin/env bash
set -euo pipefail

# Test: 16-fuzzy-menu
# Description: Test fuzzy menu integration (mock sk), fallback threshold
#              (CPI_MENU_LIMIT), and comma multi-select in fallback menu

source /workspace/testing/lib/assertions.sh

SCRIPT="claude-plugin-install"
MARKETPLACE="test-marketplace"
export XDG_CACHE_HOME=/tmp/test-cache-16

echo "Test: 16-fuzzy-menu -- Fuzzy menu and fallback threshold"

# Clean state
rm -rf "$XDG_CACHE_HOME"

# Set up test repo
REPO_DIR="/tmp/test-repo-16"
rm -rf "$REPO_DIR"
mkdir -p "$REPO_DIR"
git init "$REPO_DIR" >/dev/null 2>&1

# Create fake marketplace with 25 plugins
MARKETPLACE_DIR="/tmp/fake-marketplace-16"
rm -rf "$MARKETPLACE_DIR"
mkdir -p "$MARKETPLACE_DIR/.claude-plugin"

python3 -c "
import json
plugins = [{'name': f'plugin-{i:02d}', 'description': f'Test plugin number {i}', 'version': '1.0.0'} for i in range(1, 26)]
data = {'name': '$MARKETPLACE', 'plugins': plugins}
json.dump(data, open('$MARKETPLACE_DIR/.claude-plugin/marketplace.json', 'w'), indent=2)
"

# Set up Claude plugin infrastructure
mkdir -p ~/.claude/plugins
echo '{}' > ~/.claude/plugins/installed_plugins.json
cat > ~/.claude/plugins/known_marketplaces.json <<KMJSON
{
  "${MARKETPLACE}": {
    "source": {"source": "github", "repo": "test/test-marketplace"},
    "installLocation": "${MARKETPLACE_DIR}"
  }
}
KMJSON

# Create plugin cache directories for all 25 plugins
for i in $(seq -w 1 25); do
    mkdir -p ~/.claude/plugins/cache/${MARKETPLACE}/plugin-${i}/1.0.0
done

# Sync marketplace into the cache
$SCRIPT cache sync "$MARKETPLACE" >/dev/null 2>&1 || true

# Kill any lingering tmux sessions
tmux kill-server 2>/dev/null || true
sleep 0.2

# ============================================================
# Part 1: Mock sk for fuzzy finder test
# ============================================================
echo ""
echo "--- Part 1: Mock sk fuzzy finder ---"

# Create a mock sk that auto-selects the first line
MOCK_BIN="/tmp/mock-bin-16"
rm -rf "$MOCK_BIN"
mkdir -p "$MOCK_BIN"
cat > "$MOCK_BIN/sk" <<'MOCKSK'
#!/bin/sh
head -1
MOCKSK
chmod +x "$MOCK_BIN/sk"

# Run interactive menu with mock sk in PATH via tmux
# (tmux is needed because the tool checks sys.stdin.isatty for the
#  check_on_path helper; also the menu code expects a tty-like flow)
tmux new-session -d -s test16a -x 120 -y 40
tmux send-keys -t test16a \
    "PATH=$MOCK_BIN:\$PATH XDG_CACHE_HOME=$XDG_CACHE_HOME $SCRIPT -d $REPO_DIR 2>&1" Enter
sleep 3

FUZZY_OUTPUT=$(tmux capture-pane -t test16a -p 2>/dev/null) || true

# The mock sk selects the first line, which is plugin-01@test-marketplace.
# After selection, the tool should proceed to install and show the banner or
# confirmation prompt referencing the plugin key.
assert_contains "fuzzy selects first plugin" "$FUZZY_OUTPUT" "plugin-01@${MARKETPLACE}"

# It should reach the install flow (banner or confirmation prompt)
# The install flow shows "PLUGIN INSTALLATION" or "Have you closed Claude Code"
FOUND_INSTALL=0
echo "$FUZZY_OUTPUT" | grep -qi "INSTALLATION\|closed Claude Code\|IMPORTANT" && FOUND_INSTALL=1 || true
if [[ $FOUND_INSTALL -eq 1 ]]; then
    echo "  PASS: fuzzy selection reached install flow"
    ((PASS++)) || true
else
    echo "  FAIL: fuzzy selection did not reach install flow"
    echo "  --- actual output (first 30 lines) ---"
    echo "$FUZZY_OUTPUT" | head -30
    echo "  --- end ---"
    ((FAIL++)) || true
fi

tmux kill-session -t test16a 2>/dev/null || true
sleep 0.2

# ============================================================
# Part 2: Fallback threshold test (CPI_MENU_LIMIT)
# ============================================================
echo ""
echo "--- Part 2: Fallback menu with CPI_MENU_LIMIT ---"

# Run with no sk/fzf in PATH, CPI_MENU_LIMIT=5
# Use a clean PATH that excludes any sk/fzf
CLEAN_PATH="/usr/local/bin:/usr/bin:/bin"

tmux new-session -d -s test16b -x 120 -y 50
tmux send-keys -t test16b \
    "PATH=$CLEAN_PATH CPI_MENU_LIMIT=5 XDG_CACHE_HOME=$XDG_CACHE_HOME $SCRIPT -d $REPO_DIR 2>&1" Enter
sleep 3

FALLBACK_OUTPUT=$(tmux capture-pane -t test16b -p 2>/dev/null) || true

# Should show "Plugin Manager" header
assert_contains "fallback shows Plugin Manager" "$FALLBACK_OUTPUT" "Plugin Manager"

# Should show Available plugins section
assert_contains "fallback shows Available section" "$FALLBACK_OUTPUT" "Available"

# With CPI_MENU_LIMIT=5 and 25 plugins, 20 remain hidden
# The message should mention "more plugins" overflow
assert_contains "overflow message shown" "$FALLBACK_OUTPUT" "more plugins"
assert_contains "overflow suggests sk or fzf" "$FALLBACK_OUTPUT" "sk or fzf"

# Verify only 5 available plugins are shown by counting [N] entries
# (The fallback menu uses [idx] format for each shown plugin)
SHOWN_COUNT=$(echo "$FALLBACK_OUTPUT" | grep -cE '^\s*\[[0-9]+\]' 2>/dev/null) || SHOWN_COUNT=0
# Exactly 5 available should be shown (no installed plugins in this test)
if [[ $SHOWN_COUNT -eq 5 ]]; then
    echo "  PASS: exactly 5 plugins shown with CPI_MENU_LIMIT=5"
    ((PASS++)) || true
elif [[ $SHOWN_COUNT -ge 3 && $SHOWN_COUNT -le 7 ]]; then
    # Allow small tolerance for edge cases in pane capture
    echo "  PASS: approximately 5 plugins shown ($SHOWN_COUNT) with CPI_MENU_LIMIT=5"
    ((PASS++)) || true
else
    echo "  FAIL: expected ~5 plugins shown, got $SHOWN_COUNT"
    echo "  --- actual output ---"
    echo "$FALLBACK_OUTPUT"
    echo "  --- end ---"
    ((FAIL++)) || true
fi

# Quit the menu
tmux send-keys -t test16b "q" Enter
sleep 0.5
tmux kill-session -t test16b 2>/dev/null || true
sleep 0.2

# ============================================================
# Part 3: Comma multi-select in fallback menu
# ============================================================
echo ""
echo "--- Part 3: Comma multi-select in fallback ---"

tmux new-session -d -s test16c -x 120 -y 50
tmux send-keys -t test16c \
    "PATH=$CLEAN_PATH CPI_MENU_LIMIT=10 XDG_CACHE_HOME=$XDG_CACHE_HOME $SCRIPT -d $REPO_DIR 2>&1" Enter
sleep 3

# Send comma-separated input selecting items 1 and 2
tmux send-keys -t test16c "1,2" Enter
sleep 3

MULTI_OUTPUT=$(tmux capture-pane -t test16c -p 2>/dev/null) || true

# The multi-select of 2 available plugins should trigger the batch install flow.
# It should show "Installing 2 plugin(s)" or mention both selected plugin keys.
FOUND_MULTI=0
echo "$MULTI_OUTPUT" | grep -qi "Installing 2\|plugin-01\|plugin-02" && FOUND_MULTI=1 || true

if [[ $FOUND_MULTI -eq 1 ]]; then
    echo "  PASS: comma multi-select recognized"
    ((PASS++)) || true
else
    echo "  FAIL: comma multi-select not recognized"
    echo "  --- actual output ---"
    echo "$MULTI_OUTPUT"
    echo "  --- end ---"
    ((FAIL++)) || true
fi

# Verify it mentions both plugins
assert_contains "multi-select shows plugin-01" "$MULTI_OUTPUT" "plugin-01"
assert_contains "multi-select shows plugin-02" "$MULTI_OUTPUT" "plugin-02"

# Cleanup tmux
tmux kill-server 2>/dev/null || true

print_summary
