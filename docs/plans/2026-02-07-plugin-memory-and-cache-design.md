# Plugin Memory, Caching & Interactive Menu Design

**Date:** 2026-02-07
**Status:** Approved

## Overview

Add "plugin memory" to `claude-plugin-install` — plugins and marketplaces used in the past are cached locally, enabling an interactive menu for quick re-installation, plus full invocation logging for debuggability. Also adds uninstall support and cache/log management subcommands.

## Cache Directory Structure

```
~/.cache/shibuido/claude-plugin-install/
├── plugins-cache.jsonl        # known plugin@marketplace pairs
├── marketplace-cache.jsonl    # known marketplaces
└── invocations.jsonl          # full invocation log
```

Respects `$XDG_CACHE_HOME` if set (defaults to `~/.cache/`). Directory created on first use with `os.makedirs(exist_ok=True)`.

## Cache File Schemas

### plugins-cache.jsonl

One compact JSON object per line. Each line represents a unique plugin@marketplace ever successfully used:

```jsonl
{"plugin":"superpowers","marketplace":"superpowers-marketplace","key":"superpowers@superpowers-marketplace","first_seen":"2026-02-07T14:05:22","last_used":"2026-02-07T14:05:22","use_count":3,"install_count":2,"invocation_count":5}
```

Fields:

* `plugin` — plugin name
* `marketplace` — marketplace name
* `key` — `plugin@marketplace` composite key
* `first_seen` — ISO timestamp of first use
* `last_used` — ISO timestamp of most recent use
* `use_count` — total successful installs (legacy compat)
* `install_count` — successful install count
* `invocation_count` — total invocations (includes dry-runs, failures)

### marketplace-cache.jsonl

```jsonl
{"marketplace":"superpowers-marketplace","first_seen":"2026-02-07T14:05:22","last_used":"2026-02-07T14:05:22"}
```

### invocations.jsonl

Full invocation log, one compact JSON object per line:

```jsonl
{"timestamp":"2026-02-07T14:05:22.123456","plugin_key":"superpowers@superpowers-marketplace","plugin":"superpowers","marketplace":"superpowers-marketplace","action":"install","repo_git_root":"/home/user/myproject","repo_git_root_resolved":"/home/user/myproject","settings_file":".claude/settings.local.json","settings_file_resolved":"/home/user/myproject/.claude/settings.local.json","backup_path":".claude/settings.local.json.bak.2026-02-07--14-05-22","backup_path_resolved":"/home/user/myproject/.claude/settings.local.json.bak.2026-02-07--14-05-22","scope":"project-local","argv":["claude-plugin-install","-p","superpowers@superpowers-marketplace"],"dry_run":false,"interactive_answers":{"confirm_install":true},"success":true,"error":null,"version":"0.2.0"}
```

Key fields:

* `action` — `"install"`, `"uninstall"`, `"menu"`, `"cache-op"`
* Both raw and `readlink -f` resolved paths for repo root, settings file, backup
* `argv` — full CLI arguments
* `interactive_answers` — captures user prompt responses
* `success`/`error` — outcome tracking

## CLI Entry Points

### Scope Shortcuts (used everywhere)

| Flag | Scope |
|------|-------|
| `-l` | project-local (`.claude/settings.local.json`) |
| `-r` | project-shared/repo (`.claude/settings.json`) |
| `-g` | user/global (`~/.claude/settings.json`) |

### Install (existing, enhanced)

```bash
claude-plugin-install -p plugin@marketplace [-l|-g|-r] [-y] [-n] [-v[vv]]
```

Enhanced: writes to plugins-cache, marketplace-cache, and invocations log after operation.

### Interactive Menu (new — no -p flag)

```bash
claude-plugin-install [-d /path/to/repo]
```

Displays:

```
📂 Repo: /home/user/myproject

━━ Installed plugins ━━━━━━━━━━━━━━━━━━━━━━━━━━
  [1] superpowers@superpowers-marketplace  (local ✓, global ✓)
  [2] code-review@claude-plugins-official  (shared ✓)

━━ Remembered plugins (used before) ━━━━━━━━━━━
  [3] linter@superpowers-marketplace        (last: 2d ago, 5 installs)
  [4] formatter@claude-plugins-official     (last: 1w ago, 2 installs)

Select [1-4] or type plugin@marketplace:
```

Selection behaviors:

| Selection | Action |
|-----------|--------|
| Installed plugin (1-2) | Show scopes, offer uninstall or scope change |
| Remembered plugin (3-4) | Run install flow (scope prompt if not provided) |
| Typed `new@marketplace` | Run install flow, added to memory |
| Empty / Ctrl-C | Exit cleanly |

For installed plugin selection:

```
Selected: superpowers@superpowers-marketplace
Currently enabled in:
  [1] project-local  (.claude/settings.local.json)
  [2] user/global    (~/.claude/settings.json)

  [u] Uninstall from selected scope(s)
  [a] Uninstall from all
  [b] Back

Action:
```

### Uninstall (new)

**Interactive (no scope flag):**

```bash
claude-plugin-install uninstall superpowers@superpowers-marketplace
```

1. Auto-detect which scopes have the plugin enabled
2. Display found scopes, let user pick one/multiple/all
3. Backup each settings file before modification
4. Remove `plugin_key` from `enabledPlugins` in selected settings files
5. Remove from `installed_plugins.json` if no scopes remain
6. Log to `invocations.jsonl` with `"action":"uninstall"`
7. Plugin stays in `plugins-cache.jsonl` (memory preserved)

**Non-interactive (scope flag required):**

```bash
claude-plugin-install uninstall superpowers@superpowers-marketplace -l -y
claude-plugin-install uninstall superpowers@superpowers-marketplace --all -y
```

### Cache Management (new)

```bash
claude-plugin-install cache list              # list plugins-cache entries
claude-plugin-install cache list-marketplaces # list marketplace-cache entries
claude-plugin-install cache remove superpowers@superpowers-marketplace
claude-plugin-install cache clear             # wipe both caches
```

### Log Management (new)

```bash
claude-plugin-install log show                # last 10 entries (default)
claude-plugin-install log show --last 50      # last N entries
claude-plugin-install log trim --keep 1000    # trim to last N entries
claude-plugin-install log trim --days 90      # keep last N days (floor: 1000)
```

## Auto-trim Strategy

* On every append to `invocations.jsonl`, check line count
* If exceeds `2 × LOG_MIN_ENTRIES` (2000), trim to `LOG_MIN_ENTRIES` (1000) keeping newest
* File stays bounded between 1000-2000 entries
* Trim is atomic: write to temp file, then `os.replace()` over original
* `--days` flag respects the 1000-entry floor unless `--keep` explicitly overrides

## Verbosity Levels

All output to stderr, stdout stays clean for piping.

| Flags | Level | Prefix | Content |
|-------|-------|--------|---------|
| (none) | ERROR/WARN | `ERROR:`, `WARNING:` | Only problems |
| `-v` | INFO | `INFO:` | Operations performed, files modified |
| `-vv` | DEBUG | `DEBUG:` | Cache reads/writes, path resolution, scope detection |
| `-vvv` | TRACE | `TRACE:` | Full JSON being written, line-by-line JSONL parsing, auto-trim decisions |

## Internal Architecture (Single File)

The script stays as a single file (~1800-2000 lines) for zero-dep `curl`/`uv run` distribution. Organized internally:

```python
# === Constants & Paths ===
CACHE_DIR, PLUGINS_CACHE, MARKETPLACE_CACHE, INVOCATIONS_LOG, LOG_MIN_ENTRIES

# === CacheManager ===
# read/write/update plugins-cache.jsonl and marketplace-cache.jsonl
# update_plugin(key, ...) — upsert, bump counts/last_used
# list_plugins() / list_marketplaces()
# remove_plugin(key) / clear()

# === LogManager ===
# append(entry) — always appends, auto-trims if > 2x floor
# show(last_n) / trim(keep_n, days)

# === ScopeDetector ===
# detect_installed_scopes(plugin_key, repo_path) -> list of scopes
# reads project-local, project-shared, user settings files

# === MenuHandler ===
# interactive_menu(repo_path) — no-args flow
# display installed + known plugins, handle selection

# === Installer (existing, enhanced) ===
# install_plugin(...) — current logic + cache/log writes

# === Uninstaller (new) ===
# uninstall_plugin(plugin_key, scopes, ...) — remove from settings, backup first

# === CLI Entrypoint ===
# argparse with subcommands: (default install), uninstall, cache, log
```

Each manager class is stateless — reads JSONL on demand, writes atomically. No in-memory state between operations.

## Safety

* **Backup first** — same timestamped backup approach as existing install
* **Uninstall does NOT erase memory** — only `cache remove` explicitly forgets
* **Atomic writes** — temp file + `os.replace()` for cache/log mutations
* **Idempotent** — safe to run multiple times

## Documentation Plan

**`claude-plugin-install.README.md`** — update:

* **Plugin Memory** headline feature: "Your plugins are remembered. Install once, select from menu forever."
* **Interactive Mode** — menu flow examples
* **Uninstall** — interactive and non-interactive examples
* **Cache & Log Management** — subcommand reference
* **Scope Shortcuts** — `-l`, `-g`, `-r` quick reference
* **Non-interactive / CI usage** — `-p plugin@marketplace -y`

**`claude-plugin-install.DEV_NOTES.md`** — new:

* Verbosity levels with example `-vvv` output
* Debugging workflows
* Cache file locations, format, manual inspection (`cat`, `jq`)
* Auto-trim internals (thresholds, atomic write)
* Internal architecture and data flow
* Testing new features
* JSONL format notes (compact JSON, one object per line)

**`README.md`** (GitHub front page) — add:

> "Remembers your plugins. Install once, pick from menu next time."
