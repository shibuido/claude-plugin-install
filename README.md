# claude-plugin-install

Fix Claude Code's plugin installation bug with one command.

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

## Safety First

* Creates timestamped backups before any changes
* Validates assumptions before proceeding
* Interactive confirmation (use `-y` to skip)
* Dry-run mode available (`-n`)

## Usage

```bash
./claude-plugin-install -p PLUGIN@MARKETPLACE [options]

Options:
  -p, --plugin    Required. Plugin with marketplace (e.g., superpowers@superpowers-marketplace)
  -s, --scope     project-local (default), project-shared, or user
  -y, --yes       Non-interactive mode
  -n, --dry-run   Preview changes only
  -v, --verbose   Debug output
```

## Need Help?

* [Open an issue](https://github.com/shibuido/claude-plugin-install/issues) - for problems with this tool
* [Upstream #20593](https://github.com/anthropics/claude-code/issues/20593) - add "me too" to help prioritize the bug fix

## Detailed Documentation

See [claude-plugin-install.README.md](claude-plugin-install.README.md) for comprehensive docs.

## License

Public domain / CC0
