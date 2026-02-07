# Plugin Memory & Cache Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add plugin memory (caching), invocation logging, interactive menu, uninstall, and cache/log management subcommands to `claude-plugin-install`.

**Architecture:** Single-file Python script (~1800-2000 lines), organized with stateless manager classes (CacheManager, LogManager, ScopeDetector, MenuHandler, Uninstaller). All JSONL files under `~/.cache/shibuido/claude-plugin-install/`. Existing install flow enhanced with cache/log writes. New argparse subcommands for `uninstall`, `cache`, `log`.

**Tech Stack:** Python 3.10+ stdlib only (json, argparse, os, shutil, pathlib, datetime, tempfile, subprocess)

**Design Document:** `docs/plans/2026-02-07-plugin-memory-and-cache-design.md`

---

### Task 1: Multi-level Verbosity System

Replace the current single-level `--verbose` with `-v`/`-vv`/`-vvv` counting.

**Files:**
- Modify: `claude-plugin-install` (lines 25-73, 420-466)

**Step 1: Write the failing test**

Add to `tests/test_claude_plugin_install.py` after the existing test functions (before `TESTS` dict at line 466):

```python
def test_verbosity_levels(ctx: TestContext) -> bool:
    """Test that -v/-vv/-vvv produce different verbosity levels."""
    log_test("test_verbosity_levels")

    # Test -v produces INFO: on stderr
    result = subprocess.run(
        [sys.executable, str(ctx.script_path), "-p", ctx.plugin_key,
         "-d", str(ctx.test_dir), "-v", "--dry-run", "-y"],
        capture_output=True, text=True
    )
    if "INFO:" not in result.stderr:
        log_fail("-v should produce INFO: on stderr")
        log_verbose(f"stderr: {result.stderr}", ctx.verbose)
        return False

    # Test -vvv produces TRACE: on stderr
    result = subprocess.run(
        [sys.executable, str(ctx.script_path), "-p", ctx.plugin_key,
         "-d", str(ctx.test_dir), "-vvv", "--dry-run", "-y"],
        capture_output=True, text=True
    )
    if "TRACE:" not in result.stderr:
        log_fail("-vvv should produce TRACE: on stderr")
        log_verbose(f"stderr: {result.stderr}", ctx.verbose)
        return False

    log_success("verbosity levels work correctly")
    return True
```

Add `"test_verbosity_levels": test_verbosity_levels` to TESTS dict and DEFAULT_TEST_ORDER.

**Step 2: Run test to verify it fails**

Run: `./tests/test_claude_plugin_install.py --skip-tui test_verbosity_levels`
Expected: FAIL (no INFO:/TRACE: on stderr yet)

**Step 3: Implement multi-level verbosity**

In `claude-plugin-install`, replace the verbosity system (lines 50-73 and argparse at line 462-465):

```python
# === Verbosity Levels ===
VERBOSITY = 0  # Module-level, set by CLI

def log_info(msg: str) -> None:
    """INFO level — shown with -v or higher."""
    if VERBOSITY >= 1:
        print(f"INFO: {msg}", file=sys.stderr)

def log_debug(msg: str) -> None:
    """DEBUG level — shown with -vv or higher."""
    if VERBOSITY >= 2:
        print(f"DEBUG: {msg}", file=sys.stderr)

def log_trace(msg: str) -> None:
    """TRACE level — shown with -vvv."""
    if VERBOSITY >= 3:
        print(f"TRACE: {msg}", file=sys.stderr)

def log_warn(msg: str) -> None:
    """Always shown."""
    print(f"WARNING: {msg}", file=sys.stderr)

def log_error(msg: str) -> None:
    """Always shown."""
    print(f"ERROR: {msg}", file=sys.stderr)

def log_step(msg: str) -> None:
    """Progress steps — always shown on stdout."""
    print(f"\n{color('▶', Colors.CYAN)} {color(msg, Colors.BOLD)}")

def log_success(msg: str) -> None:
    """Success messages — always shown on stdout."""
    print(f"{color('[OK]', Colors.GREEN)} {msg}")
```

Update argparse: replace `-v`/`--verbose` with:

```python
parser.add_argument(
    "-v", "--verbose",
    action="count",
    default=0,
    help="Increase verbosity (-v=INFO, -vv=DEBUG, -vvv=TRACE)"
)
```

Replace all `log_verbose(msg, verbose)` calls with appropriate `log_info(msg)`, `log_debug(msg)`, or `log_trace(msg)`. Replace `args.verbose` boolean checks with `VERBOSITY` level checks. Set `VERBOSITY = args.verbose` early in main().

**Step 4: Run test to verify it passes**

Run: `./tests/test_claude_plugin_install.py --skip-tui test_verbosity_levels`
Expected: PASS

**Step 5: Run all existing tests to verify no regression**

Run: `./tests/test_claude_plugin_install.py --skip-tui`
Expected: All PASS

**Step 6: Commit**

```bash
git add claude-plugin-install tests/test_claude_plugin_install.py
git commit -m "feat: Add multi-level verbosity (-v/-vv/-vvv)

* -v = INFO, -vv = DEBUG, -vvv = TRACE
* All verbose output goes to stderr
* Replaces single-level --verbose flag
* Existing tests updated for new verbosity API"
```

---

### Task 2: Constants & Cache Directory Setup

Add cache directory constants and `ensure_cache_dir()`.

**Files:**
- Modify: `claude-plugin-install` (after imports, ~line 33)

**Step 1: Write the failing test**

Add to `tests/test_claude_plugin_install.py`:

```python
def test_cache_dir_created(ctx: TestContext) -> bool:
    """Test that cache directory is created on first use."""
    log_test("test_cache_dir_created")

    # Import the cache dir constant by parsing it from the script
    # Run with --help which should trigger cache dir creation
    result = subprocess.run(
        [sys.executable, str(ctx.script_path), "-p", ctx.plugin_key,
         "-d", str(ctx.test_dir), "--dry-run", "-y"],
        capture_output=True, text=True,
        env={**os.environ, "XDG_CACHE_HOME": str(ctx.test_dir / ".cache")}
    )

    cache_dir = ctx.test_dir / ".cache" / "shibuido" / "claude-plugin-install"
    if not cache_dir.exists():
        log_fail(f"cache dir not created: {cache_dir}")
        return False

    log_success("cache directory created correctly")
    return True
```

Add to TESTS dict and DEFAULT_TEST_ORDER.

**Step 2: Run test to verify it fails**

Run: `./tests/test_claude_plugin_install.py --skip-tui test_cache_dir_created`
Expected: FAIL

**Step 3: Implement constants and cache dir setup**

Add after imports in `claude-plugin-install` (after line 32):

```python
# === Constants & Paths ===
VERSION = "0.2.0"
LOG_MIN_ENTRIES = 1000

def get_cache_dir() -> Path:
    """Get cache directory, respecting XDG_CACHE_HOME."""
    base = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache"))
    return base / "shibuido" / "claude-plugin-install"

def get_cache_paths() -> dict[str, Path]:
    """Get all cache file paths."""
    cache_dir = get_cache_dir()
    return {
        "cache_dir": cache_dir,
        "plugins_cache": cache_dir / "plugins-cache.jsonl",
        "marketplace_cache": cache_dir / "marketplace-cache.jsonl",
        "invocations_log": cache_dir / "invocations.jsonl",
    }

def ensure_cache_dir() -> Path:
    """Create cache directory if it doesn't exist. Returns the path."""
    cache_dir = get_cache_dir()
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir
```

Call `ensure_cache_dir()` early in `main()`, right after parsing args.

**Step 4: Run test to verify it passes**

Run: `./tests/test_claude_plugin_install.py --skip-tui test_cache_dir_created`
Expected: PASS

**Step 5: Commit**

```bash
git add claude-plugin-install tests/test_claude_plugin_install.py
git commit -m "feat: Add cache directory constants and setup

* Cache at ~/.cache/shibuido/claude-plugin-install/
* Respects XDG_CACHE_HOME environment variable
* Created on first invocation
* Paths: plugins-cache.jsonl, marketplace-cache.jsonl, invocations.jsonl"
```

---

### Task 3: CacheManager

Stateless manager for `plugins-cache.jsonl` and `marketplace-cache.jsonl`.

**Files:**
- Modify: `claude-plugin-install` (new class after constants)

**Step 1: Write the failing test**

Add to `tests/test_claude_plugin_install.py`:

```python
def test_cache_plugin_remembered(ctx: TestContext) -> bool:
    """Test that installing a plugin adds it to plugins-cache.jsonl."""
    log_test("test_cache_plugin_remembered")

    test_cache_dir = ctx.test_dir / ".cache" / "shibuido" / "claude-plugin-install"

    result = subprocess.run(
        [sys.executable, str(ctx.script_path), "-p", ctx.plugin_key,
         "-d", str(ctx.test_dir), "-y"],
        capture_output=True, text=True,
        env={**os.environ, "XDG_CACHE_HOME": str(ctx.test_dir / ".cache")}
    )

    if result.returncode != 0:
        log_fail(f"install failed: {result.returncode}")
        log_verbose(f"stderr: {result.stderr}", ctx.verbose)
        return False

    plugins_cache = test_cache_dir / "plugins-cache.jsonl"
    if not plugins_cache.exists():
        log_fail("plugins-cache.jsonl not created")
        return False

    found = False
    with open(plugins_cache) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            entry = json.loads(line)
            if entry.get("key") == ctx.plugin_key:
                found = True
                if entry.get("install_count", 0) < 1:
                    log_fail(f"install_count should be >= 1, got {entry.get('install_count')}")
                    return False
                break

    if not found:
        log_fail(f"plugin {ctx.plugin_key} not found in plugins-cache.jsonl")
        return False

    # Check marketplace-cache too
    marketplace_cache = test_cache_dir / "marketplace-cache.jsonl"
    if not marketplace_cache.exists():
        log_fail("marketplace-cache.jsonl not created")
        return False

    found_mp = False
    with open(marketplace_cache) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            entry = json.loads(line)
            if entry.get("marketplace") == ctx.marketplace:
                found_mp = True
                break

    if not found_mp:
        log_fail(f"marketplace {ctx.marketplace} not found in marketplace-cache.jsonl")
        return False

    log_success("plugin and marketplace remembered in cache")
    return True
```

Add to TESTS dict and DEFAULT_TEST_ORDER (after `test_real_install`).

**Step 2: Run test to verify it fails**

Run: `./tests/test_claude_plugin_install.py --skip-tui test_cache_plugin_remembered`
Expected: FAIL

**Step 3: Implement CacheManager**

Add to `claude-plugin-install` after the constants section:

```python
class CacheManager:
    """Stateless manager for plugins-cache.jsonl and marketplace-cache.jsonl."""

    @staticmethod
    def _read_jsonl(path: Path) -> list[dict]:
        """Read all entries from a JSONL file."""
        if not path.exists():
            return []
        entries = []
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        log_warn(f"Skipping invalid JSON line in {path}")
        log_trace(f"Read {len(entries)} entries from {path}")
        return entries

    @staticmethod
    def _write_jsonl(path: Path, entries: list[dict]) -> None:
        """Atomically write entries to a JSONL file."""
        log_trace(f"Writing {len(entries)} entries to {path}")
        tmp_path = path.with_suffix(".tmp")
        with open(tmp_path, "w") as f:
            for entry in entries:
                f.write(json.dumps(entry, separators=(",", ":")) + "\n")
        os.replace(tmp_path, path)
        log_debug(f"Wrote {path}")

    @staticmethod
    def update_plugin(plugin_name: str, marketplace: str, success: bool) -> None:
        """Upsert a plugin entry in plugins-cache.jsonl."""
        paths = get_cache_paths()
        ensure_cache_dir()
        cache_file = paths["plugins_cache"]
        key = f"{plugin_name}@{marketplace}"
        now = datetime.now().isoformat()

        entries = CacheManager._read_jsonl(cache_file)
        found = False
        for entry in entries:
            if entry.get("key") == key:
                entry["last_used"] = now
                entry["invocation_count"] = entry.get("invocation_count", 0) + 1
                if success:
                    entry["install_count"] = entry.get("install_count", 0) + 1
                    entry["use_count"] = entry.get("use_count", 0) + 1
                found = True
                log_debug(f"Updated plugin cache entry: {key}")
                break

        if not found:
            entries.append({
                "plugin": plugin_name,
                "marketplace": marketplace,
                "key": key,
                "first_seen": now,
                "last_used": now,
                "use_count": 1 if success else 0,
                "install_count": 1 if success else 0,
                "invocation_count": 1,
            })
            log_debug(f"Added new plugin cache entry: {key}")

        CacheManager._write_jsonl(cache_file, entries)

    @staticmethod
    def update_marketplace(marketplace: str) -> None:
        """Upsert a marketplace entry in marketplace-cache.jsonl."""
        paths = get_cache_paths()
        ensure_cache_dir()
        cache_file = paths["marketplace_cache"]
        now = datetime.now().isoformat()

        entries = CacheManager._read_jsonl(cache_file)
        found = False
        for entry in entries:
            if entry.get("marketplace") == marketplace:
                entry["last_used"] = now
                found = True
                break

        if not found:
            entries.append({
                "marketplace": marketplace,
                "first_seen": now,
                "last_used": now,
            })

        CacheManager._write_jsonl(cache_file, entries)

    @staticmethod
    def list_plugins() -> list[dict]:
        """Return all cached plugin entries."""
        return CacheManager._read_jsonl(get_cache_paths()["plugins_cache"])

    @staticmethod
    def list_marketplaces() -> list[dict]:
        """Return all cached marketplace entries."""
        return CacheManager._read_jsonl(get_cache_paths()["marketplace_cache"])

    @staticmethod
    def remove_plugin(key: str) -> bool:
        """Remove a plugin from plugins-cache.jsonl. Returns True if found."""
        paths = get_cache_paths()
        cache_file = paths["plugins_cache"]
        entries = CacheManager._read_jsonl(cache_file)
        before = len(entries)
        entries = [e for e in entries if e.get("key") != key]
        if len(entries) < before:
            CacheManager._write_jsonl(cache_file, entries)
            return True
        return False

    @staticmethod
    def clear() -> None:
        """Clear both cache files."""
        paths = get_cache_paths()
        for key in ("plugins_cache", "marketplace_cache"):
            path = paths[key]
            if path.exists():
                path.unlink()
                log_info(f"Removed {path}")
```

Then integrate into the install flow: after the "SUCCESS" section in `main()` (around line 619), add:

```python
    # === UPDATE CACHE ===
    CacheManager.update_plugin(plugin_name, marketplace, success=True)
    CacheManager.update_marketplace(marketplace)
```

Also add a call for failed/dry-run invocations with `success=False` at appropriate exit points.

**Step 4: Run test to verify it passes**

Run: `./tests/test_claude_plugin_install.py --skip-tui test_cache_plugin_remembered`
Expected: PASS

**Step 5: Run all tests**

Run: `./tests/test_claude_plugin_install.py --skip-tui`
Expected: All PASS

**Step 6: Commit**

```bash
git add claude-plugin-install tests/test_claude_plugin_install.py
git commit -m "feat: Add CacheManager for plugin/marketplace memory

* plugins-cache.jsonl tracks plugin@marketplace with install/invocation counts
* marketplace-cache.jsonl tracks known marketplaces
* Atomic JSONL writes via temp file + os.replace()
* Integrated into install flow — plugins remembered after install"
```

---

### Task 4: LogManager

Stateless manager for `invocations.jsonl` with auto-trim.

**Files:**
- Modify: `claude-plugin-install` (new class after CacheManager)

**Step 1: Write the failing test**

Add to `tests/test_claude_plugin_install.py`:

```python
def test_invocation_logged(ctx: TestContext) -> bool:
    """Test that invocations are logged to invocations.jsonl."""
    log_test("test_invocation_logged")

    test_cache_dir = ctx.test_dir / ".cache" / "shibuido" / "claude-plugin-install"

    result = subprocess.run(
        [sys.executable, str(ctx.script_path), "-p", ctx.plugin_key,
         "-d", str(ctx.test_dir), "-y", "--dry-run"],
        capture_output=True, text=True,
        env={**os.environ, "XDG_CACHE_HOME": str(ctx.test_dir / ".cache")}
    )

    log_file = test_cache_dir / "invocations.jsonl"
    if not log_file.exists():
        log_fail("invocations.jsonl not created")
        return False

    entries = []
    with open(log_file) as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))

    if len(entries) < 1:
        log_fail("no invocation entries found")
        return False

    last = entries[-1]
    required_fields = ["timestamp", "plugin_key", "action", "argv", "success"]
    for field in required_fields:
        if field not in last:
            log_fail(f"missing field '{field}' in invocation entry")
            return False

    if last["plugin_key"] != ctx.plugin_key:
        log_fail(f"plugin_key mismatch: {last['plugin_key']} != {ctx.plugin_key}")
        return False

    if last["dry_run"] is not True:
        log_fail("dry_run should be True for --dry-run invocation")
        return False

    log_success("invocation logged correctly")
    return True


def test_log_auto_trim(ctx: TestContext) -> bool:
    """Test that invocations.jsonl auto-trims when exceeding threshold."""
    log_test("test_log_auto_trim")

    test_cache_dir = ctx.test_dir / ".cache" / "shibuido" / "claude-plugin-install"
    test_cache_dir.mkdir(parents=True, exist_ok=True)
    log_file = test_cache_dir / "invocations.jsonl"

    # Write 2001 fake entries (exceeds 2x LOG_MIN_ENTRIES=1000 threshold)
    with open(log_file, "w") as f:
        for i in range(2001):
            entry = {"timestamp": f"2026-01-{(i%28)+1:02d}T00:00:00", "plugin_key": "test@test",
                     "action": "install", "argv": [], "success": True, "dry_run": False,
                     "seq": i}
            f.write(json.dumps(entry, separators=(",", ":")) + "\n")

    # Run the tool — should trigger auto-trim on append
    result = subprocess.run(
        [sys.executable, str(ctx.script_path), "-p", ctx.plugin_key,
         "-d", str(ctx.test_dir), "-y", "--dry-run"],
        capture_output=True, text=True,
        env={**os.environ, "XDG_CACHE_HOME": str(ctx.test_dir / ".cache")}
    )

    # Count lines after
    with open(log_file) as f:
        lines = [l for l in f if l.strip()]

    # Should be trimmed to ~1001 (1000 kept + 1 new append)
    if len(lines) > 1100:
        log_fail(f"auto-trim failed: {len(lines)} lines (expected ~1001)")
        return False

    if len(lines) < 1000:
        log_fail(f"over-trimmed: {len(lines)} lines (expected >= 1000)")
        return False

    log_success(f"auto-trim works ({len(lines)} lines after trim)")
    return True
```

Add both to TESTS dict and DEFAULT_TEST_ORDER.

**Step 2: Run tests to verify they fail**

Run: `./tests/test_claude_plugin_install.py --skip-tui test_invocation_logged test_log_auto_trim`
Expected: FAIL

**Step 3: Implement LogManager**

Add to `claude-plugin-install` after CacheManager:

```python
class LogManager:
    """Stateless manager for invocations.jsonl with auto-trim."""

    @staticmethod
    def append(entry: dict) -> None:
        """Append an invocation entry and auto-trim if needed."""
        paths = get_cache_paths()
        ensure_cache_dir()
        log_file = paths["invocations_log"]

        line = json.dumps(entry, separators=(",", ":")) + "\n"
        with open(log_file, "a") as f:
            f.write(line)
        log_debug(f"Logged invocation: action={entry.get('action')}")

        # Auto-trim check
        LogManager._auto_trim(log_file)

    @staticmethod
    def _auto_trim(log_file: Path) -> None:
        """Trim log if it exceeds 2x LOG_MIN_ENTRIES."""
        try:
            with open(log_file) as f:
                lines = f.readlines()
        except FileNotFoundError:
            return

        if len(lines) <= LOG_MIN_ENTRIES * 2:
            log_trace(f"Log has {len(lines)} lines, no trim needed (threshold: {LOG_MIN_ENTRIES * 2})")
            return

        log_info(f"Auto-trimming log from {len(lines)} to {LOG_MIN_ENTRIES} entries")
        keep = lines[-LOG_MIN_ENTRIES:]
        tmp_path = log_file.with_suffix(".tmp")
        with open(tmp_path, "w") as f:
            f.writelines(keep)
        os.replace(tmp_path, log_file)

    @staticmethod
    def show(last_n: int = 10) -> list[dict]:
        """Return last N invocation entries."""
        paths = get_cache_paths()
        log_file = paths["invocations_log"]
        if not log_file.exists():
            return []
        entries = []
        with open(log_file) as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
        return entries[-last_n:]

    @staticmethod
    def trim(keep_n: Optional[int] = None, days: Optional[int] = None) -> int:
        """Trim log entries. Returns number of entries removed."""
        paths = get_cache_paths()
        log_file = paths["invocations_log"]
        if not log_file.exists():
            return 0

        with open(log_file) as f:
            lines = f.readlines()

        original_count = len(lines)

        if days is not None:
            cutoff = datetime.now().timestamp() - (days * 86400)
            kept = []
            for line in lines:
                line_s = line.strip()
                if not line_s:
                    continue
                try:
                    entry = json.loads(line_s)
                    ts = datetime.fromisoformat(entry["timestamp"]).timestamp()
                    if ts >= cutoff:
                        kept.append(line)
                except (json.JSONDecodeError, KeyError, ValueError):
                    kept.append(line)  # keep unparseable lines
            # Respect floor unless keep_n explicitly overrides
            if keep_n is None and len(kept) < LOG_MIN_ENTRIES:
                kept = lines[-LOG_MIN_ENTRIES:] if len(lines) >= LOG_MIN_ENTRIES else lines
            lines = kept

        if keep_n is not None:
            lines = lines[-keep_n:] if len(lines) > keep_n else lines

        tmp_path = log_file.with_suffix(".tmp")
        with open(tmp_path, "w") as f:
            f.writelines(lines)
        os.replace(tmp_path, log_file)

        return original_count - len(lines)
```

Integrate into the install flow. Build the invocation entry dict and call `LogManager.append()` at the end of `main()`, for both success and failure paths:

```python
def build_invocation_entry(
    plugin_key: str, plugin_name: str, marketplace: str, action: str,
    args: argparse.Namespace, project_path: Path, paths: dict,
    backup_paths: list, success: bool, error: Optional[str],
    interactive_answers: dict
) -> dict:
    """Build a compact invocation log entry."""
    settings_file = str(paths.get("settings", ""))
    backup_path = str(backup_paths[-1]) if backup_paths else ""

    def resolve(p: str) -> str:
        try:
            return str(Path(p).resolve()) if p else ""
        except (OSError, ValueError):
            return p

    return {
        "timestamp": datetime.now().isoformat(),
        "plugin_key": plugin_key,
        "plugin": plugin_name,
        "marketplace": marketplace,
        "action": action,
        "repo_git_root": str(project_path),
        "repo_git_root_resolved": resolve(str(project_path)),
        "settings_file": settings_file,
        "settings_file_resolved": resolve(settings_file),
        "backup_path": backup_path,
        "backup_path_resolved": resolve(backup_path),
        "scope": args.scope,
        "argv": sys.argv,
        "dry_run": args.dry_run,
        "interactive_answers": interactive_answers,
        "success": success,
        "error": error,
        "version": VERSION,
    }
```

**Step 4: Run tests to verify they pass**

Run: `./tests/test_claude_plugin_install.py --skip-tui test_invocation_logged test_log_auto_trim`
Expected: PASS

**Step 5: Run all tests**

Run: `./tests/test_claude_plugin_install.py --skip-tui`
Expected: All PASS

**Step 6: Commit**

```bash
git add claude-plugin-install tests/test_claude_plugin_install.py
git commit -m "feat: Add LogManager with invocation logging and auto-trim

* Every invocation appended to invocations.jsonl
* Full context: plugin, paths, resolved paths, argv, answers, success
* Auto-trim at 2000 entries → 1000 (atomic write)
* show(last_n) and trim(keep_n, days) for manual management"
```

---

### Task 5: ScopeDetector

Detect which scopes have a plugin installed for a given repo.

**Files:**
- Modify: `claude-plugin-install` (new class after LogManager)

**Step 1: Write the failing test**

Add to `tests/test_claude_plugin_install.py`:

```python
def test_scope_detection(ctx: TestContext) -> bool:
    """Test that scope detection finds installed plugins across scopes."""
    log_test("test_scope_detection")

    # First install the plugin to project-local
    result = subprocess.run(
        [sys.executable, str(ctx.script_path), "-p", ctx.plugin_key,
         "-d", str(ctx.test_dir), "-y"],
        capture_output=True, text=True
    )

    if result.returncode != 0:
        log_fail(f"install failed: {result.returncode}")
        return False

    # Now run with no -p flag — should show interactive menu with scope detection
    # For now, test that the script can be invoked without -p
    result = subprocess.run(
        [sys.executable, str(ctx.script_path),
         "-d", str(ctx.test_dir), "-y"],
        capture_output=True, text=True,
        input="q\n"  # quit the menu
    )

    # Should not crash — returncode 0 means menu was shown
    if result.returncode not in (0, 130):  # 0=normal, 130=ctrl-c
        log_fail(f"interactive mode crashed: {result.returncode}")
        log_verbose(f"stderr: {result.stderr}", ctx.verbose)
        return False

    # Should mention the installed plugin
    output = result.stdout + result.stderr
    if ctx.plugin_key not in output:
        log_fail(f"plugin {ctx.plugin_key} not shown in interactive mode")
        log_verbose(f"output: {output}", ctx.verbose)
        return False

    log_success("scope detection works correctly")
    return True
```

Add to TESTS dict and DEFAULT_TEST_ORDER.

**Step 2: Run test to verify it fails**

Run: `./tests/test_claude_plugin_install.py --skip-tui test_scope_detection`
Expected: FAIL (no-args mode doesn't exist yet)

**Step 3: Implement ScopeDetector**

Add to `claude-plugin-install` after LogManager:

```python
class ScopeDetector:
    """Detect which scopes have a plugin installed."""

    SCOPE_FILES = {
        "project-local": lambda repo: repo / ".claude" / "settings.local.json",
        "project-shared": lambda repo: repo / ".claude" / "settings.json",
        "user": lambda _: Path.home() / ".claude" / "settings.json",
    }

    SCOPE_SHORTCUTS = {
        "project-local": "local",
        "project-shared": "shared",
        "user": "global",
    }

    @staticmethod
    def detect_installed_scopes(plugin_key: str, repo_path: Path) -> list[dict]:
        """Return list of scopes where plugin is enabled.

        Returns: [{"scope": "project-local", "file": Path, "shortcut": "local"}, ...]
        """
        results = []
        for scope, path_fn in ScopeDetector.SCOPE_FILES.items():
            settings_file = path_fn(repo_path)
            if not settings_file.exists():
                log_trace(f"Scope {scope}: file not found ({settings_file})")
                continue
            try:
                with open(settings_file) as f:
                    data = json.load(f)
                if data.get("enabledPlugins", {}).get(plugin_key):
                    results.append({
                        "scope": scope,
                        "file": settings_file,
                        "shortcut": ScopeDetector.SCOPE_SHORTCUTS[scope],
                    })
                    log_debug(f"Scope {scope}: plugin enabled")
                else:
                    log_trace(f"Scope {scope}: plugin not in enabledPlugins")
            except (json.JSONDecodeError, IOError) as e:
                log_warn(f"Could not read {settings_file}: {e}")
        return results

    @staticmethod
    def detect_all_installed_plugins(repo_path: Path) -> dict[str, list[str]]:
        """Return all installed plugins with their scopes.

        Returns: {"plugin@marketplace": ["project-local", "user"], ...}
        """
        plugins: dict[str, list[str]] = {}
        for scope, path_fn in ScopeDetector.SCOPE_FILES.items():
            settings_file = path_fn(repo_path)
            if not settings_file.exists():
                continue
            try:
                with open(settings_file) as f:
                    data = json.load(f)
                for key, enabled in data.get("enabledPlugins", {}).items():
                    if enabled:
                        if key not in plugins:
                            plugins[key] = []
                        plugins[key].append(scope)
            except (json.JSONDecodeError, IOError):
                pass
        return plugins
```

**Step 4: Run test — this one will pass after Task 6 (MenuHandler), skip for now**

**Step 5: Commit**

```bash
git add claude-plugin-install
git commit -m "feat: Add ScopeDetector for cross-scope plugin detection

* Detects which scopes (project-local, project-shared, user) have a plugin enabled
* detect_all_installed_plugins() for menu display
* Scope shortcuts: local, shared, global"
```

---

### Task 6: Argparse Restructure with Subcommands

Restructure CLI to support: default (install or interactive menu), `uninstall`, `cache`, `log`.

**Files:**
- Modify: `claude-plugin-install` (replace `main()` argparse section, lines 420-487)

**Step 1: Write the failing test**

Add to `tests/test_claude_plugin_install.py`:

```python
def test_subcommands_help(ctx: TestContext) -> bool:
    """Test that subcommands show proper help."""
    log_test("test_subcommands_help")

    # cache subcommand
    result = subprocess.run(
        [sys.executable, str(ctx.script_path), "cache", "--help"],
        capture_output=True, text=True
    )
    if result.returncode != 0 or "list" not in result.stdout:
        log_fail("'cache --help' should work and mention 'list'")
        log_verbose(f"stdout: {result.stdout}\nstderr: {result.stderr}", ctx.verbose)
        return False

    # log subcommand
    result = subprocess.run(
        [sys.executable, str(ctx.script_path), "log", "--help"],
        capture_output=True, text=True
    )
    if result.returncode != 0 or "show" not in result.stdout:
        log_fail("'log --help' should work and mention 'show'")
        return False

    # uninstall subcommand
    result = subprocess.run(
        [sys.executable, str(ctx.script_path), "uninstall", "--help"],
        capture_output=True, text=True
    )
    if result.returncode != 0 or "PLUGIN@MARKETPLACE" not in result.stdout:
        log_fail("'uninstall --help' should work and mention PLUGIN@MARKETPLACE")
        return False

    log_success("subcommands have proper help")
    return True
```

Add to TESTS dict and DEFAULT_TEST_ORDER.

**Step 2: Run test to verify it fails**

Run: `./tests/test_claude_plugin_install.py --skip-tui test_subcommands_help`
Expected: FAIL

**Step 3: Implement argparse restructure**

Replace the `main()` function's argparse section with subcommand-based parsing. This is a large refactor. The key structure:

```python
def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser with subcommands."""
    parser = argparse.ArgumentParser(
        description="claude-plugin-install — Install, manage, and remember Claude Code plugins",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
EXAMPLES:
  claude-plugin-install                                    # interactive menu
  claude-plugin-install -p superpowers@superpowers-marketplace  # install
  claude-plugin-install -p superpowers@superpowers-marketplace -y  # non-interactive
  claude-plugin-install uninstall superpowers@superpowers-marketplace
  claude-plugin-install cache list
  claude-plugin-install log show --last 20
"""
    )

    # Global flags
    parser.add_argument("-v", "--verbose", action="count", default=0,
                        help="Increase verbosity (-v=INFO, -vv=DEBUG, -vvv=TRACE)")
    parser.add_argument("-d", "--project-path", type=Path, default=Path.cwd(),
                        help="Project path (default: current directory)")

    # Install flags (for default/no-subcommand mode)
    parser.add_argument("-p", "--plugin", metavar="PLUGIN@MARKETPLACE",
                        help="Plugin to install (e.g., superpowers@superpowers-marketplace)")
    parser.add_argument("-y", "--yes", "--non-interactive", dest="non_interactive",
                        action="store_true", help="Non-interactive mode")
    parser.add_argument("-n", "--dry-run", action="store_true",
                        help="Preview changes only")
    parser.add_argument("-s", "--scope", choices=["project-local", "project-shared", "user"],
                        default="project-local", help="Installation scope")
    parser.add_argument("-l", dest="scope_shortcut", action="store_const",
                        const="project-local", help="Shortcut: project-local scope")
    parser.add_argument("-g", dest="scope_shortcut", action="store_const",
                        const="user", help="Shortcut: user/global scope")
    parser.add_argument("-r", dest="scope_shortcut", action="store_const",
                        const="project-shared", help="Shortcut: project-shared/repo scope")

    subparsers = parser.add_subparsers(dest="subcommand")

    # uninstall subcommand
    unsub = subparsers.add_parser("uninstall", help="Uninstall a plugin")
    unsub.add_argument("plugin", metavar="PLUGIN@MARKETPLACE",
                       help="Plugin to uninstall")
    unsub.add_argument("-l", dest="scope_shortcut", action="store_const",
                       const="project-local", help="Shortcut: project-local scope")
    unsub.add_argument("-g", dest="scope_shortcut", action="store_const",
                       const="user", help="Shortcut: user/global scope")
    unsub.add_argument("-r", dest="scope_shortcut", action="store_const",
                       const="project-shared", help="Shortcut: project-shared/repo scope")
    unsub.add_argument("--all", dest="all_scopes", action="store_true",
                       help="Uninstall from all scopes")
    unsub.add_argument("-y", "--yes", dest="non_interactive", action="store_true",
                       help="Non-interactive mode")

    # cache subcommand
    cachesub = subparsers.add_parser("cache", help="Manage plugin memory cache")
    cache_sub = cachesub.add_subparsers(dest="cache_action")
    cache_sub.add_parser("list", help="List remembered plugins")
    cache_sub.add_parser("list-marketplaces", help="List remembered marketplaces")
    cache_rm = cache_sub.add_parser("remove", help="Forget a plugin")
    cache_rm.add_argument("plugin", metavar="PLUGIN@MARKETPLACE")
    cache_sub.add_parser("clear", help="Clear all plugin memory")

    # log subcommand
    logsub = subparsers.add_parser("log", help="Manage invocation log")
    log_sub = logsub.add_subparsers(dest="log_action")
    log_show = log_sub.add_parser("show", help="Show recent invocations")
    log_show.add_argument("--last", type=int, default=10, help="Number of entries")
    log_trim = log_sub.add_parser("trim", help="Trim log entries")
    log_trim.add_argument("--keep", type=int, help="Keep last N entries")
    log_trim.add_argument("--days", type=int, help="Keep entries from last N days")

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    global VERBOSITY
    VERBOSITY = args.verbose

    # Resolve scope shortcut
    if hasattr(args, "scope_shortcut") and args.scope_shortcut:
        args.scope = args.scope_shortcut

    ensure_cache_dir()

    # Route to subcommand handlers
    if args.subcommand == "uninstall":
        return cmd_uninstall(args)
    elif args.subcommand == "cache":
        return cmd_cache(args)
    elif args.subcommand == "log":
        return cmd_log(args)
    elif args.plugin:
        return cmd_install(args)
    else:
        return cmd_interactive_menu(args)
```

Keep the existing install logic in a new `cmd_install(args)` function (extracted from the old `main()`). Add stub functions for the others:

```python
def cmd_uninstall(args) -> int:
    """Handle uninstall subcommand."""
    log_error("Uninstall not yet implemented")
    return 1

def cmd_cache(args) -> int:
    """Handle cache subcommand."""
    action = getattr(args, "cache_action", None)
    if action == "list":
        entries = CacheManager.list_plugins()
        if not entries:
            print("No remembered plugins.")
            return 0
        for e in entries:
            print(f"  {e['key']}  (installs: {e.get('install_count', 0)}, last: {e.get('last_used', '?')})")
        return 0
    elif action == "list-marketplaces":
        entries = CacheManager.list_marketplaces()
        if not entries:
            print("No remembered marketplaces.")
            return 0
        for e in entries:
            print(f"  {e['marketplace']}  (last: {e.get('last_used', '?')})")
        return 0
    elif action == "remove":
        if CacheManager.remove_plugin(args.plugin):
            log_success(f"Removed {args.plugin} from plugin memory")
        else:
            log_warn(f"{args.plugin} not found in plugin memory")
        return 0
    elif action == "clear":
        CacheManager.clear()
        log_success("Plugin memory cleared")
        return 0
    else:
        print("Usage: claude-plugin-install cache {list|list-marketplaces|remove|clear}")
        return 1

def cmd_log(args) -> int:
    """Handle log subcommand."""
    action = getattr(args, "log_action", None)
    if action == "show":
        entries = LogManager.show(args.last)
        if not entries:
            print("No invocation history.")
            return 0
        for e in entries:
            ts = e.get("timestamp", "?")[:19]
            key = e.get("plugin_key", "?")
            act = e.get("action", "?")
            ok = "✓" if e.get("success") else "✗"
            print(f"  {ts}  {ok} {act:10s} {key}")
        return 0
    elif action == "trim":
        removed = LogManager.trim(keep_n=args.keep, days=args.days)
        log_success(f"Trimmed {removed} entries from invocation log")
        return 0
    else:
        print("Usage: claude-plugin-install log {show|trim}")
        return 1

def cmd_interactive_menu(args) -> int:
    """Handle interactive menu (no-args mode). Stub for now."""
    log_error("Interactive menu not yet implemented")
    return 1
```

**Step 4: Run test to verify it passes**

Run: `./tests/test_claude_plugin_install.py --skip-tui test_subcommands_help`
Expected: PASS

**Step 5: Run all tests — fix any regressions from the argparse refactor**

Run: `./tests/test_claude_plugin_install.py --skip-tui`
Expected: All PASS (existing tests still use `-p` flag which routes to `cmd_install`)

**Step 6: Commit**

```bash
git add claude-plugin-install tests/test_claude_plugin_install.py
git commit -m "feat: Restructure CLI with subcommands (uninstall, cache, log)

* Subcommands: uninstall, cache {list|list-marketplaces|remove|clear}, log {show|trim}
* Scope shortcuts: -l (local), -g (global), -r (repo/shared)
* No -p flag → interactive menu (stub)
* Existing -p install flow preserved in cmd_install()
* cache and log subcommands fully functional"
```

---

### Task 7: Interactive Menu (MenuHandler)

The no-args interactive mode.

**Files:**
- Modify: `claude-plugin-install` (replace `cmd_interactive_menu` stub)

**Step 1: Run the scope detection test from Task 5 to confirm it fails**

Run: `./tests/test_claude_plugin_install.py --skip-tui test_scope_detection`
Expected: FAIL (menu not implemented yet)

**Step 2: Implement MenuHandler and cmd_interactive_menu**

```python
class MenuHandler:
    """Interactive menu for plugin selection."""

    @staticmethod
    def display_menu(repo_path: Path) -> Optional[dict]:
        """Show interactive menu. Returns selection dict or None."""
        print(f"\n{color('📂', Colors.CYAN)} Repo: {color(str(repo_path), Colors.BOLD)}\n")

        # Detect installed plugins
        installed = ScopeDetector.detect_all_installed_plugins(repo_path)

        # Get remembered plugins from cache
        cached = CacheManager.list_plugins()
        cached_keys = {e["key"] for e in cached}

        # Build menu items
        items = []
        idx = 1

        if installed:
            print(color("━━ Installed plugins ━━━━━━━━━━━━━━━━━━━━━━━━━━", Colors.GREEN))
            for key, scopes in sorted(installed.items()):
                scope_str = ", ".join(
                    f"{ScopeDetector.SCOPE_SHORTCUTS.get(s, s)} ✓" for s in scopes
                )
                print(f"  [{idx}] {color(key, Colors.BOLD)}  ({scope_str})")
                items.append({"idx": idx, "key": key, "installed": True, "scopes": scopes})
                idx += 1
            print()

        # Remembered but not installed here
        remembered = [e for e in cached if e["key"] not in installed]
        if remembered:
            print(color("━━ Remembered plugins (used before) ━━━━━━━━━━━", Colors.BLUE))
            for entry in remembered:
                last = entry.get("last_used", "?")[:10]
                count = entry.get("install_count", 0)
                # Calculate relative time
                try:
                    from_dt = datetime.fromisoformat(entry.get("last_used", ""))
                    delta = datetime.now() - from_dt
                    if delta.days == 0:
                        ago = "today"
                    elif delta.days == 1:
                        ago = "1d ago"
                    elif delta.days < 7:
                        ago = f"{delta.days}d ago"
                    elif delta.days < 30:
                        ago = f"{delta.days // 7}w ago"
                    else:
                        ago = f"{delta.days // 30}mo ago"
                except (ValueError, TypeError):
                    ago = "?"
                print(f"  [{idx}] {entry['key']}  (last: {ago}, {count} installs)")
                items.append({"idx": idx, "key": entry["key"], "installed": False})
                idx += 1
            print()

        if not items:
            print("  No installed or remembered plugins.")
            print(f"  Type a plugin@marketplace to install, or 'q' to quit.\n")

        # Prompt
        try:
            choice = input(f"Select [1-{idx-1}] or type plugin@marketplace (q=quit): ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return None

        if not choice or choice.lower() == "q":
            return None

        # Try numeric selection
        try:
            num = int(choice)
            for item in items:
                if item["idx"] == num:
                    return item
            print(f"Invalid selection: {num}")
            return None
        except ValueError:
            pass

        # Try plugin@marketplace input
        if "@" in choice:
            return {"key": choice, "installed": False, "typed": True}

        print(f"Invalid input. Use a number or plugin@marketplace format.")
        return None

    @staticmethod
    def handle_installed_selection(plugin_key: str, scopes: list[str],
                                    repo_path: Path, non_interactive: bool) -> Optional[dict]:
        """Show options for an already-installed plugin."""
        print(f"\n{color('Selected:', Colors.BOLD)} {plugin_key}")
        print("Currently enabled in:")
        for i, scope in enumerate(scopes, 1):
            shortcut = ScopeDetector.SCOPE_SHORTCUTS.get(scope, scope)
            path_fn = ScopeDetector.SCOPE_FILES[scope]
            print(f"  [{i}] {shortcut}  ({path_fn(repo_path)})")

        print(f"\n  [u] Uninstall from selected scope(s)")
        print(f"  [a] Uninstall from all")
        print(f"  [b] Back")

        try:
            action = input(f"\nAction: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            return None

        if action == "b" or not action:
            return None
        elif action == "a":
            return {"action": "uninstall", "plugin_key": plugin_key, "scopes": scopes}
        elif action == "u":
            # Let user pick scopes
            print("Enter scope numbers (comma-separated) to uninstall from:")
            try:
                picks = input("> ").strip()
            except (EOFError, KeyboardInterrupt):
                return None
            selected_scopes = []
            for p in picks.split(","):
                p = p.strip()
                try:
                    idx = int(p) - 1
                    if 0 <= idx < len(scopes):
                        selected_scopes.append(scopes[idx])
                except ValueError:
                    pass
            if selected_scopes:
                return {"action": "uninstall", "plugin_key": plugin_key, "scopes": selected_scopes}
        return None


def cmd_interactive_menu(args) -> int:
    """Handle interactive menu (no-args mode)."""
    project_path = args.project_path.resolve()

    selection = MenuHandler.display_menu(project_path)
    if selection is None:
        return 0

    plugin_key = selection["key"]

    if selection.get("installed"):
        # Show installed plugin options (uninstall, etc.)
        result = MenuHandler.handle_installed_selection(
            plugin_key, selection["scopes"], project_path, args.non_interactive
        )
        if result and result.get("action") == "uninstall":
            # Delegate to uninstall
            args.plugin = plugin_key
            args.all_scopes = len(result["scopes"]) == len(ScopeDetector.SCOPE_FILES)
            args.subcommand = "uninstall"
            if not args.all_scopes:
                # Set specific scope
                args.scope = result["scopes"][0] if len(result["scopes"]) == 1 else None
            return cmd_uninstall(args)
        return 0
    else:
        # Install the selected/typed plugin
        plugin_name, marketplace, error = validate_plugin_arg(plugin_key)
        if error:
            log_error(error)
            return 1
        args.plugin = plugin_key
        return cmd_install(args)
```

**Step 3: Run scope detection test**

Run: `./tests/test_claude_plugin_install.py --skip-tui test_scope_detection`
Expected: PASS

**Step 4: Run all tests**

Run: `./tests/test_claude_plugin_install.py --skip-tui`
Expected: All PASS

**Step 5: Commit**

```bash
git add claude-plugin-install tests/test_claude_plugin_install.py
git commit -m "feat: Add interactive menu mode (no-args invocation)

* Shows installed plugins with scope indicators
* Shows remembered plugins from cache with stats
* Select by number or type plugin@marketplace
* Installed plugin selection offers uninstall options
* Remembered plugin selection triggers install flow"
```

---

### Task 8: Uninstaller

Implement the uninstall flow.

**Files:**
- Modify: `claude-plugin-install` (replace `cmd_uninstall` stub)

**Step 1: Write the failing test**

Add to `tests/test_claude_plugin_install.py`:

```python
def test_uninstall(ctx: TestContext) -> bool:
    """Test that uninstall removes plugin from settings."""
    log_test("test_uninstall")

    # First install
    result = subprocess.run(
        [sys.executable, str(ctx.script_path), "-p", ctx.plugin_key,
         "-d", str(ctx.test_dir), "-y"],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        log_fail(f"install failed: {result.returncode}")
        return False

    # Verify installed
    settings_file = ctx.test_dir / ".claude" / "settings.local.json"
    with open(settings_file) as f:
        data = json.load(f)
    if ctx.plugin_key not in data.get("enabledPlugins", {}):
        log_fail("plugin not installed")
        return False

    # Now uninstall
    result = subprocess.run(
        [sys.executable, str(ctx.script_path), "uninstall", ctx.plugin_key,
         "-l", "-y", "-d", str(ctx.test_dir)],
        capture_output=True, text=True
    )

    if result.returncode != 0:
        log_fail(f"uninstall failed: {result.returncode}")
        log_verbose(f"stderr: {result.stderr}", ctx.verbose)
        return False

    # Verify uninstalled from settings
    with open(settings_file) as f:
        data = json.load(f)
    if ctx.plugin_key in data.get("enabledPlugins", {}):
        log_fail("plugin still in enabledPlugins after uninstall")
        return False

    log_success("uninstall works correctly")
    return True
```

Add to TESTS dict and DEFAULT_TEST_ORDER.

**Step 2: Run test to verify it fails**

Run: `./tests/test_claude_plugin_install.py --skip-tui test_uninstall`
Expected: FAIL

**Step 3: Implement cmd_uninstall**

```python
def cmd_uninstall(args) -> int:
    """Handle uninstall subcommand."""
    plugin_arg = args.plugin
    plugin_name, marketplace, error = validate_plugin_arg(plugin_arg)
    if error:
        log_error(error)
        return 1

    plugin_key = f"{plugin_name}@{marketplace}"
    project_path = args.project_path.resolve()

    # Detect installed scopes
    scopes = ScopeDetector.detect_installed_scopes(plugin_key, project_path)

    if not scopes:
        log_warn(f"{plugin_key} is not installed in any scope for {project_path}")
        return 0

    # Determine which scopes to uninstall from
    if getattr(args, "all_scopes", False):
        target_scopes = scopes
    elif hasattr(args, "scope_shortcut") and args.scope_shortcut:
        target_scopes = [s for s in scopes if s["scope"] == args.scope_shortcut]
        if not target_scopes:
            log_warn(f"{plugin_key} is not installed in scope {args.scope_shortcut}")
            return 0
    elif getattr(args, "non_interactive", False):
        log_error("Non-interactive uninstall requires -l, -g, -r, or --all")
        return 1
    else:
        # Interactive: show scopes and ask
        print(f"\n{color('Uninstall:', Colors.BOLD)} {plugin_key}")
        print("Found in scopes:")
        for i, s in enumerate(scopes, 1):
            print(f"  [{i}] {s['shortcut']}  ({s['file']})")
        print(f"  [a] All scopes")

        try:
            choice = input(f"\nUninstall from (numbers/a): ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0

        if choice == "a":
            target_scopes = scopes
        else:
            target_scopes = []
            for c in choice.split(","):
                c = c.strip()
                try:
                    idx = int(c) - 1
                    if 0 <= idx < len(scopes):
                        target_scopes.append(scopes[idx])
                except ValueError:
                    pass

        if not target_scopes:
            log_info("No scopes selected, exiting.")
            return 0

    # Perform uninstall
    interactive_answers = {}
    backup_paths = []

    for scope_info in target_scopes:
        settings_file = scope_info["file"]
        log_info(f"Removing {plugin_key} from {scope_info['shortcut']} ({settings_file})")

        # Backup
        backup = backup_file(settings_file, VERBOSITY >= 1)
        if backup:
            backup_paths.append(backup)

        # Remove from enabledPlugins
        try:
            with open(settings_file) as f:
                data = json.load(f)
            if plugin_key in data.get("enabledPlugins", {}):
                del data["enabledPlugins"][plugin_key]
                with open(settings_file, "w") as f:
                    json.dump(data, f, indent=2)
                    f.write("\n")
                log_success(f"Removed from {scope_info['shortcut']}")
            else:
                log_warn(f"Not found in {scope_info['shortcut']} (already removed?)")
        except (json.JSONDecodeError, IOError) as e:
            log_error(f"Failed to update {settings_file}: {e}")
            return 1

    # Remove from installed_plugins.json if no scopes remain
    remaining = ScopeDetector.detect_installed_scopes(plugin_key, project_path)
    if not remaining:
        installed_plugins = Path.home() / ".claude" / "plugins" / "installed_plugins.json"
        if installed_plugins.exists():
            try:
                backup = backup_file(installed_plugins, VERBOSITY >= 1)
                if backup:
                    backup_paths.append(backup)
                with open(installed_plugins) as f:
                    data = json.load(f)
                if plugin_key in data.get("plugins", {}):
                    # Remove entries for this project
                    entries = data["plugins"][plugin_key]
                    entries = [e for e in entries if e.get("projectPath") != str(project_path)]
                    if entries:
                        data["plugins"][plugin_key] = entries
                    else:
                        del data["plugins"][plugin_key]
                    with open(installed_plugins, "w") as f:
                        json.dump(data, f, indent=2)
                    log_success("Cleaned up installed_plugins.json")
            except (json.JSONDecodeError, IOError) as e:
                log_warn(f"Could not clean installed_plugins.json: {e}")

    # Log invocation
    log_entry = build_invocation_entry(
        plugin_key=plugin_key, plugin_name=plugin_name, marketplace=marketplace,
        action="uninstall", args=args, project_path=project_path,
        paths={"settings": target_scopes[0]["file"] if target_scopes else ""},
        backup_paths=backup_paths, success=True, error=None,
        interactive_answers=interactive_answers,
    )
    LogManager.append(log_entry)
    CacheManager.update_plugin(plugin_name, marketplace, success=False)  # invocation but not install

    print(color(f"\n✓ Uninstalled {plugin_key}", Colors.GREEN))
    return 0
```

**Step 4: Run test to verify it passes**

Run: `./tests/test_claude_plugin_install.py --skip-tui test_uninstall`
Expected: PASS

**Step 5: Run all tests**

Run: `./tests/test_claude_plugin_install.py --skip-tui`
Expected: All PASS

**Step 6: Commit**

```bash
git add claude-plugin-install tests/test_claude_plugin_install.py
git commit -m "feat: Add uninstall command with scope detection

* Interactive: auto-detects scopes, user picks which to remove
* Non-interactive: requires -l/-g/-r/--all flag
* Backups created before modification
* Cleans installed_plugins.json when no scopes remain
* Plugin stays in memory cache (only cache remove forgets)"
```

---

### Task 9: Documentation Update

Update README.md, claude-plugin-install.README.md, create DEV_NOTES.md.

**Files:**
- Modify: `README.md`
- Modify: `claude-plugin-install.README.md`
- Create: `claude-plugin-install.DEV_NOTES.md`

**Step 1: Update README.md**

Add "Plugin Memory" tagline and updated usage:

```markdown
# claude-plugin-install

Fix Claude Code's plugin installation bug with one command. **Remembers your plugins — install once, pick from menu next time.**
```

Add interactive mode to Quick Install section:

```markdown
## Interactive Mode

Run without arguments to see installed and remembered plugins:

```bash
./claude-plugin-install
```

## Uninstall

```bash
./claude-plugin-install uninstall superpowers@superpowers-marketplace
```
```

Update Usage section with scope shortcuts and subcommands.

**Step 2: Update claude-plugin-install.README.md**

Add new sections:

* **Plugin Memory** — how caching works, where files are stored
* **Interactive Mode** — menu flow with example output
* **Uninstall** — interactive and non-interactive examples
* **Scope Shortcuts** — `-l`, `-g`, `-r` table
* **Cache Management** — `cache list`, `cache remove`, `cache clear`
* **Log Management** — `log show`, `log trim`
* **Non-interactive / CI Usage** — `-p plugin@marketplace -y`

**Step 3: Create claude-plugin-install.DEV_NOTES.md**

Contents:

* **Verbosity Levels** — `-v`/`-vv`/`-vvv` with example output snippets
* **Debugging Workflows** — how to investigate a failed install using `-vvv` and `log show`
* **Cache File Locations** — paths, format, manual inspection:
  ```bash
  cat ~/.cache/shibuido/claude-plugin-install/plugins-cache.jsonl | jq .
  ```
* **Auto-trim Internals** — thresholds (1000/2000), atomic write via `os.replace()`
* **Internal Architecture** — class responsibilities (CacheManager, LogManager, ScopeDetector, MenuHandler)
* **JSONL Format Notes** — compact JSON, one object per line, `separators=(",",":")`
* **Testing** — how to run tests, how to test with custom XDG_CACHE_HOME

**Step 4: Commit**

```bash
git add README.md claude-plugin-install.README.md claude-plugin-install.DEV_NOTES.md
git commit -m "docs: Update documentation for plugin memory features

* README.md: Add plugin memory tagline, interactive mode, uninstall
* claude-plugin-install.README.md: Full reference for all new features
* claude-plugin-install.DEV_NOTES.md: Verbosity, debugging, internals"
```

---

### Task 10: Final Integration Test & Cleanup

End-to-end test of the full workflow.

**Files:**
- Modify: `tests/test_claude_plugin_install.py`

**Step 1: Write integration test**

```python
def test_full_workflow(ctx: TestContext) -> bool:
    """End-to-end: install → cache check → uninstall → cache still has memory."""
    log_test("test_full_workflow")

    env = {**os.environ, "XDG_CACHE_HOME": str(ctx.test_dir / ".cache")}
    test_cache_dir = ctx.test_dir / ".cache" / "shibuido" / "claude-plugin-install"

    # 1. Install
    result = subprocess.run(
        [sys.executable, str(ctx.script_path), "-p", ctx.plugin_key,
         "-d", str(ctx.test_dir), "-y"],
        capture_output=True, text=True, env=env
    )
    if result.returncode != 0:
        log_fail(f"install failed: {result.returncode}")
        return False

    # 2. Check cache has the plugin
    result = subprocess.run(
        [sys.executable, str(ctx.script_path), "cache", "list"],
        capture_output=True, text=True, env=env
    )
    if ctx.plugin_key not in result.stdout:
        log_fail("plugin not in cache list after install")
        return False

    # 3. Check log has entry
    result = subprocess.run(
        [sys.executable, str(ctx.script_path), "log", "show", "--last", "1"],
        capture_output=True, text=True, env=env
    )
    if ctx.plugin_key not in result.stdout:
        log_fail("plugin not in log after install")
        return False

    # 4. Uninstall
    result = subprocess.run(
        [sys.executable, str(ctx.script_path), "uninstall", ctx.plugin_key,
         "-l", "-y", "-d", str(ctx.test_dir)],
        capture_output=True, text=True, env=env
    )
    if result.returncode != 0:
        log_fail(f"uninstall failed: {result.returncode}")
        return False

    # 5. Plugin should still be in cache (memory preserved)
    result = subprocess.run(
        [sys.executable, str(ctx.script_path), "cache", "list"],
        capture_output=True, text=True, env=env
    )
    if ctx.plugin_key not in result.stdout:
        log_fail("plugin should still be in cache after uninstall")
        return False

    # 6. Verify settings file no longer has plugin
    settings_file = ctx.test_dir / ".claude" / "settings.local.json"
    if settings_file.exists():
        with open(settings_file) as f:
            data = json.load(f)
        if ctx.plugin_key in data.get("enabledPlugins", {}):
            log_fail("plugin still in settings after uninstall")
            return False

    log_success("full workflow (install → cache → uninstall → memory preserved)")
    return True
```

Add to TESTS dict and DEFAULT_TEST_ORDER (at the end).

**Step 2: Run full test suite**

Run: `./tests/test_claude_plugin_install.py --skip-tui`
Expected: All PASS

**Step 3: Commit**

```bash
git add tests/test_claude_plugin_install.py
git commit -m "test: Add full workflow integration test

* install → cache check → log check → uninstall → memory preserved
* Tests XDG_CACHE_HOME isolation
* Verifies plugin memory survives uninstall"
```

---

## Summary of Tasks

| Task | Component | Description |
|------|-----------|-------------|
| 1 | Verbosity | Multi-level `-v`/`-vv`/`-vvv` |
| 2 | Constants | Cache dir setup, `XDG_CACHE_HOME` |
| 3 | CacheManager | Plugin/marketplace JSONL caching |
| 4 | LogManager | Invocation logging with auto-trim |
| 5 | ScopeDetector | Cross-scope plugin detection |
| 6 | CLI Restructure | Subcommands: uninstall, cache, log |
| 7 | MenuHandler | Interactive no-args menu |
| 8 | Uninstaller | Scope-aware uninstall flow |
| 9 | Documentation | README, detailed docs, DEV_NOTES |
| 10 | Integration | Full workflow end-to-end test |
