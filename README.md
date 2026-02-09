# claude-plugin-install

Fix Claude Code's plugin installation bug with one command. **Remembers your plugins -- install once, pick from menu next time.**

## The Problem

Claude Code fails to install plugins when the same plugin name exists in multiple marketplaces. You get "already installed" errors even though the plugin isn't working in your project.

**Upstream issues** (add your voice to help prioritize the fix!):

* [#20593](https://github.com/anthropics/claude-code/issues/20593) - Wrong marketplace matching
* [#14202](https://github.com/anthropics/claude-code/issues/14202) - Project scope confusion

## Installation

### One-liner (download and run)

```bash
curl -fsSL https://raw.githubusercontent.com/shibuido/claude-plugin-install/master/claude-plugin-install -o claude-plugin-install
chmod +x claude-plugin-install
./claude-plugin-install -p superpowers@superpowers-marketplace
```

The tool will detect it's not on your PATH and offer to install itself automatically.

### With uv (no download needed)

```bash
uv run https://raw.githubusercontent.com/shibuido/claude-plugin-install/master/claude-plugin-install -p superpowers@superpowers-marketplace
```

### Permanent install (symlink to PATH)

```bash
# Clone the repo
git clone https://github.com/shibuido/claude-plugin-install.git
cd claude-plugin-install

# Symlink to ~/.local/bin (or any directory on your PATH)
mkdir -p ~/.local/bin
ln -sf "$(pwd)/claude-plugin-install" ~/.local/bin/claude-plugin-install

# Now available everywhere:
claude-plugin-install -p superpowers@superpowers-marketplace
```

### Self-install prompt

When run interactively, the tool checks if `claude-plugin-install` is available on your PATH. If not, it shows a one-liner to install and offers to do it for you:

```
TIP: claude-plugin-install is not on your PATH.
  To make it available everywhere, run:
    mkdir -p ~/.local/bin && ln -sf /path/to/claude-plugin-install ~/.local/bin/claude-plugin-install

  Install now? [Y/n]
```

## Plugin Memory

Every plugin you install is remembered automatically. Next time you run the tool, your plugins appear in an interactive menu -- no need to type the full `plugin@marketplace` string again.

### Marketplace Sync

Import all available plugins (with descriptions and versions) from your installed marketplaces:

```bash
# Sync all known marketplaces
./claude-plugin-install cache sync

# Sync a specific marketplace
./claude-plugin-install cache sync superpowers-marketplace
```

After syncing, `cache list` and the interactive menu show plugin descriptions.

Cache files live in `~/.cache/shibuido/claude-plugin-install/` (respects `XDG_CACHE_HOME`).

## Interactive Mode

Run with no arguments to get the interactive menu:

```bash
./claude-plugin-install
```

The menu shows installed plugins (with their scopes) and remembered plugins from previous sessions.

**Fuzzy search:** If `sk` ([skim](https://github.com/lotabout/skim)) or `fzf` is installed, the menu uses fuzzy search instead of a numbered list. `sk` is preferred when both are available.

* In fuzzy mode, use **TAB** to toggle multiple selections, then press **Enter** to confirm.
* In fallback (numbered) mode, select by number or type comma-separated numbers (e.g., `1,2,3`) to install multiple plugins at once. You can also type a new `plugin@marketplace` to install directly.

**`CPI_MENU_LIMIT`:** Controls how many available plugins are shown in the fallback numbered menu (default: 15). Set this environment variable to see more or fewer entries:

```bash
CPI_MENU_LIMIT=30 ./claude-plugin-install
```

## Uninstall

```bash
# Interactive scope selection
./claude-plugin-install uninstall superpowers@superpowers-marketplace

# Non-interactive: local scope
./claude-plugin-install uninstall superpowers@superpowers-marketplace -l -y

# Non-interactive: all scopes
./claude-plugin-install uninstall superpowers@superpowers-marketplace --all -y
```

## Safety First

* Creates timestamped backups before any changes
* Validates assumptions before proceeding
* Interactive confirmation (use `-y` to skip)
* Dry-run mode available (`-n`)

## Usage

```bash
./claude-plugin-install                                         # interactive menu
./claude-plugin-install -p PLUGIN@MARKETPLACE [options]         # install
./claude-plugin-install uninstall PLUGIN@MARKETPLACE [options]  # uninstall
./claude-plugin-install cache list                              # list remembered plugins
./claude-plugin-install cache sync                              # import from marketplaces
./claude-plugin-install log show --last 20                      # show recent invocations

Options:
  -p, --plugin    Plugin with marketplace (e.g., superpowers@superpowers-marketplace)
  -s, --scope     project-local (default), project-shared, or user
  -l              Shortcut: project-local scope
  -g              Shortcut: user/global scope
  -r              Shortcut: project-shared/repo scope
  -y, --yes       Non-interactive mode
  -n, --dry-run   Preview changes only
  -v              Verbose output (-v info, -vv debug, -vvv trace)
  -d              Project path (default: current directory)

Environment variables:
  CPI_MENU_LIMIT  Max plugins shown in fallback menu (default: 15)

Subcommands:
  uninstall       Remove a plugin from one or more scopes
  cache           Manage plugin memory (list, sync, remove, clear)
  log             View and trim invocation history (show, trim)
```

## Need Help?

* [Open an issue](https://github.com/shibuido/claude-plugin-install/issues) - for problems with this tool
* [Upstream #20593](https://github.com/anthropics/claude-code/issues/20593) - add "me too" to help prioritize the bug fix

## Detailed Documentation

See [claude-plugin-install.README.md](claude-plugin-install.README.md) for comprehensive docs.

Developer internals and debugging: [claude-plugin-install.DEV_NOTES.md](claude-plugin-install.DEV_NOTES.md).

## License

Public domain / CC0
