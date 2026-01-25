# Claude Plugin Install - Archival Context

This directory contains the complete context, history, and artifacts from the development of the Claude Code plugin installation workaround tool.

## Origin

**Date:** 2026-01-24 to 2026-01-25

**Problem:** Claude Code has a bug where plugin installation fails when a plugin with the same name exists in multiple marketplaces. The installer:

1. Matches on plugin name only, ignoring the `@marketplace` qualifier
2. Reports the **wrong marketplace** in error messages
3. Refuses to install even with fully-qualified name like `superpowers@superpowers-marketplace`

**Root Cause:** Two bugs identified:

1. Plugin name resolution ignores marketplace qualifier (matches `superpowers@*` instead of exact `superpowers@superpowers-marketplace`)
2. Scope checking doesn't filter by `projectPath` - treats all `local` scope entries as conflicts

## GitHub Issues

### Primary Issues Filed

| Issue | Repository | Description | URL |
|-------|------------|-------------|-----|
| #20593 | anthropics/claude-code | Bug report: wrong marketplace matching | https://github.com/anthropics/claude-code/issues/20593 |
| #355 | obra/superpowers | Tracking issue for superpowers users | https://github.com/obra/superpowers/issues/355 |
| #11 | obra/superpowers-marketplace | Tracking issue for marketplace | https://github.com/obra/superpowers-marketplace/issues/11 |

### Related Existing Issues

| Issue | Repository | Description | URL |
|-------|------------|-------------|-----|
| #14202 | anthropics/claude-code | Plugin scope confusion (commented on) | https://github.com/anthropics/claude-code/issues/14202 |
| #20390 | anthropics/claude-code | Related plugin installation issues | https://github.com/anthropics/claude-code/issues/20390 |
| #20077 | anthropics/claude-code | Plugin scope issues | https://github.com/anthropics/claude-code/issues/20077 |
| #18322 | anthropics/claude-code | Project-scoped plugins | https://github.com/anthropics/claude-code/issues/18322 |
| #19743 | anthropics/claude-code | Plugin installation problems | https://github.com/anthropics/claude-code/issues/19743 |
| #14185 | anthropics/claude-code | Plugin scope handling | https://github.com/anthropics/claude-code/issues/14185 |

### GitHub Comment IDs

Comments posted with workaround script link:

- **anthropics/claude-code#14202** - Comment with gist link and context
- **anthropics/claude-code#20593** - New issue filed with full bug report

To edit a comment: `gh api repos/{owner}/{repo}/issues/comments/{id} -X PATCH -f body="..."`

## Gist

**URL:** https://gist.github.com/gwpl/cd6dcd899ca0acce1b4a1bc486d56a9e

**Contents:**

- `fix-superpowers-plugin.py` - Hardcoded workaround for superpowers plugin
- `fix-superpowers-plugin.README.md` - Documentation for hardcoded version
- `fix-selected-plugin.py` - Generic version with `-p PLUGIN -m MARKETPLACE` flags
- `fix-selected-plugin.README.md` - Documentation for generic version

**Raw download URL:**
```
curl -fsSL https://gist.githubusercontent.com/gwpl/cd6dcd899ca0acce1b4a1bc486d56a9e/raw/fix-selected-plugin.py -o fix-selected-plugin.py
```

## Files in This Archive

### Scripts (`archival/scripts/`)

| File | Description |
|------|-------------|
| `fix-selected-plugin.py` | **Generic workaround** - accepts any plugin/marketplace via CLI flags |
| `fix-selected-plugin.README.md` | Documentation for generic version |
| `fix-selected-plugin.test.py` | Automated test suite with tmux TUI verification |
| `fix-superpowers-plugin.py` | Original hardcoded version for superpowers only |
| `fix-superpowers-plugin.README.md` | Documentation for hardcoded version |

### Documentation (`archival/docs/`)

| File | Description |
|------|-------------|
| `2026-01-24--claude-code-plugin-scope-flakiness-investigation.md` | Deep investigation of the bug |
| `2026-01-24--claude-code-tui-tmux-send-keys-interaction.md` | tmux TUI interaction discoveries |

## Key Technical Details

### Plugin System Files

| File | Purpose |
|------|---------|
| `~/.claude/plugins/installed_plugins.json` | Central plugin registry |
| `~/.claude/plugins/known_marketplaces.json` | Registered marketplaces |
| `~/.claude/plugins/cache/{marketplace}/{plugin}/{version}/` | Plugin files |
| `.claude/settings.json` | Project-shared plugin settings |
| `.claude/settings.local.json` | Project-local plugin settings |
| `~/.claude/settings.json` | User-global plugin settings |

### Plugin Key Format

```
{plugin}@{marketplace}
```

Example: `superpowers@superpowers-marketplace`

### Installation Entry Format (installed_plugins.json)

```json
{
  "scope": "local",
  "projectPath": "/path/to/project",
  "installPath": "~/.claude/plugins/cache/marketplace/plugin/x.x.x",
  "version": "x.x.x",
  "installedAt": "2026-01-24T12:00:00.000000",
  "lastUpdated": "2026-01-24T12:00:00.000000"
}
```

### Settings Entry Format

```json
{
  "enabledPlugins": {
    "plugin@marketplace": true
  }
}
```

## Manual Workaround Steps

If the script doesn't work, the manual workaround is:

1. **Close Claude Code** in the target directory

2. **Edit `~/.claude/plugins/installed_plugins.json`:**
   - Add entry to `plugins["plugin@marketplace"]` array
   - Include: `scope`, `projectPath`, `installPath`, `version`, `installedAt`, `lastUpdated`

3. **Create/edit `.claude/settings.local.json`:**
   ```json
   {
     "enabledPlugins": {
       "plugin@marketplace": true
     }
   }
   ```

4. **Restart Claude Code** and verify with `/plugin` -> Installed tab

## tmux TUI Interaction Notes

Key discoveries for automating Claude Code TUI:

1. **1.5s delay required** between sending text and pressing Enter (readline timing)
2. **Trust dialog** appears for new directories - must press Enter to confirm
3. **Tab key** navigates between Browse/Installed/Marketplaces tabs
4. **Escape** closes dialogs, `/exit` exits Claude

Example tmux send-keys:
```bash
tmux send-keys -t target "text"
sleep 1.5
tmux send-keys -t target C-m  # Enter
```

## Test Script Features

The `fix-selected-plugin.test.py` includes:

- **Parametrized testing:** `-p PLUGIN`, `-m MARKETPLACE`, `-d DIRECTORY`
- **tmux integration:** `-t TARGET` for existing session, `-S SOCKET` for isolated
- **Retry mechanism:** `--tui-retries N` for flaky TUI tests
- **Pane size check:** Verifies terminal is large enough (90x25 minimum)
- **Auto-install:** Ensures plugin is installed before TUI verification
- **Trust dialog handling:** Automatically confirms trust prompt
- **Scrolling:** Navigates Installed list to find plugin

## Design Principles

1. **Safety first:** Always backup files before modification
2. **Non-destructive:** Only adds entries, never removes existing ones
3. **Interactive by default:** Asks for confirmation at each step
4. **Verbose errors:** On failure, provides full debug info for issue reporting
5. **Race condition awareness:** Warns about closing Claude Code first
6. **Idempotent:** Safe to run multiple times

## Future Work

To turn this into a proper `claude-plugin-install` utility:

1. Rename `fix-selected-plugin.py` to `claude-plugin-install` (no extension)
2. Keep the uv shebang for dependency-free execution
3. Add to PATH or create installation script
4. Consider adding:
   - `--uninstall` flag
   - `--list` to show installed plugins
   - `--update` to update plugin versions
   - Shell completions (bash, zsh, fish)

## Attribution

Developed with Claude Code (Opus 4.5) assistance.

**Author:** gwpl
**License:** Public domain / CC0 - use freely, no attribution required.
