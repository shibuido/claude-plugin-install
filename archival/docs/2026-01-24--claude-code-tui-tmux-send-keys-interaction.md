# Claude Code TUI Interaction via tmux send-keys

**Date:** 2026-01-24

## Problem Summary

Sending commands to Claude Code CLI TUI running in tmux via `send-keys` requires special handling due to:

1. **Race conditions** - Enter keypress arrives before text input fully processes
2. **Readline timing** - TUI readline initialization needs time to register input
3. **Escape sequence disambiguation** - tmux's `escape-time` setting affects key interpretation

## Solution: The 1.5-Second Delay Pattern

```bash
# ✅ WORKING PATTERN
tmux send-keys -t session:pane C-u                    # Clear line first
sleep 0.3                                              # Small delay
tmux send-keys -t session:pane '/plugin list'         # Send command text
sleep 1.5                                              # CRITICAL: Wait for readline
tmux send-keys -t session:pane C-m                    # Send Enter (carriage return)
```

**Why this works:**

* Readline initialization disables certain terminal translations
* Sending Enter **before** readline registers text causes autocomplete instead of execution
* 1.5s delay allows readline buffer to fully process input

## Enter Key Methods (All Equivalent for Execution)

| Method | Description | Recommendation |
|--------|-------------|----------------|
| `Enter` | tmux reserved keyword | Most readable |
| `C-m` | Ctrl+M / Carriage Return (ASCII 13, 0x0D) | Best for scripts |
| `C-j` | Ctrl+J / Line Feed (ASCII 10, 0x0A) | Unix-native alternative |
| `-H 0D` | Hexadecimal CR byte | Low-level control |

```bash
# All equivalent:
tmux send-keys -t pane "cmd" Enter
tmux send-keys -t pane "cmd" C-m
tmux send-keys -t pane "cmd" C-j
tmux send-keys -t pane "cmd" -H 0D
```

## Critical Flags

| Flag | Effect | When to Use |
|------|--------|-------------|
| `-l` | Literal mode - "Enter" → 5 chars E-n-t-e-r | **AVOID** when executing |
| `-R` | Reset terminal state | Before sending to TUI apps |
| `-t target` | Session:window.pane format | **ALWAYS** specify in scripts |

## Multiline Input Methods

### Method 1: load-buffer + paste-buffer (Recommended)

```bash
# Heredoc pattern
tmux load-buffer - <<'EOF'
First line of prompt
Second line
Code block here
EOF

tmux paste-buffer -t session:pane
sleep 2.0                              # Longer delay for large pastes
tmux send-keys -t session:pane C-m
```

### Method 2: Sequential send-keys with C-j

```bash
tmux send-keys -t pane "Line 1"
tmux send-keys -t pane C-j             # Newline (not Enter/execute)
tmux send-keys -t pane "Line 2"
sleep 1.5
tmux send-keys -t pane C-m             # Final execute
```

### Method 3: Claude Code Multiline (in-app)

| Terminal | Binding |
|----------|---------|
| macOS | Option+Enter |
| iTerm2/WezTerm/Ghostty | Shift+Enter |
| Universal | `\` + Enter (backslash escape) |
| VS Code/Alacritty | Run `/terminal-setup` first |

## tmux Configuration for TUI Apps

Add to `~/.tmux.conf`:

```bash
# Reduce escape-time for faster Escape key processing (default 500ms is too slow)
set-option -sg escape-time 10    # 10ms for local, 50ms for remote

# For Claude Code TUI specifically
set-option -g default-terminal "tmux-256color"
```

## Debugging Failed Commands

**Symptoms & Fixes:**

| Symptom | Cause | Fix |
|---------|-------|-----|
| Text appears but doesn't execute | Insufficient delay | Increase sleep to 2-3s |
| "E-n-t-e-r" appears literally | Used `-l` flag | Remove `-l` flag |
| Wrong pane receives input | Missing `-t` target | Always specify `-t session:pane` |
| Autocomplete triggers instead | Enter arrived before text | Add delay before Enter |

**Diagnostic commands:**

```bash
# Check pane exists
tmux list-panes -a | grep target-name

# Check pane not in copy mode
tmux display-message -t target '#{pane_in_mode}'

# Capture current content
tmux capture-pane -t target -p > /tmp/pane_content.txt

# Test with increased delay
tmux send-keys -t target "echo test" && sleep 3 && tmux send-keys -t target C-m
```

## Practical Script for Claude Code Automation

```bash
#!/bin/bash
# send_to_claude.sh - Reliably send commands to Claude Code TUI

TARGET="${1:-claude:0}"
CMD="$2"
DELAY="${3:-1.5}"

# Clear any existing input
tmux send-keys -t "$TARGET" C-u
sleep 0.2

# Send command text
echo "$CMD" | tmux load-buffer -
tmux paste-buffer -t "$TARGET"

# Wait for readline to process
sleep "$DELAY"

# Execute
tmux send-keys -t "$TARGET" C-m

# Optional: Capture result
sleep 1
tmux capture-pane -t "$TARGET" -p
```

**Usage:**

```bash
./send_to_claude.sh "vector_semantic_search_multiple_rest_adapter:0" "/help" 1.5
./send_to_claude.sh "claude:0" "/plugin list" 2.0
```

## Why This Complexity Exists

### Terminal Input Pipeline

```
User keystroke
    ↓
Keyboard scancode (0x1C for Enter)
    ↓
Kernel input subsystem (KEY_ENTER)
    ↓
Terminal emulator → ASCII CR (0x0D, '\r')
    ↓
PTY master → Line discipline
    ↓ ICRNL translation: '\r' → '\n'
    ↓ Canonical mode buffering
PTY slave
    ↓
Readline library → accept-line function
    ↓
Shell/Application command execution
```

### Race Condition Details

* `tmux send-keys` is **asynchronous** - returns immediately without waiting
* Text characters and Enter key travel through same pipeline
* If Enter arrives before readline buffer processes text, TUI may:
  * Trigger autocomplete
  * Execute empty command
  * Misinterpret as Escape sequence

### Empirical Timing Thresholds

| Operation | Minimum Delay | Recommended |
|-----------|--------------|-------------|
| Simple text command | 100ms | 500ms |
| TUI with readline | 1000ms | 1500ms |
| Large paste (>500 chars) | 1500ms | 2000ms+ |
| After Escape key | 100ms | 150ms |

## wait-for Pattern (Advanced)

For guaranteed sequential execution:

```bash
tmux send-keys -t work 'some_cmd; tmux wait-for -S done' C-m \; wait-for done
# Execution blocks until 'done' signal received
```

## References

* [tmux send-keys timing issues - GitHub #1778](https://github.com/tmux/tmux/issues/1778)
* [pchalasani/claude-code-tools](https://github.com/pchalasani/claude-code-tools) - tmux-cli plugin
* [The TTY demystified](https://www.linusakesson.net/programming/tty/)
* [tmux escape-time explanation](https://jeffkreeftmeijer.com/tmux-escape-time/)

---

## Testing Session Log (2026-01-24)

**Session:** `vector_semantic_search_multiple_rest_adapter:0`

**Failed attempts (no delay):**

```bash
tmux send-keys -t ... '/plugin install superpowers@superpowers-marketplace' Enter
# Result: Commands appeared on input line but didn't execute
```

**Working attempt (with 1.5s delay):**

```bash
tmux send-keys -t ... C-u
sleep 0.3
tmux send-keys -t ... '/help'
sleep 1.5
tmux send-keys -t ... C-m
# Result: Command executed successfully, plugin UI appeared
```
