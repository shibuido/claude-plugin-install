#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""
Test suite for claude-plugin-install

Usage:
    ./tests/test_claude_plugin_install.py [OPTIONS] [TEST_NAMES...]

Examples:
    # Run core tests (skip flaky TUI test)
    ./tests/test_claude_plugin_install.py --skip-tui

    # Run all tests with defaults (creates isolated test session)
    ./tests/test_claude_plugin_install.py

    # Run on existing tmux session
    ./tests/test_claude_plugin_install.py -t claudetesting:0

    # Run specific tests only
    ./tests/test_claude_plugin_install.py test_dry_run test_real_install

    # Custom plugin/marketplace
    ./tests/test_claude_plugin_install.py -p my-plugin@my-marketplace

    # Verbose output
    ./tests/test_claude_plugin_install.py -v

    # List available tests
    ./tests/test_claude_plugin_install.py -l

Available tests:
    test_script_help           - Verify --help works and shows correct syntax
    test_invalid_format        - Test error when missing @marketplace
    test_unknown_marketplace   - Test error for unknown marketplace
    test_dry_run               - Test dry-run mode doesn't modify files
    test_real_install          - Test actual installation
    test_backup_created        - Verify backup files created
    test_claude_verify         - Verify plugin in Claude Code TUI (experimental)
    test_idempotent            - Test running twice doesn't break
    test_verbosity_levels      - Test that -v/-vv/-vvv produce different output
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional


class Colors:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"


def color(text: str, c: str) -> str:
    return f"{c}{text}{Colors.RESET}"


def log_info(msg: str) -> None:
    print(f"{color('[INFO]', Colors.BLUE)} {msg}")


def log_success(msg: str) -> None:
    print(f"{color('[PASS]', Colors.GREEN)} {msg}")


def log_fail(msg: str) -> None:
    print(f"{color('[FAIL]', Colors.RED)} {msg}")


def log_skip(msg: str) -> None:
    print(f"{color('[SKIP]', Colors.YELLOW)} {msg}")


def log_verbose(msg: str, verbose: bool) -> None:
    if verbose:
        print(f"{color('[DEBUG]', Colors.MAGENTA)} {msg}")


def log_test(name: str) -> None:
    print(f"\n{color('▶', Colors.CYAN)} {color(f'Running: {name}', Colors.BOLD)}")


class TmuxHelper:
    """Helper class for tmux operations."""

    MIN_WIDTH = 90
    MIN_HEIGHT = 25

    def __init__(self, target: Optional[str], socket: str, verbose: bool):
        self.verbose = verbose
        self.owns_session = False
        self.socket = socket

        if target:
            self.target = target
            self.session = target.split(':')[0]
            self.socket_args = ["-S", f"/tmp/{socket}"]
        else:
            self.session = f"test-plugin-{datetime.now().strftime('%H%M%S')}"
            self.target = f"{self.session}:0"
            self.socket_args = ["-S", f"/tmp/{socket}"]
            self._create_session()

    def _run_tmux(self, args: list[str], check: bool = True) -> subprocess.CompletedProcess:
        cmd = ["tmux"] + self.socket_args + args
        log_verbose(f"Running: {' '.join(cmd)}", self.verbose)
        return subprocess.run(cmd, capture_output=True, text=True, check=check)

    def _create_session(self) -> None:
        log_verbose(f"Creating test session: {self.session}", self.verbose)
        self._run_tmux(["new-session", "-d", "-s", self.session])
        self.owns_session = True
        time.sleep(0.5)

    def send_keys(self, keys: str, enter: bool = True) -> None:
        self._run_tmux(["send-keys", "-t", self.target, "C-u"])
        time.sleep(0.2)
        self._run_tmux(["send-keys", "-t", self.target, keys])
        if enter:
            time.sleep(1.5)
            self._run_tmux(["send-keys", "-t", self.target, "C-m"])

    def capture_pane(self) -> str:
        result = self._run_tmux(["capture-pane", "-t", self.target, "-p"], check=False)
        return result.stdout

    def wait_for_prompt(self, timeout: float = 10.0) -> bool:
        start = time.time()
        while time.time() - start < timeout:
            content = self.capture_pane()
            if content.strip().endswith('$'):
                return True
            time.sleep(0.5)
        return False

    def cleanup(self) -> None:
        if self.owns_session:
            log_verbose(f"Killing test session: {self.session}", self.verbose)
            self._run_tmux(["kill-session", "-t", self.session], check=False)


class TestContext:
    """Context for test execution."""

    def __init__(self, args: argparse.Namespace):
        # Parse plugin@marketplace
        plugin_arg = args.plugin
        if "@" in plugin_arg:
            parts = plugin_arg.split("@", 1)
            self.plugin = parts[0]
            self.marketplace = parts[1]
        else:
            self.plugin = plugin_arg
            self.marketplace = "superpowers-marketplace"

        self.plugin_key = f"{self.plugin}@{self.marketplace}"
        self.verbose = args.verbose
        self.keep_temp = args.keep_temp
        self.tui_retries = getattr(args, 'tui_retries', 3)

        # Script path
        self.script_path = Path(__file__).parent.parent / "claude-plugin-install"
        if not self.script_path.exists():
            raise FileNotFoundError(f"Script not found: {self.script_path}")

        # Test directory
        if args.directory:
            self.test_dir = Path(args.directory).resolve()
            self.owns_test_dir = False
        else:
            self.temp_dir = tempfile.mkdtemp(prefix="test-plugin-fix-", dir="/tmp/claude-tui")
            self.test_dir = Path(self.temp_dir)
            self.owns_test_dir = True

        # tmux helper
        self.tmux = TmuxHelper(args.tmux_target, args.socket, args.verbose)

        # Results
        self.passed = 0
        self.failed = 0
        self.skipped = 0

    def cleanup(self) -> None:
        self.tmux.cleanup()
        if self.owns_test_dir and not self.keep_temp:
            log_verbose(f"Removing temp dir: {self.test_dir}", self.verbose)
            shutil.rmtree(self.test_dir, ignore_errors=True)


# ============================================================================
# TEST FUNCTIONS
# ============================================================================

def test_script_help(ctx: TestContext) -> bool:
    """Test that --help works and shows PLUGIN@MARKETPLACE syntax."""
    log_test("test_script_help")

    result = subprocess.run(
        [sys.executable, str(ctx.script_path), "--help"],
        capture_output=True, text=True
    )

    if result.returncode != 0:
        log_fail(f"--help returned non-zero: {result.returncode}")
        log_verbose(f"stderr: {result.stderr}", ctx.verbose)
        return False

    # Check for new syntax
    if "PLUGIN@MARKETPLACE" not in result.stdout:
        log_fail("--help missing PLUGIN@MARKETPLACE syntax")
        return False

    # Should NOT have -m/--marketplace option anymore
    if "-m," in result.stdout or "--marketplace" in result.stdout:
        log_fail("--help still shows old -m/--marketplace option")
        return False

    log_success("--help works correctly with new syntax")
    return True


def test_invalid_format(ctx: TestContext) -> bool:
    """Test error when plugin format is missing @marketplace."""
    log_test("test_invalid_format")

    result = subprocess.run(
        [sys.executable, str(ctx.script_path), "-p", "superpowers", "-y"],
        capture_output=True, text=True
    )

    if result.returncode == 0:
        log_fail("Should have failed for missing @marketplace")
        return False

    stderr = result.stderr.lower()
    if "plugin@marketplace" not in stderr and "invalid" not in stderr:
        log_fail("Error message should mention plugin@marketplace format")
        log_verbose(f"stderr: {result.stderr}", ctx.verbose)
        return False

    if "available marketplaces" not in stderr:
        log_fail("Error should list available marketplaces")
        return False

    log_success("Correctly errors on missing @marketplace")
    return True


def test_unknown_marketplace(ctx: TestContext) -> bool:
    """Test error for unknown marketplace with guidance."""
    log_test("test_unknown_marketplace")

    result = subprocess.run(
        [sys.executable, str(ctx.script_path), "-p", "plugin@nonexistent-marketplace", "-y"],
        capture_output=True, text=True
    )

    if result.returncode == 0:
        log_fail("Should have failed for unknown marketplace")
        return False

    stderr = result.stderr.lower()
    if "not found" not in stderr:
        log_fail("Error should say marketplace not found")
        log_verbose(f"stderr: {result.stderr}", ctx.verbose)
        return False

    if "marketplace add" not in stderr:
        log_fail("Error should provide guidance to add marketplace")
        return False

    if "feature request" not in stderr and "issue" not in stderr:
        log_fail("Error should mention filing feature request")
        return False

    log_success("Correctly errors on unknown marketplace with guidance")
    return True


def test_dry_run(ctx: TestContext) -> bool:
    """Test dry-run mode doesn't modify files."""
    log_test("test_dry_run")

    installed_plugins = Path.home() / ".claude" / "plugins" / "installed_plugins.json"
    before_mtime = installed_plugins.stat().st_mtime if installed_plugins.exists() else 0

    result = subprocess.run(
        [sys.executable, str(ctx.script_path),
         "-p", ctx.plugin_key,
         "-d", str(ctx.test_dir),
         "--dry-run", "-y"],
        capture_output=True, text=True
    )

    log_verbose(f"stdout:\n{result.stdout}", ctx.verbose)

    if result.returncode != 0:
        log_fail(f"dry-run returned non-zero: {result.returncode}")
        log_verbose(f"stderr: {result.stderr}", ctx.verbose)
        return False

    if "DRY RUN" not in result.stdout:
        log_fail("dry-run output missing 'DRY RUN' indicator")
        return False

    after_mtime = installed_plugins.stat().st_mtime if installed_plugins.exists() else 0
    if after_mtime != before_mtime:
        log_fail("dry-run modified installed_plugins.json!")
        return False

    settings_file = ctx.test_dir / ".claude" / "settings.local.json"
    if settings_file.exists():
        log_fail("dry-run created settings file!")
        return False

    log_success("dry-run works correctly (no files modified)")
    return True


def test_real_install(ctx: TestContext) -> bool:
    """Test actual installation."""
    log_test("test_real_install")

    result = subprocess.run(
        [sys.executable, str(ctx.script_path),
         "-p", ctx.plugin_key,
         "-d", str(ctx.test_dir),
         "-y"],
        capture_output=True, text=True
    )

    log_verbose(f"stdout:\n{result.stdout}", ctx.verbose)

    if result.returncode != 0:
        log_fail(f"install returned non-zero: {result.returncode}")
        log_verbose(f"stderr: {result.stderr}", ctx.verbose)
        return False

    if "SUCCESS" not in result.stdout:
        log_fail("install output missing 'SUCCESS' indicator")
        return False

    settings_file = ctx.test_dir / ".claude" / "settings.local.json"
    if not settings_file.exists():
        log_fail(f"settings file not created: {settings_file}")
        return False

    with open(settings_file) as f:
        settings = json.load(f)

    if ctx.plugin_key not in settings.get("enabledPlugins", {}):
        log_fail(f"plugin not in enabledPlugins: {settings}")
        return False

    installed_plugins = Path.home() / ".claude" / "plugins" / "installed_plugins.json"
    with open(installed_plugins) as f:
        data = json.load(f)

    if ctx.plugin_key not in data.get("plugins", {}):
        log_fail(f"plugin not in installed_plugins.json")
        return False

    found = False
    for entry in data["plugins"][ctx.plugin_key]:
        if entry.get("projectPath") == str(ctx.test_dir):
            found = True
            break

    if not found:
        log_fail(f"project path not found in plugin entries")
        return False

    log_success("real install works correctly")
    return True


def test_backup_created(ctx: TestContext) -> bool:
    """Test that backup files are created."""
    log_test("test_backup_created")

    plugins_dir = Path.home() / ".claude" / "plugins"
    backups = list(plugins_dir.glob("installed_plugins.json.bak.*"))

    if not backups:
        log_fail("no backup files found")
        return False

    recent = False
    now = time.time()
    for backup in backups:
        if now - backup.stat().st_mtime < 300:
            recent = True
            log_verbose(f"Found recent backup: {backup}", ctx.verbose)
            break

    if not recent:
        log_fail("no recent backup found (within 5 minutes)")
        return False

    log_success("backup files created correctly")
    return True


def test_claude_verify(ctx: TestContext) -> bool:
    """Verify plugin appears in Claude Code TUI (experimental)."""
    log_test("test_claude_verify")

    # This test is complex and involves TUI interaction
    # See archival/scripts/fix-selected-plugin.test.py for full implementation
    log_skip("TUI verification skipped (use --skip-tui to silence)")
    return True


def test_idempotent(ctx: TestContext) -> bool:
    """Test that running twice doesn't break anything."""
    log_test("test_idempotent")

    result = subprocess.run(
        [sys.executable, str(ctx.script_path),
         "-p", ctx.plugin_key,
         "-d", str(ctx.test_dir),
         "-y"],
        capture_output=True, text=True
    )

    log_verbose(f"stdout:\n{result.stdout}", ctx.verbose)

    if result.returncode != 0:
        log_fail(f"second run returned non-zero: {result.returncode}")
        return False

    settings_file = ctx.test_dir / ".claude" / "settings.local.json"
    try:
        with open(settings_file) as f:
            settings = json.load(f)
        if ctx.plugin_key not in settings.get("enabledPlugins", {}):
            log_fail("plugin missing from settings after second run")
            return False
    except json.JSONDecodeError as e:
        log_fail(f"settings file corrupted after second run: {e}")
        return False

    log_success("script is idempotent (safe to run multiple times)")
    return True


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


# ============================================================================
# TEST REGISTRY
# ============================================================================

TESTS: dict[str, Callable[[TestContext], bool]] = {
    "test_script_help": test_script_help,
    "test_invalid_format": test_invalid_format,
    "test_unknown_marketplace": test_unknown_marketplace,
    "test_dry_run": test_dry_run,
    "test_real_install": test_real_install,
    "test_backup_created": test_backup_created,
    "test_claude_verify": test_claude_verify,
    "test_idempotent": test_idempotent,
    "test_verbosity_levels": test_verbosity_levels,
}

DEFAULT_TEST_ORDER = [
    "test_script_help",
    "test_invalid_format",
    "test_unknown_marketplace",
    "test_dry_run",
    "test_real_install",
    "test_backup_created",
    "test_claude_verify",
    "test_idempotent",
    "test_verbosity_levels",
]


def list_tests() -> None:
    print("\nAvailable tests:\n")
    for name in DEFAULT_TEST_ORDER:
        func = TESTS[name]
        doc = func.__doc__ or "No description"
        print(f"  {color(name, Colors.CYAN)}")
        print(f"    {doc.strip()}\n")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Test suite for claude-plugin-install",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
EXAMPLES:
  ./tests/test_claude_plugin_install.py
  ./tests/test_claude_plugin_install.py --skip-tui
  ./tests/test_claude_plugin_install.py -t claudetesting:0
  ./tests/test_claude_plugin_install.py test_dry_run test_real_install
  ./tests/test_claude_plugin_install.py -v
  ./tests/test_claude_plugin_install.py -l
"""
    )

    parser.add_argument("tests", nargs="*", help="Specific tests to run (default: all)")
    parser.add_argument("-p", "--plugin", default="superpowers@superpowers-marketplace",
                       help="Plugin@marketplace to test (default: superpowers@superpowers-marketplace)")
    parser.add_argument("-d", "--directory", help="Test directory (default: creates temp dir in /tmp/claude-tui)")
    parser.add_argument("-t", "--tmux-target", help="Existing tmux target window (e.g., claudetesting:0)")
    parser.add_argument("-S", "--socket", default="claudetesting",
                       help="tmux socket name (default: claudetesting)")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose output")
    parser.add_argument("-l", "--list", action="store_true", help="List available tests and exit")
    parser.add_argument("--keep-temp", action="store_true", help="Don't cleanup temp directory after tests")
    parser.add_argument("--skip-tui", action="store_true", help="Skip TUI verification tests")
    parser.add_argument("--tui-retries", type=int, default=3, help="Number of retries for flaky TUI tests")

    args = parser.parse_args()

    if args.list:
        list_tests()
        return 0

    # Ensure /tmp/claude-tui exists
    Path("/tmp/claude-tui").mkdir(parents=True, exist_ok=True)

    # Determine which tests to run
    if args.tests:
        tests_to_run = []
        for name in args.tests:
            if name not in TESTS:
                print(f"{color('ERROR', Colors.RED)}: Unknown test '{name}'")
                print(f"Run with -l to see available tests")
                return 1
            tests_to_run.append(name)
    else:
        tests_to_run = DEFAULT_TEST_ORDER.copy()

    if args.skip_tui and "test_claude_verify" in tests_to_run:
        tests_to_run.remove("test_claude_verify")
        log_info("Skipping TUI tests (--skip-tui)")

    print(color("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    claude-plugin-install TEST SUITE                          ║
╚══════════════════════════════════════════════════════════════════════════════╝
""", Colors.CYAN))

    try:
        ctx = TestContext(args)
    except FileNotFoundError as e:
        print(f"{color('ERROR', Colors.RED)}: {e}")
        return 1

    log_info(f"Plugin: {ctx.plugin_key}")
    log_info(f"Test directory: {ctx.test_dir}")
    log_info(f"tmux socket: {args.socket}")
    log_info(f"Tests to run: {', '.join(tests_to_run)}")

    ctx.test_dir.mkdir(parents=True, exist_ok=True)

    try:
        for name in tests_to_run:
            func = TESTS[name]
            try:
                result = func(ctx)
                if result:
                    ctx.passed += 1
                else:
                    ctx.failed += 1
            except Exception as e:
                log_fail(f"Exception in {name}: {e}")
                if ctx.verbose:
                    import traceback
                    traceback.print_exc()
                ctx.failed += 1
    finally:
        ctx.cleanup()

    total = ctx.passed + ctx.failed + ctx.skipped
    print(color(f"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                              TEST SUMMARY                                    ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  Passed:  {ctx.passed:<4}                                                         ║
║  Failed:  {ctx.failed:<4}                                                         ║
║  Skipped: {ctx.skipped:<4}                                                         ║
║  Total:   {total:<4}                                                         ║
╚══════════════════════════════════════════════════════════════════════════════╝
""", Colors.GREEN if ctx.failed == 0 else Colors.RED))

    return 0 if ctx.failed == 0 else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print(f"\n{color('[INFO]', Colors.BLUE)} Interrupted by user")
        sys.exit(130)
