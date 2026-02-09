# claude-plugin-install - Detailed Documentation

## Overview

`claude-plugin-install` is a workaround tool for a bug in Claude Code where plugin installation fails when a plugin with the same name exists in multiple marketplaces.

### The Bug

When you run `/plugin install superpowers@superpowers-marketplace` in Claude Code:

1. The system finds `superpowers` in `claude-plugins-official` (different marketplace)
2. It says "already installed" even though you asked for a different marketplace
3. The plugin doesn't work in your project

This tool fixes the issue by directly modifying the configuration files that Claude Code uses.

### Related Upstream Issues

* [anthropics/claude-code#20593](https://github.com/anthropics/claude-code/issues/20593) - Bug: wrong marketplace matching
* [anthropics/claude-code#14202](https://github.com/anthropics/claude-code/issues/14202) - Bug: projectPath scope issues

Please add a comment or reaction to these issues to help prioritize the fix!

## Requirements

* Python 3.10 or later
* Claude Code installed (`~/.claude/` directory exists)
* At least one marketplace configured in Claude Code

## Installation

### Method 1: Direct Download (Simplest)

```bash
curl -fsSL https://raw.githubusercontent.com/shibuido/claude-plugin-install/master/claude-plugin-install -o claude-plugin-install
chmod +x claude-plugin-install
```

### Method 2: Using uv (Modern, Handles Dependencies)

No download needed - run directly:

```bash
uv run https://raw.githubusercontent.com/shibuido/claude-plugin-install/master/claude-plugin-install -p superpowers@superpowers-marketplace
```

Or download and run:

```bash
curl -fsSL https://raw.githubusercontent.com/shibuido/claude-plugin-install/master/claude-plugin-install -o claude-plugin-install
chmod +x claude-plugin-install
uv run ./claude-plugin-install -p superpowers@superpowers-marketplace
```

### Method 3: Git Clone

```bash
git clone https://github.com/shibuido/claude-plugin-install.git
cd claude-plugin-install
./claude-plugin-install -p superpowers@superpowers-marketplace
```

### Method 4: pip venv (Traditional)

```bash
python3 -m venv .venv
source .venv/bin/activate
python claude-plugin-install -p superpowers@superpowers-marketplace
```

### Self-install (PATH Detection)

When run interactively, the tool checks if `claude-plugin-install` is available on your PATH. If not, it offers to create a symlink:

```
TIP: claude-plugin-install is not on your PATH.
  To make it available everywhere, run:
    mkdir -p ~/.local/bin && ln -sf /path/to/claude-plugin-install ~/.local/bin/claude-plugin-install

  Install now? [Y/n]
```

## Plugin Memory

Your plugins are remembered. Install once, select from menu forever.

Every plugin you install (or attempt to install) is recorded in a local cache. The next time you run `claude-plugin-install` with no arguments, you will see those plugins listed in the interactive menu -- ready to re-install with a single keypress.

### Where cache files live

```
~/.cache/shibuido/claude-plugin-install/
  plugins-cache.jsonl        # remembered plugins
  marketplace-cache.jsonl    # remembered marketplaces
  invocations.jsonl          # invocation log
```

If `XDG_CACHE_HOME` is set, it replaces `~/.cache`:

```
$XDG_CACHE_HOME/shibuido/claude-plugin-install/
```

### Marketplace Sync

Import all available plugins (with descriptions and versions) from your installed marketplaces:

```bash
# Sync all known marketplaces
./claude-plugin-install cache sync

# Sync a specific marketplace
./claude-plugin-install cache sync superpowers-marketplace
```

Sync reads each marketplace's `marketplace.json` and imports all plugin entries into the local cache. After syncing, `cache list` and the interactive menu show plugin descriptions and versions.

Sync is idempotent -- re-running it does not create duplicates.

## Interactive Mode

Run with no arguments to enter the interactive menu:

```bash
./claude-plugin-install
```

Example output:

```
Plugin Manager | Repo: /home/user/my-project

-- Installed plugins --------------------------
  1i. superpowers@superpowers-marketplace     :: Core skills library: TDD, debugging...  (local)
  2i. my-tool@my-marketplace                  :: Custom dev utilities  (local, global)

-- Available plugins --------------------------
  3a. other-plugin@some-marketplace           :: Useful plugin for X  (last: 2d ago, 3 installs)
  4a. brand-new@some-marketplace              :: Fresh plugin  (last: ?, 0 installs)

Select [1-4], type plugin@marketplace, or q to quit:
```

* **Installed plugins** show which scopes they are active in (local, shared, global).
* **Available plugins** show when they were last used and how many times they have been installed.
* Selecting an installed plugin offers to uninstall it.
* Selecting an available plugin installs it.
* You can also type a brand new `plugin@marketplace` string to install something fresh.

### Fuzzy Search

If `sk` (skim) or `fzf` is installed, the menu automatically uses fuzzy search instead of a numbered list. `sk` is preferred when both are available.

* Use **TAB** to toggle multiple selections
* Press **Enter** to confirm
* Press **ESC** to quit

The tool passes `--ansi --reverse --prompt "Plugin> "` to the finder.

### Fallback Mode

When neither `sk` nor `fzf` is available, the tool falls back to a numbered menu.

* Select by number, or type comma-separated numbers (e.g., `1,2,3`) to select multiple
* Type a new `plugin@marketplace` string to install directly
* Selecting an installed plugin offers to uninstall it
* Selecting an available plugin installs it

### CPI_MENU_LIMIT

Controls the maximum number of available plugins shown in fallback mode (default: 15).

```bash
CPI_MENU_LIMIT=30 ./claude-plugin-install
```

* Installed plugins are always shown regardless of the limit.
* When more plugins exist than the limit, the menu shows: `"... and N more plugins. Install sk or fzf for fuzzy search."`

## Uninstall

Remove a plugin from one or more scopes.

### Interactive uninstall

```bash
./claude-plugin-install uninstall superpowers@superpowers-marketplace
```

The tool detects which scopes the plugin is installed in and lets you choose.

### Non-interactive uninstall

```bash
# Remove from project-local scope
./claude-plugin-install uninstall superpowers@superpowers-marketplace -l -y

# Remove from user/global scope
./claude-plugin-install uninstall superpowers@superpowers-marketplace -g -y

# Remove from project-shared/repo scope
./claude-plugin-install uninstall superpowers@superpowers-marketplace -r -y

# Remove from all scopes
./claude-plugin-install uninstall superpowers@superpowers-marketplace --all -y
```

## Scope Shortcuts

| Flag | Scope | File |
|------|-------|------|
| `-l` | project-local | `.claude/settings.local.json` |
| `-r` | project-shared/repo | `.claude/settings.json` |
| `-g` | user/global | `~/.claude/settings.json` |

These shortcuts work for both install and uninstall:

```bash
# Install to global scope
./claude-plugin-install -p superpowers@superpowers-marketplace -g

# Uninstall from local scope
./claude-plugin-install uninstall superpowers@superpowers-marketplace -l -y
```

You can also use the long form `-s`/`--scope`:

```bash
./claude-plugin-install -p superpowers@superpowers-marketplace --scope user
./claude-plugin-install -p superpowers@superpowers-marketplace --scope project-shared
./claude-plugin-install -p superpowers@superpowers-marketplace --scope project-local
```

## Scope Options Explained

### project-local (default)

* Settings file: `.claude/settings.local.json`
* Scope: Current user, current project only
* Git: File is typically gitignored
* Use when: You want the plugin for yourself in this project

### project-shared

* Settings file: `.claude/settings.json`
* Scope: All users of this project
* Git: File is committed to git
* Use when: You want the plugin available to all collaborators

### user

* Settings file: `~/.claude/settings.json`
* Scope: All projects for current user
* Git: N/A (user home directory)
* Use when: You want the plugin everywhere

## Cache Management

Manage remembered plugins and marketplaces:

```bash
# List all remembered plugins
./claude-plugin-install cache list

# List remembered marketplaces
./claude-plugin-install cache list-marketplaces

# Forget a specific plugin
./claude-plugin-install cache remove superpowers@superpowers-marketplace

# Clear all plugin memory
./claude-plugin-install cache clear

# Import all plugins from marketplaces
./claude-plugin-install cache sync

# Import from a specific marketplace
./claude-plugin-install cache sync superpowers-marketplace
```

## Log Management

View and manage the invocation history:

```bash
# Show last 10 invocations (default)
./claude-plugin-install log show

# Show last 20 invocations
./claude-plugin-install log show --last 20

# Trim log to last 500 entries
./claude-plugin-install log trim --keep 500

# Trim entries older than 30 days
./claude-plugin-install log trim --days 30
```

## Non-interactive / CI Usage

For automated scripts and CI pipelines, combine `-p` with `-y`:

```bash
./claude-plugin-install -p superpowers@superpowers-marketplace -y
```

Add `-n` for dry-run (preview only):

```bash
./claude-plugin-install -p superpowers@superpowers-marketplace -y -n
```

Uninstall non-interactively (must specify scope):

```bash
./claude-plugin-install uninstall superpowers@superpowers-marketplace -l -y
./claude-plugin-install uninstall superpowers@superpowers-marketplace --all -y
```

## Usage

### Basic Usage

```bash
# Close Claude Code first, then:
./claude-plugin-install -p superpowers@superpowers-marketplace
```

### All Options

```
./claude-plugin-install [options]
./claude-plugin-install -p PLUGIN@MARKETPLACE [options]
./claude-plugin-install uninstall PLUGIN@MARKETPLACE [options]
./claude-plugin-install cache {list|list-marketplaces|remove|clear}
./claude-plugin-install log {show|trim}

Install options:
  -p, --plugin PLUGIN@MARKETPLACE
                        Plugin with marketplace (e.g., superpowers@superpowers-marketplace)
  -s, --scope {project-local,project-shared,user}
                        Installation scope (default: project-local)
  -l                    Shortcut: project-local scope
  -g                    Shortcut: user/global scope
  -r                    Shortcut: project-shared/repo scope
  -y, --yes             Non-interactive mode: skip all confirmation prompts
  -n, --dry-run         Show what would be done without making changes
  -v, --verbose         Increase verbosity (-v=INFO, -vv=DEBUG, -vvv=TRACE)
  -d, --project-path    Project path (default: current directory)
  -h, --help            Show help message

Uninstall options:
  plugin                PLUGIN@MARKETPLACE (positional argument)
  -l / -g / -r          Scope shortcut (required for non-interactive)
  --all                 Uninstall from all scopes
  -y, --yes             Non-interactive mode

Cache subcommands:
  list                  List remembered plugins
  list-marketplaces     List remembered marketplaces
  remove PLUGIN@MKTPL  Forget a specific plugin
  clear                 Clear all plugin memory
  sync [MARKETPLACE]    Import plugins from marketplaces (all if no argument)

Log subcommands:
  show                  Show recent invocations (--last N)
  trim                  Trim log entries (--keep N, --days N)

Environment variables:
  CPI_MENU_LIMIT        Max available plugins shown in fallback menu (default: 15)
```

### Examples

```bash
# Interactive menu (no arguments)
./claude-plugin-install

# Basic install for current project
./claude-plugin-install -p superpowers@superpowers-marketplace

# Non-interactive mode (for scripts)
./claude-plugin-install -p superpowers@superpowers-marketplace -y

# Preview changes without applying
./claude-plugin-install -p superpowers@superpowers-marketplace --dry-run

# Install globally for all projects
./claude-plugin-install -p superpowers@superpowers-marketplace -g

# Install to project-shared scope (committed to git)
./claude-plugin-install -p superpowers@superpowers-marketplace -r

# Verbose output for debugging
./claude-plugin-install -p superpowers@superpowers-marketplace -vvv

# Install for a specific project directory
./claude-plugin-install -p superpowers@superpowers-marketplace -d /path/to/project

# Uninstall interactively
./claude-plugin-install uninstall superpowers@superpowers-marketplace

# Uninstall from local scope, non-interactive
./claude-plugin-install uninstall superpowers@superpowers-marketplace -l -y

# Uninstall from all scopes
./claude-plugin-install uninstall superpowers@superpowers-marketplace --all -y

# View remembered plugins
./claude-plugin-install cache list

# View recent invocation log
./claude-plugin-install log show --last 5
```

## How It Works

The script performs these steps:

1. **Validates prerequisites**
   * Checks `~/.claude/plugins/known_marketplaces.json` exists
   * Verifies the marketplace is registered
   * Confirms the plugin cache exists at `~/.claude/plugins/cache/MARKETPLACE/PLUGIN/`

2. **Creates backups**
   * Backs up `installed_plugins.json` with timestamp
   * Backs up settings file if it exists

3. **Updates installed_plugins.json**
   * Adds a new entry to the plugin's installation array
   * Sets the correct scope and project path

4. **Updates settings file**
   * Creates/updates the settings file for the chosen scope
   * Adds `enabledPlugins` entry for the plugin

5. **Updates plugin memory**
   * Records the plugin in `plugins-cache.jsonl`
   * Records the marketplace in `marketplace-cache.jsonl`
   * Logs the invocation in `invocations.jsonl`

6. **Success**
   * Reports what was changed
   * Lists backup files created

## Troubleshooting

### "Marketplace not found"

The marketplace isn't registered in Claude Code. First, add it:

```
/plugin marketplace add owner/marketplace-name
```

Then run this script again.

### "Plugin cache not found"

The plugin hasn't been downloaded. This happens if:

1. The marketplace was just added but not synced
2. The plugin name is incorrect

Try running `/plugin marketplace add owner/marketplace-name` again in Claude Code.

### Plugin still not working after running the script

1. Make sure you closed Claude Code before running the script
2. Restart Claude Code completely
3. Check `/plugin` -> Installed tab
4. Try running with `-vvv` for full trace output

### "already installed" warning

The script detected the plugin is already configured. You can:

1. Press `n` to cancel and check if it's actually working
2. Press `y` to re-apply the fix anyway

## Safety Design

This tool follows conservative safety principles:

1. **Backup first** - All files are backed up with timestamps before modification
2. **Verify assumptions** - Checks file structure and prerequisites before proceeding
3. **Interactive by default** - Asks for confirmation at each step
4. **Verbose logging** - Full visibility into what's happening
5. **Fail-safe** - On any error, provides debug info for issue reporting
6. **No destructive ops** - Only adds entries, never removes existing ones (except uninstall)

## Contributing

### Report Issues

* For issues with this workaround tool: [shibuido/claude-plugin-install/issues](https://github.com/shibuido/claude-plugin-install/issues)
* For the upstream Claude Code bug: Add a comment to [#20593](https://github.com/anthropics/claude-code/issues/20593) or [#14202](https://github.com/anthropics/claude-code/issues/14202)

### Development

```bash
git clone https://github.com/shibuido/claude-plugin-install.git
cd claude-plugin-install

# Run tests
./testing/run_tests.sh

# Run with verbose output for debugging
./claude-plugin-install -p superpowers@superpowers-marketplace -vvv --dry-run
```

See [claude-plugin-install.DEV_NOTES.md](claude-plugin-install.DEV_NOTES.md) for developer internals and debugging workflows.

## License

Public domain / CC0
