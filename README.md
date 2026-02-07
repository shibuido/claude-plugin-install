# claude-plugin-install

Fix Claude Code's plugin installation bug with one command. **Remembers your plugins -- install once, pick from menu next time.**

## The Problem

Claude Code fails to install plugins when the same plugin name exists in multiple marketplaces. You get "already installed" errors even though the plugin isn't working in your project.

**Upstream issues** (add your voice to help prioritize the fix!):

* [#20593](https://github.com/anthropics/claude-code/issues/20593) - Wrong marketplace matching
* [#14202](https://github.com/anthropics/claude-code/issues/14202) - Project scope confusion

## Quick Install

```bash
# Download
curl -fsSL https://raw.githubusercontent.com/shibuido/claude-plugin-install/master/claude-plugin-install -o claude-plugin-install
chmod +x claude-plugin-install

# Close Claude Code first, then run:
./claude-plugin-install -p superpowers@superpowers-marketplace
```

Or with `uv`:

```bash
uv run https://raw.githubusercontent.com/shibuido/claude-plugin-install/master/claude-plugin-install -p superpowers@superpowers-marketplace
```

## Plugin Memory

Every plugin you install is remembered automatically. Next time you run the tool, your plugins appear in an interactive menu -- no need to type the full `plugin@marketplace` string again.

Cache files live in `~/.cache/shibuido/claude-plugin-install/` (respects `XDG_CACHE_HOME`).

## Interactive Mode

Run with no arguments to get the interactive menu:

```bash
./claude-plugin-install
```

The menu shows installed plugins (with their scopes) and remembered plugins from previous sessions. Select by number or type a new `plugin@marketplace` to install.

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

Subcommands:
  uninstall       Remove a plugin from one or more scopes
  cache           Manage plugin memory (list, remove, clear)
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
