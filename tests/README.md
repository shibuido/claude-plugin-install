# Tests for claude-plugin-install

## Running Tests

### Quick Start

```bash
# Run all tests (skip TUI test)
./tests/test_claude_plugin_install.py --skip-tui

# List available tests
./tests/test_claude_plugin_install.py -l
```

### Full Test Suite

```bash
# Run all tests including TUI verification
./tests/test_claude_plugin_install.py

# With verbose output
./tests/test_claude_plugin_install.py -v
```

### Specific Tests

```bash
# Run only validation tests
./tests/test_claude_plugin_install.py test_invalid_format test_unknown_marketplace

# Run installation tests
./tests/test_claude_plugin_install.py test_dry_run test_real_install
```

## Test Descriptions

| Test | Description |
|------|-------------|
| `test_script_help` | Verify --help shows correct PLUGIN@MARKETPLACE syntax |
| `test_invalid_format` | Error when missing @marketplace |
| `test_unknown_marketplace` | Error with guidance for unknown marketplace |
| `test_dry_run` | Dry-run mode doesn't modify files |
| `test_real_install` | Actual installation works |
| `test_backup_created` | Backup files are created |
| `test_claude_verify` | Plugin appears in Claude Code TUI (experimental) |
| `test_idempotent` | Running twice is safe |

## tmux Integration

Tests use tmux for TUI verification. By default, tests create an isolated session.

```bash
# Use existing tmux session
./tests/test_claude_plugin_install.py -t claudetesting:0 -S claudetesting

# Skip TUI tests entirely
./tests/test_claude_plugin_install.py --skip-tui
```

## Test Directory

Tests create temporary directories under `/tmp/claude-tui/` for isolation.

```bash
# Keep temp directories for debugging
./tests/test_claude_plugin_install.py --keep-temp

# Use specific directory
./tests/test_claude_plugin_install.py -d /tmp/claude-tui/my-test
```

## Custom Plugin

```bash
# Test with a different plugin
./tests/test_claude_plugin_install.py -p my-plugin@my-marketplace
```
