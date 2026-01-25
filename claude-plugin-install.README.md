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

## Usage

### Basic Usage

```bash
# Close Claude Code first, then:
./claude-plugin-install -p superpowers@superpowers-marketplace
```

### All Options

```
./claude-plugin-install -p PLUGIN@MARKETPLACE [options]

Required:
  -p, --plugin PLUGIN@MARKETPLACE
                        Plugin with marketplace (e.g., superpowers@superpowers-marketplace)

Optional:
  -s, --scope {project-local,project-shared,user}
                        Installation scope (default: project-local)
  -y, --yes             Non-interactive mode: skip all confirmation prompts
  -n, --dry-run         Show what would be done without making changes
  -v, --verbose         Enable verbose/debug output
  -d, --project-path    Project path (default: current directory)
  -h, --help            Show help message
```

### Examples

```bash
# Basic usage - install for current project
./claude-plugin-install -p superpowers@superpowers-marketplace

# Non-interactive mode (for scripts)
./claude-plugin-install -p superpowers@superpowers-marketplace -y

# Preview changes without applying
./claude-plugin-install -p superpowers@superpowers-marketplace --dry-run

# Install globally for all projects
./claude-plugin-install -p superpowers@superpowers-marketplace --scope user

# Debug mode with verbose output
./claude-plugin-install -p superpowers@superpowers-marketplace -v

# Install for a specific project directory
./claude-plugin-install -p superpowers@superpowers-marketplace -d /path/to/project
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

5. **Success**
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
4. Try running with `-v` for verbose output

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
6. **No destructive ops** - Only adds entries, never removes existing ones

## Contributing

### Report Issues

* For issues with this workaround tool: [shibuido/claude-plugin-install/issues](https://github.com/shibuido/claude-plugin-install/issues)
* For the upstream Claude Code bug: Add a comment to [#20593](https://github.com/anthropics/claude-code/issues/20593) or [#14202](https://github.com/anthropics/claude-code/issues/14202)

### Development

```bash
git clone https://github.com/shibuido/claude-plugin-install.git
cd claude-plugin-install

# Run tests
./tests/test_claude_plugin_install.py

# Run with verbose output for debugging
./claude-plugin-install -p superpowers@superpowers-marketplace -v --dry-run
```

## License

Public domain / CC0
