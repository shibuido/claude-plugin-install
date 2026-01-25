# Claude Code Plugin Installation Fix (Generic)

A generic workaround script for the Claude Code plugin installation bug. Works with **any plugin** from **any marketplace**.

> **Note:** For the superpowers plugin specifically, see `fix-superpowers-plugin.py` which has the plugin hardcoded for convenience.

## The Problem

When a plugin exists in multiple marketplaces, Claude Code's plugin installer:

1. Matches on plugin name only, ignoring the marketplace qualifier
2. Reports the **wrong marketplace** in error messages
3. Refuses to install even with fully-qualified name

## Quick Start

```bash
# Download
curl -fsSL https://gist.githubusercontent.com/gwpl/cd6dcd899ca0acce1b4a1bc486d56a9e/raw/fix-selected-plugin.py -o fix-selected-plugin.py
chmod +x fix-selected-plugin.py

# Close Claude Code first, then run:
./fix-selected-plugin.py -p PLUGIN_NAME -m MARKETPLACE_NAME
```

## Usage

```
./fix-selected-plugin.py -p PLUGIN -m MARKETPLACE [OPTIONS]

Required:
  -p, --plugin        Plugin name (e.g., superpowers, my-plugin)
  -m, --marketplace   Marketplace name (e.g., superpowers-marketplace)

Options:
  -h, --help          Show help message
  -y, --yes           Non-interactive mode (skip confirmations)
  -v, --verbose       Enable verbose/debug output
  -n, --dry-run       Show what would be done without changes
  -s, --scope SCOPE   Installation scope (default: project-local)
  -d, --project-path  Project path (default: current directory)
```

## Examples

```bash
# Install superpowers from superpowers-marketplace
./fix-selected-plugin.py -p superpowers -m superpowers-marketplace

# Install any plugin from any marketplace
./fix-selected-plugin.py -p my-plugin -m my-marketplace

# Non-interactive for scripts/automation
./fix-selected-plugin.py -p superpowers -m superpowers-marketplace -y

# Install globally for user (all projects)
./fix-selected-plugin.py -p superpowers -m superpowers-marketplace -s user

# Verbose output for debugging
./fix-selected-plugin.py -p superpowers -m superpowers-marketplace -v

# Preview without making changes
./fix-selected-plugin.py -p superpowers -m superpowers-marketplace -n
```

## Scope Options

| Scope | Flag | Settings File | Use Case |
|-------|------|--------------|----------|
| `project-local` | `-s project-local` | `.claude/settings.local.json` | Just you, this project (default) |
| `project-shared` | `-s project-shared` | `.claude/settings.json` | All users of this project |
| `user` | `-s user` | `~/.claude/settings.json` | You, all projects (global) |

## Safety Features

* **Backup First**: All files backed up with `.bak.YYYY-MM-DD--HH-MM-SS` extension
* **Verify Assumptions**: Checks marketplace registration and plugin cache exist
* **Interactive by Default**: Asks for confirmation at each step
* **Race Condition Warning**: Reminds you to close Claude Code before running
* **Debug Info**: On any error, provides full debug info for issue reporting
* **Non-destructive**: Only adds entries, never removes existing ones

## What It Does

### Files Modified

**1. `~/.claude/plugins/installed_plugins.json`**

Adds a new entry to the `"PLUGIN@MARKETPLACE"` array:

```json
{
  "scope": "local",
  "projectPath": "/your/project/path",
  "installPath": "~/.claude/plugins/cache/MARKETPLACE/PLUGIN/x.x.x",
  "version": "x.x.x",
  "installedAt": "2026-01-24T12:00:00.000000",
  "lastUpdated": "2026-01-24T12:00:00.000000"
}
```

**2. Project settings file** (depends on `--scope`):

Adds or merges:

```json
{
  "enabledPlugins": {
    "PLUGIN@MARKETPLACE": true
  }
}
```

### Prerequisites (verified by script)

* Marketplace registered in `~/.claude/plugins/known_marketplaces.json`
* Plugin cache exists at `~/.claude/plugins/cache/MARKETPLACE/PLUGIN/`

If missing, run first: `/plugin marketplace add OWNER/MARKETPLACE`

## Related Issues

* [anthropics/claude-code#20593](https://github.com/anthropics/claude-code/issues/20593) - Bug: wrong marketplace matching
* [anthropics/claude-code#14202](https://github.com/anthropics/claude-code/issues/14202) - Bug: projectPath scope issues

## License

Public domain / CC0 - use freely, no attribution required.
