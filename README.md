# claude-plugin-install

Fix Claude Code's plugin installation bug with one command. **Remembers your plugins -- install once, pick from menu next time.**

## Features

* **Plugin memory** -- Install once, select from an interactive menu forever. No more typing `plugin@marketplace` strings.
* **Fuzzy search** -- Auto-detects [sk](https://github.com/lotabout/skim) or [fzf](https://github.com/junegunn/fzf) for instant search with TAB multi-select (`--menu` to force mode)
* **Marketplace sync** -- Import all available plugins with descriptions from your marketplaces (`cache sync`)
* **Multi-scope** -- Install to project-local, project-shared, or user/global scope
* **Batch operations** -- Select multiple plugins at once (TAB in fuzzy mode, comma-separated in fallback)
* **Safety first** -- Timestamped backups, dry-run mode, interactive confirmations

## Quick Start

```bash
curl -fsSL https://raw.githubusercontent.com/shibuido/claude-plugin-install/master/claude-plugin-install -o claude-plugin-install
chmod +x claude-plugin-install
./claude-plugin-install -p superpowers@superpowers-marketplace
```

Or with [uv](https://docs.astral.sh/uv/) (no download needed):

```bash
uv run https://raw.githubusercontent.com/shibuido/claude-plugin-install/master/claude-plugin-install -p superpowers@superpowers-marketplace
```

The tool detects it's not on your PATH and offers to install itself. See the [full user manual](claude-plugin-install.README.md#installation) for more installation methods.

## The Problem

Claude Code fails to install plugins when the same plugin name exists in multiple marketplaces. You get "already installed" errors even though the plugin isn't working in your project.

**Add your voice to help prioritize the upstream fix:**

* [#20593](https://github.com/anthropics/claude-code/issues/20593) -- Wrong marketplace matching
* [#14202](https://github.com/anthropics/claude-code/issues/14202) -- Project scope confusion

## Documentation

| Document | Description |
|----------|-------------|
| [Full User Manual](claude-plugin-install.README.md) | All features, options, examples, troubleshooting |
| [Developer Notes](claude-plugin-install.DEV_NOTES.md) | Internals, debugging, architecture |
| [Testing Guide](testing/TESTING_DEVELOPER_GUIDELINES.md) | E2E test infrastructure and guidelines |
| [External Discussions](DISCUSSIONS.md) | Upstream issues, community links |

## Need Help?

* [Open an issue](https://github.com/shibuido/claude-plugin-install/issues) -- for problems with this tool
* [Upstream #20593](https://github.com/anthropics/claude-code/issues/20593) -- add "me too" to help prioritize the bug fix

## License

Public domain / CC0
