# Testing Developer Guidelines

## Testing Approach: Containerized End-to-End (E2E) Testing

We use **containerized end-to-end testing** with Docker to validate `claude-plugin-install` behavior in isolated, reproducible environments. Each test runs in an ephemeral Docker container that is automatically deleted after execution.

**Why E2E?** We test the tool the way users use it: as a black box that receives CLI arguments and produces observable effects (files created, JSON modified, output printed). No internal code paths are tested directly.

**Why Docker?** The tool modifies system files (`~/.claude/settings.json`, `~/.claude/plugins/installed_plugins.json`). Docker isolation prevents tests from affecting the developer's actual Claude Code configuration.

## Directory Structure

```
testing/
  Dockerfile              # Shared image for all tests
  run_tests.sh            # Test runner entrypoint
  TESTING_DEVELOPER_GUIDELINES.md  # This file
  .gitignore
  lib/
    assertions.sh         # Shared bash assertion functions
  tests/
    01-help/
      fixture/.gitkeep    # Predefined directory layout (if needed)
      test.sh             # Test script
    02-invalid-format/
      fixture/.gitkeep
      test.sh
    ...
```

## Test Organization

Tests are numbered and ordered from simplest to most complex:

| Range | Category | Description |
|-------|----------|-------------|
| 01-03 | Error handling | Help output, invalid input, unknown marketplace |
| 04 | Dry run | Non-destructive preview mode |
| 05-07 | Install | Local scope, global scope, idempotency |
| 08 | Uninstall | Install then uninstall |
| 09-10 | Subcommands | Cache operations, log operations |
| 11 | Diagnostics | Verbosity levels |
| 12 | Full workflow | Complete user story (install -> cache -> uninstall -> memory) |

**Non-interactive tests come first**, interactive (tmux-based) tests follow.

## Running Tests

```bash
# Run all tests
./testing/run_tests.sh

# Run specific test(s)
./testing/run_tests.sh 01-help 05-install-local

# List available tests
./testing/run_tests.sh list

# Verbose mode (show Docker build output)
./testing/run_tests.sh -v

# Clean up Docker image
./testing/run_tests.sh cleanup
```

The runner automatically builds the Docker image before running tests. Build output is suppressed by default (shown on failure or with `-v`).

## Writing a New Test

### 1. Create the test directory

```bash
mkdir -p testing/tests/NN-descriptive-name/fixture
touch testing/tests/NN-descriptive-name/fixture/.gitkeep
```

### 2. Write test.sh

```bash
#!/usr/bin/env bash
set -euo pipefail

# Test: NN-descriptive-name
# Description: What this test verifies

source /workspace/testing/lib/assertions.sh

SCRIPT="claude-plugin-install"
PLUGIN="superpowers"
MARKETPLACE="superpowers-marketplace"
PLUGIN_KEY="${PLUGIN}@${MARKETPLACE}"
export XDG_CACHE_HOME=/tmp/test-cache-NN

echo "Test: NN-descriptive-name -- Short description"

# Clean state
rm -rf "$XDG_CACHE_HOME"

# Set up test repo
REPO_DIR="/tmp/test-repo-NN"
rm -rf "$REPO_DIR"
mkdir -p "$REPO_DIR"
git init "$REPO_DIR" >/dev/null 2>&1

# Set up Claude plugin infrastructure
mkdir -p ~/.claude/plugins/cache/${MARKETPLACE}/${PLUGIN}/1.0.0
echo '{}' > ~/.claude/plugins/installed_plugins.json
echo "{\"${MARKETPLACE}\": {\"url\": \"https://example.com\"}}" \
    > ~/.claude/plugins/known_marketplaces.json

# ---- YOUR TEST LOGIC ----
OUTPUT=$($SCRIPT -p "$PLUGIN_KEY" -d "$REPO_DIR" -l -y 2>&1) || true

assert_contains "descriptive label" "$OUTPUT" "expected text"
assert_file_exists "file was created" "$REPO_DIR/.claude/settings.local.json"

# ---- END ----
print_summary
```

### 3. Make it executable and test

```bash
chmod +x testing/tests/NN-descriptive-name/test.sh
./testing/run_tests.sh NN-descriptive-name
```

## Available Assertions

All assertions are defined in `testing/lib/assertions.sh` and are safe under `set -euo pipefail`.

| Function | Parameters | Description |
|----------|-----------|-------------|
| `assert_eq` | label, expected, actual | String equality |
| `assert_contains` | label, haystack, needle | Case-insensitive substring match |
| `assert_not_contains` | label, haystack, needle | Substring not present |
| `assert_file_exists` | label, filepath | File exists |
| `assert_file_not_exists` | label, filepath | File does not exist |
| `assert_json_has_key` | label, filepath, key | Key appears in JSON file (string match) |
| `assert_json_not_has_key` | label, filepath, key | Key absent from JSON file |
| `assert_exit_code` | label, expected, actual | Exit code matches |
| `assert_exit_code_not` | label, not_expected, actual | Exit code does not match |
| `print_summary` | (none) | Print pass/fail counts and exit |

**Important:** Always call `print_summary` at the end of every test.sh.

## Key Conventions

* **XDG_CACHE_HOME isolation**: Every test sets `export XDG_CACHE_HOME=/tmp/test-cache-NN` to prevent cache conflicts between tests
* **Fresh repos**: Each test creates its own git repo in `/tmp/test-repo-NN`
* **Plugin infrastructure setup**: Tests that do installs need `~/.claude/plugins/cache/{marketplace}/{plugin}/{version}/` and `known_marketplaces.json`
* **Capture output with `|| true`**: Use `OUTPUT=$($SCRIPT ... 2>&1) || true` to prevent `set -e` from killing the test on non-zero exit
* **Arithmetic with `|| true`**: Bash `((x++))` returns 1 when x=0; always use `((x++)) || true`

## Docker Configuration

* **Image prefix**: `DOCKER_PREFIX` env var (default: `cpi-test`)
* **Base image**: `python:3.10-slim` (matches tool's minimum Python version)
* **Tool invocation**: `python3` wrapper (the tool has a `uv` shebang but zero dependencies)
* **Ephemeral containers**: Every `docker run` uses `--rm` for automatic cleanup

## Fixture Directories

Each test has a `fixture/` subdirectory for predefined file layouts. Currently most tests set up their state programmatically (git init, create JSON files), but fixtures are available for tests that need complex pre-existing directory structures. Place files in `fixture/` and copy them in test.sh:

```bash
cp -r /workspace/testing/tests/NN-test-name/fixture/some-dir /tmp/test-repo-NN/
```
