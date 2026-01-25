# Claude Code Superpowers Plugin Installation Fix

A robust workaround script for the Claude Code plugin installation bug where plugins with the same name in different marketplaces cause flaky installation failures.

## The Problem

When `superpowers` exists in **both** `claude-plugins-official` AND `superpowers-marketplace`, Claude Code's plugin installer:

1. Matches on plugin name only, ignoring the marketplace qualifier
2. Reports the **wrong marketplace** in error messages
3. Refuses to install even with fully-qualified name

**Example error:**

```
❯ /plugin install superpowers@superpowers-marketplace
  ⎿  Plugin 'superpowers@claude-plugins-official' is already installed.
```

Note: User requested `@superpowers-marketplace` but error refers to `@claude-plugins-official`.

## Quick Start

```bash
# Download and run (requires uv)
curl -fsSL https://gist.githubusercontent.com/gwpl/cd6dcd899ca0acce1b4a1bc486d56a9e/raw/fix-superpowers-plugin.py -o fix-superpowers-plugin.py
chmod +x fix-superpowers-plugin.py

# Close Claude Code first, then run:
./fix-superpowers-plugin.py
```

Or with `uv run`:

```bash
uv run fix-superpowers-plugin.py
```

## Usage

```
./fix-superpowers-plugin.py [OPTIONS]

Options:
  -h, --help            Show help message
  -y, --yes             Non-interactive mode (skip confirmations)
  -v, --verbose         Enable verbose/debug output
  --dry-run             Show what would be done without changes
  --scope {project-local,project-shared,user}
                        Installation scope (default: project-local)
  --project-path PATH   Project path (default: current directory)
```

## Scope Options

| Scope | Settings File | Use Case |
|-------|--------------|----------|
| `project-local` | `.claude/settings.local.json` | Just you, this project (default) |
| `project-shared` | `.claude/settings.json` | All users of this project (committed to git) |
| `user` | `~/.claude/settings.json` | You, all projects (global) |

## Examples

```bash
# Interactive mode (asks for confirmation)
./fix-superpowers-plugin.py

# Non-interactive for scripts/automation
./fix-superpowers-plugin.py -y

# Install for all project users (shared)
./fix-superpowers-plugin.py --scope project-shared

# Verbose output for debugging
./fix-superpowers-plugin.py -v

# See what would happen without making changes
./fix-superpowers-plugin.py --dry-run
```

## Safety Features

* **Backup First**: All files backed up with `.bak.YYYY-MM-DD--HH-MM-SS` extension before modification
* **Verify Assumptions**: Checks file structure and marketplace registration before proceeding
* **Interactive by Default**: Asks for confirmation at each step
* **Race Condition Warning**: Reminds you to close Claude Code before running
* **Debug Info**: On any error, provides full debug info for issue reporting
* **Non-destructive**: Only adds entries, never removes existing ones

## Related Issues

* [anthropics/claude-code#20593](https://github.com/anthropics/claude-code/issues/20593) - Bug: wrong marketplace matching
* [anthropics/claude-code#14202](https://github.com/anthropics/claude-code/issues/14202) - Bug: projectPath scope issues
* [obra/superpowers-marketplace#11](https://github.com/obra/superpowers-marketplace/issues/11) - Tracking: workaround & info
* [obra/superpowers#355](https://github.com/obra/superpowers/issues/355) - Pointer: visibility for users

## Requirements

* Python 3.10+
* [uv](https://github.com/astral-sh/uv) (for shebang execution) or run directly with `python3`

## What It Does

### Files Modified

**1. `~/.claude/plugins/installed_plugins.json`**

Adds a new entry to the `"superpowers@superpowers-marketplace"` array:

```json
{
  "scope": "local",
  "projectPath": "/your/project/path",
  "installPath": "~/.claude/plugins/cache/superpowers-marketplace/superpowers/4.x.x",
  "version": "4.x.x",
  "installedAt": "2026-01-24T12:00:00.000000",
  "lastUpdated": "2026-01-24T12:00:00.000000"
}
```

**2. Project settings file** (depends on `--scope`):

| Scope | File |
|-------|------|
| `project-local` (default) | `.claude/settings.local.json` |
| `project-shared` | `.claude/settings.json` |
| `user` | `~/.claude/settings.json` |

Adds or merges:

```json
{
  "enabledPlugins": {
    "superpowers@superpowers-marketplace": true
  }
}
```

### Prerequisites (verified by script)

* `superpowers-marketplace` registered in `~/.claude/plugins/known_marketplaces.json`
* Plugin cache exists at `~/.claude/plugins/cache/superpowers-marketplace/superpowers/`

If missing, run first: `/plugin marketplace add obra/superpowers-marketplace`

### Steps Performed

1. Verifies prerequisites (marketplace registered, cache exists)
2. Checks if already installed for this project
3. Creates timestamped backups of files to be modified
4. Adds entry to `installed_plugins.json`
5. Creates/updates settings with `enabledPlugins`

## After Running

1. Start Claude Code: `claude`
2. Run `/plugin` and check the **Installed** tab
3. You should see: `superpowers Plugin · superpowers-marketplace · ✔ enabled`

## License

Public domain / CC0 - use freely, no attribution required.
