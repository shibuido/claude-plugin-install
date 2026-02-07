# claude-plugin-install - Developer Notes

Internal reference for contributors and debugging.

## Verbosity Levels

The `-v` flag can be stacked for increasing detail:

| Flag | Level | Label | When to use |
|------|-------|-------|-------------|
| (none) | 0 | quiet | Normal operation, only warnings/errors/success |
| `-v` | 1 | INFO | See high-level operation flow |
| `-vv` | 2 | DEBUG | See file paths, cache reads/writes |
| `-vvv` | 3 | TRACE | See full JSON data, every internal step |

All verbose output goes to stderr, so stdout remains clean for piping.

### Example

```bash
$ ./claude-plugin-install -p superpowers@superpowers-marketplace -vvv --dry-run -y 2>&1 | head
TRACE: Cache directory: /home/user/.cache/shibuido/claude-plugin-install
TRACE: Verbosity level: 3
DEBUG: Paths: installed_plugins=/home/user/.claude/plugins/installed_plugins.json, ...
INFO: Plugin: superpowers@superpowers-marketplace
INFO: Project path: /home/user/my-project
INFO: Scope: project-local
INFO: DRY RUN MODE - No changes will be made
```

## Debugging Workflows

### Investigating a failed install

1. **Run with full trace to see what happened:**

   ```bash
   ./claude-plugin-install -p superpowers@superpowers-marketplace -vvv --dry-run -y 2>&1 | tee /tmp/claude-plugin-debug.log
   ```

2. **Check that the marketplace exists:**

   ```bash
   cat ~/.claude/plugins/known_marketplaces.json | python3 -m json.tool
   ```

3. **Check plugin cache directory:**

   ```bash
   ls -la ~/.claude/plugins/cache/superpowers-marketplace/superpowers/
   ```

4. **Check current settings files for the scope:**

   ```bash
   # project-local
   cat .claude/settings.local.json | python3 -m json.tool

   # project-shared
   cat .claude/settings.json | python3 -m json.tool

   # user/global
   cat ~/.claude/settings.json | python3 -m json.tool
   ```

5. **Check installed_plugins.json:**

   ```bash
   cat ~/.claude/plugins/installed_plugins.json | python3 -m json.tool
   ```

6. **Review invocation log for recent errors:**

   ```bash
   ./claude-plugin-install log show --last 5
   ```

### Investigating an uninstall problem

1. **Check which scopes have the plugin:**

   ```bash
   ./claude-plugin-install -vvv 2>&1 | grep -i scope
   ```

2. **Try uninstall with dry-run equivalent (just run interactively and answer no):**

   ```bash
   ./claude-plugin-install uninstall superpowers@superpowers-marketplace -vvv
   ```

## Cache File Locations

Default location:

```
~/.cache/shibuido/claude-plugin-install/
  plugins-cache.jsonl        # one JSON object per line, each plugin remembered
  marketplace-cache.jsonl    # one JSON object per line, each marketplace seen
  invocations.jsonl          # one JSON object per line, each tool invocation
```

Overridden by `XDG_CACHE_HOME`:

```
$XDG_CACHE_HOME/shibuido/claude-plugin-install/
```

### Inspecting cache files manually

```bash
# View plugin memory (pretty-print each line)
while IFS= read -r line; do echo "$line" | python3 -m json.tool --compact; done < ~/.cache/shibuido/claude-plugin-install/plugins-cache.jsonl

# View marketplace memory
while IFS= read -r line; do echo "$line" | python3 -m json.tool --compact; done < ~/.cache/shibuido/claude-plugin-install/marketplace-cache.jsonl

# View recent invocations via the tool
./claude-plugin-install log show --last 5
```

### Plugin cache entry format

```json
{
  "plugin": "superpowers",
  "marketplace": "superpowers-marketplace",
  "key": "superpowers@superpowers-marketplace",
  "first_seen": "2025-07-01T10:30:00",
  "last_used": "2025-07-15T14:22:00",
  "use_count": 5,
  "install_count": 3,
  "invocation_count": 8
}
```

### Invocation log entry format

```json
{
  "timestamp": "2025-07-15T14:22:00",
  "plugin_key": "superpowers@superpowers-marketplace",
  "plugin": "superpowers",
  "marketplace": "superpowers-marketplace",
  "action": "install",
  "repo_git_root": "/home/user/my-project",
  "repo_git_root_resolved": "/home/user/my-project",
  "settings_file": "/home/user/my-project/.claude/settings.local.json",
  "settings_file_resolved": "/home/user/my-project/.claude/settings.local.json",
  "backup_path": "...",
  "scope": "project-local",
  "argv": ["./claude-plugin-install", "-p", "superpowers@superpowers-marketplace"],
  "dry_run": false,
  "interactive_answers": {},
  "success": true,
  "error": null,
  "version": "0.2.0"
}
```

## Auto-trim Internals

The invocation log (`invocations.jsonl`) auto-trims to prevent unbounded growth:

* **Floor:** `LOG_MIN_ENTRIES = 1000` -- the log will never be trimmed below 1000 entries.
* **Trigger:** When the log exceeds `LOG_MIN_ENTRIES * 2 = 2000` lines, it is trimmed back to 1000.
* **Mechanism:** The newest 1000 entries are kept, older ones are discarded.
* **Atomic writes:** Trimming writes to a `.tmp` file first, then uses `os.replace()` for atomic rename. This prevents corruption if the process is interrupted.
* **When it runs:** Auto-trim is checked after every `LogManager.append()` call.

The `log trim` subcommand provides manual control:

* `--keep N` keeps the last N entries regardless of the floor.
* `--days N` removes entries older than N days, but respects the 1000-entry floor (unless `--keep` is also specified).

## Internal Architecture

### Class responsibilities

* **`CacheManager`** -- Manages `plugins-cache.jsonl` and `marketplace-cache.jsonl`. Stateless: all methods are `@staticmethod`. Reads/writes JSONL with atomic `os.replace()`.

* **`LogManager`** -- Manages `invocations.jsonl` with append-only writes and auto-trim. Stateless: all methods are `@staticmethod`.

* **`ScopeDetector`** -- Detects which scopes (project-local, project-shared, user) have a given plugin installed. Reads settings files without modifying them. Also provides `detect_all_installed_plugins()` for the interactive menu.

* **`MenuHandler`** -- Renders the interactive no-args menu. Shows installed plugins (from `ScopeDetector`) and remembered plugins (from `CacheManager`). Handles selection and routes to install/uninstall.

### Key functions

* **`build_invocation_entry()`** -- Constructs the full invocation record dict before logging. Resolves symlinks via `Path.resolve()` for both settings and backup paths.

* **`validate_plugin_arg()`** -- Parses `plugin@marketplace`, checks against known marketplaces, suggests similar names on typos.

* **`get_paths()`** -- Computes all relevant file paths for a given scope/project combination.

* **`verify_assumptions()`** -- Pre-flight check: marketplace exists, plugin cache exists, installed_plugins.json exists.

* **`backup_file()`** -- Creates timestamped backup copy of a file before modification.

### Command routing

```
main()
  |-- args.subcommand == "uninstall" --> cmd_uninstall()
  |-- args.subcommand == "cache"     --> cmd_cache()
  |-- args.subcommand == "log"       --> cmd_log()
  |-- args.plugin is set             --> cmd_install()
  |-- (no args)                      --> cmd_interactive_menu()
```

## JSONL Format Notes

All cache and log files use JSONL (JSON Lines) format:

* One JSON object per line.
* Compact encoding: `separators=(",", ":")` -- no extra whitespace.
* Each line is terminated by `\n`.
* Files are written atomically: data goes to a `.tmp` file first, then `os.replace()` renames it over the original.
* Invalid lines are skipped with a warning during reads (graceful degradation).

## Testing

### Running tests

```bash
./tests/test_claude_plugin_install.py
```

### XDG_CACHE_HOME isolation trick

To avoid polluting your real cache during testing, set `XDG_CACHE_HOME` to a temporary directory:

```bash
export XDG_CACHE_HOME=$(mktemp -d)
./claude-plugin-install -p superpowers@superpowers-marketplace -vvv --dry-run -y
ls -la "$XDG_CACHE_HOME/shibuido/claude-plugin-install/"
```

This creates an isolated cache directory that does not interfere with your normal plugin memory.

### Manual testing workflow

```bash
# 1. Set up isolated cache
export XDG_CACHE_HOME=$(mktemp -d)

# 2. Run a dry-run install to populate cache
./claude-plugin-install -p superpowers@superpowers-marketplace -vvv --dry-run -y

# 3. Check that cache was populated
./claude-plugin-install cache list

# 4. Check invocation log
./claude-plugin-install log show --last 5

# 5. Clean up
rm -rf "$XDG_CACHE_HOME"
unset XDG_CACHE_HOME
```
