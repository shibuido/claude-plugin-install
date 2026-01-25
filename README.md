# claude-plugin-install

A workaround tool for Claude Code plugin installation bugs.

## Problem

Claude Code has a bug where plugin installation fails when a plugin with the same name exists in multiple marketplaces. For example, installing `superpowers@superpowers-marketplace` fails because `superpowers@claude-plugins-official` exists.

**Tracked in:** [anthropics/claude-code#20593](https://github.com/anthropics/claude-code/issues/20593)

## Quick Start

```bash
# Download
curl -fsSL https://gist.githubusercontent.com/gwpl/cd6dcd899ca0acce1b4a1bc486d56a9e/raw/fix-selected-plugin.py -o claude-plugin-install
chmod +x claude-plugin-install

# Close Claude Code first, then run:
./claude-plugin-install -p PLUGIN_NAME -m MARKETPLACE_NAME
```

## Status

**Work in Progress** - This repo is being developed into a proper CLI tool.

See [archival/](archival/) for the original development context and scripts.

## License

Public domain / CC0
