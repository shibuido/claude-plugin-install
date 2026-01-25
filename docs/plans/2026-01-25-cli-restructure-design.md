# CLI Restructure Design

**Date:** 2026-01-25
**Status:** Approved

## Overview

Restructure the repository to provide a clean, user-friendly CLI tool with proper documentation and tests.

## Key Design Decisions

1. **Single `-p plugin@marketplace` parameter** - Enforces explicit marketplace specification, preventing the exact confusion that causes the upstream bug
2. **Helpful error messages** - Guide users when format is wrong or marketplace unknown
3. **Multiple installation methods** - Direct run, uv run, pip venv

## File Layout

```
claude-plugin-install/
├── claude-plugin-install           # Main script (executable, no ext)
├── claude-plugin-install.README.md # Detailed documentation
├── README.md                       # GitHub welcome page (concise)
├── .gitignore
├── docs/
│   └── plans/                      # Design documents
├── tests/
│   ├── test_claude_plugin_install.py  # Main test suite
│   └── README.md                   # Test documentation
└── archival/                       # Original development context
    ├── CONTEXT.md
    ├── README.md
    ├── docs/
    └── scripts/
        ├── fix-selected-plugin.py
        ├── fix-selected-plugin.README.md
        ├── fix-selected-plugin.test.py
        ├── fix-superpowers-plugin.py
        └── fix-superpowers-plugin.README.md
```

## Script Interface

```bash
./claude-plugin-install -p plugin@marketplace [options]

Options:
  -p, --plugin PLUGIN@MARKETPLACE  Required. Full qualified plugin name
  -s, --scope SCOPE                project-local (default), project-shared, user
  -y, --yes                        Non-interactive mode
  -n, --dry-run                    Preview changes only
  -v, --verbose                    Debug output
  -h, --help                       Show help
```

## Validation & Error Messages

### Missing `@` in plugin argument

```
Error: Invalid plugin format. Expected: plugin@marketplace

You provided: superpowers

Available marketplaces on your system:
  - claude-plugins-official
  - superpowers-marketplace

Example: ./claude-plugin-install -p superpowers@superpowers-marketplace
```

### Unknown marketplace

```
Error: Marketplace 'my-marketplace' not found in your Claude Code configuration.

Available marketplaces:
  - claude-plugins-official
  - superpowers-marketplace

To add a new marketplace in Claude Code:
  /plugin marketplace add owner/my-marketplace

If adding the marketplace also fails and needs a workaround,
please file a feature request: https://github.com/shibuido/claude-plugin-install/issues
```

## README.md (GitHub Welcome Page)

Concise, scannable structure:

1. **Title + one-liner** - What it does
2. **The Problem** - Explain the bug briefly
3. **Upstream issues** - Links with encouragement to add "me too"
4. **Quick Install** - curl one-liner + usage
5. **Safety First** - Bullet points on robustness (backups, validation, dry-run)
6. **Need Help?** - Link to issues
7. **Detailed Documentation** - Link to claude-plugin-install.README.md

## claude-plugin-install.README.md (Detailed Docs)

Comprehensive reference:

1. Overview - Full bug explanation
2. Requirements - Python 3.10+, Claude Code installed
3. Installation methods:
   - Direct run (simplest, stdlib only)
   - uv run (modern, handles deps)
   - pip venv (traditional)
4. Usage - All options with examples
5. Scope options explained
6. How it works - Step-by-step
7. Troubleshooting
8. Related issues
9. Contributing

## Tests

**Location:** `tests/test_claude_plugin_install.py`

**Test cases:**

| Test | Description |
|------|-------------|
| `test_script_help` | Verify --help shows `-p PLUGIN@MARKETPLACE` |
| `test_invalid_format` | Error when missing `@` |
| `test_unknown_marketplace` | Error with guidance for unknown marketplace |
| `test_dry_run` | Dry-run doesn't modify files |
| `test_real_install` | Actual installation works |
| `test_backup_created` | Backup files created |
| `test_claude_verify` | TUI verification (flaky, skippable) |
| `test_idempotent` | Running twice is safe |

Adapted from `archival/scripts/fix-selected-plugin.test.py` with new syntax.

## Implementation Notes

- Fork `claude-plugin-install` from `archival/scripts/fix-selected-plugin.py`
- Modify argument parsing: single `-p` with `@` split instead of `-p`/`-m`
- Add validation for `@` presence and marketplace existence
- Keep PEP 723 shebang for uv compatibility
- Maintain all safety features (backup, validation, confirmation)
