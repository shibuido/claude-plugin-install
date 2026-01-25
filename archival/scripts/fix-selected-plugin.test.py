#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║           TEST SCRIPT FOR fix-selected-plugin.py                             ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                              ║
║  PURPOSE:                                                                    ║
║  Automated testing for the Claude Code plugin installation fix script.       ║
║  Tests both dry-run and real installation, verifies via Claude Code TUI.     ║
║                                                                              ║
║  FEATURES:                                                                   ║
║  - Parametrized testing (plugin, marketplace, directory)                     ║
║  - tmux integration for TUI verification                                     ║
║  - Selective test execution                                                  ║
║  - Verbose output for debugging                                              ║
║  - Uses existing tmux session or creates isolated test session               ║
║                                                                              ║
║  USAGE:                                                                      ║
║    ./fix-selected-plugin.test.py [OPTIONS] [TEST_NAMES...]                   ║
║                                                                              ║
║  EXAMPLES:                                                                   ║
║    # Run core tests (skip flaky TUI test)                                    ║
║    ./fix-selected-plugin.test.py --skip-tui                                  ║
║                                                                              ║
║    # Run all tests with defaults (creates isolated test session)             ║
║    ./fix-selected-plugin.test.py                                             ║
║                                                                              ║
║    # Run on existing tmux session                                            ║
║    ./fix-selected-plugin.test.py -t claudetmp:1                              ║
║                                                                              ║
║    # Run specific tests only                                                 ║
║    ./fix-selected-plugin.test.py test_dry_run test_real_install              ║
║                                                                              ║
║    # Custom plugin/marketplace                                               ║
║    ./fix-selected-plugin.test.py -p my-plugin -m my-marketplace              ║
║                                                                              ║
║    # Verbose output                                                          ║
║    ./fix-selected-plugin.test.py -v                                          ║
║                                                                              ║
║  TMUX OPTIONS:                                                               ║
║    -t, --tmux-target   Target window (e.g., claudetmp:1, mysession:0)        ║
║                        If not specified, creates isolated test session       ║
║    -S, --socket        tmux socket name (default: test-fix-claude-plugin)    ║
║                        Only used when creating new test session              ║
║                                                                              ║
║  TEST OPTIONS:                                                               ║
║    -p, --plugin        Plugin name to test (default: superpowers)            ║
║    -m, --marketplace   Marketplace name (default: superpowers-marketplace)   ║
║    -d, --directory     Test directory (default: creates temp dir)            ║
║    -v, --verbose       Enable verbose output                                 ║
║    -l, --list          List available tests and exit                         ║
║    --keep-temp         Don't cleanup temp directory after tests              ║
║                                                                              ║
║  AVAILABLE TESTS:                                                            ║
║    test_script_help       - Verify --help works                              ║
║    test_dry_run           - Test dry-run mode                                ║
║    test_real_install      - Test actual installation                         ║
║    test_claude_verify     - Verify plugin in Claude Code TUI (experimental)  ║
║    test_backup_created    - Verify backup files created                      ║
║    test_idempotent        - Test running twice doesn't break                 ║
║                                                                              ║
║  NOTE: test_claude_verify is experimental and may be flaky due to TUI        ║
║  timing issues. Use --skip-tui to skip it.                                   ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
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
from typing import Any, Callable, Optional

# ANSI color codes
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
            # Use existing session
            self.target = target
            # Extract session name from target (e.g., "claudetmp:1" -> "claudetmp")
            self.session = target.split(':')[0]
            self.socket_args = []  # Use default socket for existing sessions
        else:
            # Create isolated test session
            self.session = f"test-plugin-{datetime.now().strftime('%H%M%S')}"
            self.target = f"{self.session}:0"
            self.socket_args = ["-S", f"/tmp/{socket}"]
            self._create_session()

    def get_pane_size(self) -> tuple[int, int]:
        """Get current pane size (width, height)."""
        result = self._run_tmux(["display-message", "-t", self.target, "-p", "#{pane_width} #{pane_height}"], check=False)
        if result.returncode == 0 and result.stdout.strip():
            parts = result.stdout.strip().split()
            if len(parts) == 2:
                return int(parts[0]), int(parts[1])
        return 0, 0

    def ensure_min_size(self) -> bool:
        """Ensure pane meets minimum size requirements for TUI."""
        width, height = self.get_pane_size()
        log_verbose(f"Pane size: {width}x{height}", self.verbose)

        if width < self.MIN_WIDTH or height < self.MIN_HEIGHT:
            log_verbose(f"Pane too small (need {self.MIN_WIDTH}x{self.MIN_HEIGHT}), attempting resize...", self.verbose)
            # Try to resize the pane
            self._run_tmux(["resize-pane", "-t", self.target, "-x", str(self.MIN_WIDTH), "-y", str(self.MIN_HEIGHT)], check=False)
            time.sleep(0.5)
            new_width, new_height = self.get_pane_size()
            log_verbose(f"New pane size: {new_width}x{new_height}", self.verbose)
            return new_width >= self.MIN_WIDTH and new_height >= self.MIN_HEIGHT
        return True

    def _run_tmux(self, args: list[str], check: bool = True) -> subprocess.CompletedProcess:
        cmd = ["tmux"] + self.socket_args + args
        log_verbose(f"Running: {' '.join(cmd)}", self.verbose)
        return subprocess.run(cmd, capture_output=True, text=True, check=check)

    def _create_session(self) -> None:
        """Create isolated test session."""
        log_verbose(f"Creating test session: {self.session}", self.verbose)
        self._run_tmux(["new-session", "-d", "-s", self.session])
        self.owns_session = True
        time.sleep(0.5)

    def send_keys(self, keys: str, enter: bool = True) -> None:
        """Send keys to tmux pane with proper delay."""
        self._run_tmux(["send-keys", "-t", self.target, "C-u"])
        time.sleep(0.2)
        self._run_tmux(["send-keys", "-t", self.target, keys])
        if enter:
            time.sleep(1.5)
            self._run_tmux(["send-keys", "-t", self.target, "C-m"])

    def capture_pane(self) -> str:
        """Capture current pane content."""
        result = self._run_tmux(["capture-pane", "-t", self.target, "-p"], check=False)
        return result.stdout

    def wait_for_prompt(self, timeout: float = 10.0) -> bool:
        """Wait for shell prompt to appear."""
        start = time.time()
        while time.time() - start < timeout:
            content = self.capture_pane()
            if content.strip().endswith('$'):
                return True
            time.sleep(0.5)
        return False

    def wait_for_text(self, text: str, timeout: float = 10.0) -> bool:
        """Wait for specific text to appear in pane."""
        start = time.time()
        while time.time() - start < timeout:
            content = self.capture_pane()
            if text in content:
                return True
            time.sleep(0.5)
        return False

    def cleanup(self) -> None:
        """Cleanup test session if we created it."""
        if self.owns_session:
            log_verbose(f"Killing test session: {self.session}", self.verbose)
            self._run_tmux(["kill-session", "-t", self.session], check=False)


class TestContext:
    """Context for test execution."""

    def __init__(self, args: argparse.Namespace):
        self.plugin = args.plugin
        self.marketplace = args.marketplace
        self.plugin_key = f"{self.plugin}@{self.marketplace}"
        self.verbose = args.verbose
        self.keep_temp = args.keep_temp
        self.tui_retries = getattr(args, 'tui_retries', 3)

        # Script path
        self.script_path = Path(__file__).parent / "fix-selected-plugin.py"
        if not self.script_path.exists():
            raise FileNotFoundError(f"Script not found: {self.script_path}")

        # Test directory
        if args.directory:
            self.test_dir = Path(args.directory).resolve()
            self.owns_test_dir = False
        else:
            self.temp_dir = tempfile.mkdtemp(prefix="test-plugin-fix-")
            self.test_dir = Path(self.temp_dir)
            self.owns_test_dir = True

        # tmux helper
        self.tmux = TmuxHelper(args.tmux_target, args.socket, args.verbose)

        # Results
        self.passed = 0
        self.failed = 0
        self.skipped = 0

    def ensure_shell_ready(self) -> bool:
        """Ensure tmux pane is at shell prompt, clean up if needed."""
        content = self.tmux.capture_pane()

        # If Claude is running, exit it
        if "Claude Code" in content or "Welcome" in content:
            log_verbose("Claude still running, exiting...", self.verbose)
            self.tmux._run_tmux(["send-keys", "-t", self.tmux.target, "C-c"])
            time.sleep(1)
            self.tmux._run_tmux(["send-keys", "-t", self.tmux.target, "/exit"])
            time.sleep(1.5)
            self.tmux._run_tmux(["send-keys", "-t", self.tmux.target, "Enter"])
            time.sleep(2)

        # Send Ctrl-C to cancel any running command
        self.tmux._run_tmux(["send-keys", "-t", self.tmux.target, "C-c"])
        time.sleep(0.5)

        return self.tmux.wait_for_prompt(timeout=5)

    def cleanup(self) -> None:
        """Cleanup resources."""
        self.tmux.cleanup()
        if self.owns_test_dir and not self.keep_temp:
            log_verbose(f"Removing temp dir: {self.test_dir}", self.verbose)
            shutil.rmtree(self.test_dir, ignore_errors=True)


# ============================================================================
# TEST FUNCTIONS
# ============================================================================

def test_script_help(ctx: TestContext) -> bool:
    """Test that --help works."""
    log_test("test_script_help")

    result = subprocess.run(
        [sys.executable, str(ctx.script_path), "--help"],
        capture_output=True, text=True
    )

    if result.returncode != 0:
        log_fail(f"--help returned non-zero: {result.returncode}")
        log_verbose(f"stderr: {result.stderr}", ctx.verbose)
        return False

    if "-p" not in result.stdout or "--plugin" not in result.stdout:
        log_fail("--help missing -p/--plugin documentation")
        return False

    if "-m" not in result.stdout or "--marketplace" not in result.stdout:
        log_fail("--help missing -m/--marketplace documentation")
        return False

    log_success("--help works correctly")
    return True


def test_dry_run(ctx: TestContext) -> bool:
    """Test dry-run mode doesn't modify files."""
    log_test("test_dry_run")

    # Get state before
    installed_plugins = Path.home() / ".claude" / "plugins" / "installed_plugins.json"
    before_mtime = installed_plugins.stat().st_mtime if installed_plugins.exists() else 0

    # Run dry-run
    result = subprocess.run(
        [sys.executable, str(ctx.script_path),
         "-p", ctx.plugin, "-m", ctx.marketplace,
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

    # Verify file not modified
    after_mtime = installed_plugins.stat().st_mtime if installed_plugins.exists() else 0
    if after_mtime != before_mtime:
        log_fail("dry-run modified installed_plugins.json!")
        return False

    # Verify settings not created
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
         "-p", ctx.plugin, "-m", ctx.marketplace,
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

    # Verify settings file created
    settings_file = ctx.test_dir / ".claude" / "settings.local.json"
    if not settings_file.exists():
        log_fail(f"settings file not created: {settings_file}")
        return False

    # Verify settings content
    with open(settings_file) as f:
        settings = json.load(f)

    if ctx.plugin_key not in settings.get("enabledPlugins", {}):
        log_fail(f"plugin not in enabledPlugins: {settings}")
        return False

    # Verify installed_plugins.json updated
    installed_plugins = Path.home() / ".claude" / "plugins" / "installed_plugins.json"
    with open(installed_plugins) as f:
        data = json.load(f)

    if ctx.plugin_key not in data.get("plugins", {}):
        log_fail(f"plugin not in installed_plugins.json")
        return False

    # Check our project is in the list
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

    # Check for recent backup (within last 5 minutes)
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
    """Verify plugin appears in Claude Code TUI (experimental - TUI interaction can be flaky)."""
    log_test("test_claude_verify")

    # Check pane size is adequate for TUI
    if not ctx.tmux.ensure_min_size():
        log_fail(f"Pane too small for TUI test (need {ctx.tmux.MIN_WIDTH}x{ctx.tmux.MIN_HEIGHT})")
        return False

    # First ensure the plugin is installed for this directory
    settings_file = ctx.test_dir / ".claude" / "settings.local.json"
    if not settings_file.exists():
        log_verbose("Plugin not installed for test dir, running installation first...", ctx.verbose)
        result = subprocess.run(
            [sys.executable, str(ctx.script_path),
             "-p", ctx.plugin, "-m", ctx.marketplace,
             "-d", str(ctx.test_dir),
             "-y"],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            log_fail("Could not install plugin for TUI verification")
            log_verbose(f"stderr: {result.stderr}", ctx.verbose)
            return False
        log_verbose("Plugin installed successfully", ctx.verbose)

    tmux = ctx.tmux

    # Change to test directory
    tmux.send_keys(f"cd {ctx.test_dir}")
    time.sleep(2)

    # Start Claude
    log_verbose("Starting Claude Code...", ctx.verbose)
    tmux.send_keys("claude")
    time.sleep(4)

    # Check for trust dialog and handle it
    content = tmux.capture_pane()
    log_verbose(f"Initial screen:\n{content}", ctx.verbose)

    if "trust" in content.lower() or "Yes, proceed" in content:
        log_verbose("Trust dialog detected, pressing Enter to confirm...", ctx.verbose)
        tmux._run_tmux(["send-keys", "-t", tmux.target, "Enter"])
        time.sleep(5)  # Wait for Claude to fully start after trust confirmation
        content = tmux.capture_pane()
        log_verbose(f"After trust confirmation:\n{content}", ctx.verbose)

    # Wait for Claude to be ready (look for the prompt indicator)
    time.sleep(3)
    content = tmux.capture_pane()

    if "Claude Code" not in content and "Welcome" not in content:
        log_fail("Claude Code did not start properly")
        log_verbose(f"Screen content:\n{content}", ctx.verbose)
        # Try to exit
        tmux._run_tmux(["send-keys", "-t", tmux.target, "C-c"])
        time.sleep(1)
        return False

    log_verbose("Claude Code started successfully", ctx.verbose)

    # Open plugin menu - need to type /plugin and press Enter
    log_verbose("Opening /plugin menu...", ctx.verbose)
    # Clear any existing input first
    tmux._run_tmux(["send-keys", "-t", tmux.target, "C-u"])
    time.sleep(0.3)
    # Type /plugin character by character for reliability
    tmux._run_tmux(["send-keys", "-t", tmux.target, "/plugin"])
    time.sleep(1.5)  # Wait for readline
    tmux._run_tmux(["send-keys", "-t", tmux.target, "Enter"])
    time.sleep(5)  # Wait for plugin UI to render

    # Capture plugin menu state
    content = tmux.capture_pane()
    log_verbose(f"After /plugin command:\n{content}", ctx.verbose)

    # Check if plugin menu opened (should show Browse/Installed tabs or plugin list)
    if "Browse" in content or "Installed" in content or "marketplace" in content.lower():
        log_verbose("Plugin menu opened successfully", ctx.verbose)
    else:
        log_verbose("Plugin menu may not have opened, trying again...", ctx.verbose)
        # Try sending /plugin again
        tmux._run_tmux(["send-keys", "-t", tmux.target, "Escape"])
        time.sleep(0.5)
        tmux._run_tmux(["send-keys", "-t", tmux.target, "/plugin"])
        time.sleep(1.5)
        tmux._run_tmux(["send-keys", "-t", tmux.target, "Enter"])
        time.sleep(5)
        content = tmux.capture_pane()
        log_verbose(f"After retry /plugin:\n{content}", ctx.verbose)

    # Navigate to Installed tab - try Tab key first, then Right arrow
    log_verbose("Navigating to Installed tab...", ctx.verbose)
    tmux._run_tmux(["send-keys", "-t", tmux.target, "Tab"])
    time.sleep(2)

    content = tmux.capture_pane()
    log_verbose(f"After Tab:\n{content}", ctx.verbose)

    # If Tab didn't work, try Right arrow
    if "installed" not in content.lower():
        tmux._run_tmux(["send-keys", "-t", tmux.target, "Right"])
        time.sleep(2)
        content = tmux.capture_pane()
        log_verbose(f"After Right:\n{content}", ctx.verbose)

    # Check if plugin is visible, if not try scrolling down
    if ctx.plugin.lower() not in content.lower():
        log_verbose("Plugin not visible, scrolling down...", ctx.verbose)
        for _ in range(5):  # Scroll up to 5 times
            tmux._run_tmux(["send-keys", "-t", tmux.target, "Down"])
            time.sleep(0.5)
            content = tmux.capture_pane()
            if ctx.plugin.lower() in content.lower():
                log_verbose("Found plugin after scrolling", ctx.verbose)
                break
        log_verbose(f"After scrolling:\n{content}", ctx.verbose)

    # Look for indicators that plugin is installed/enabled
    plugin_found = ctx.plugin.lower() in content.lower()
    plugin_key_found = ctx.plugin_key.lower() in content.lower()

    # Check for enabled indicators
    enabled_indicators = ["enabled", "✔", "✓", "installed", "active", "superpowers-marketplace"]
    enabled_found = any(ind.lower() in content.lower() for ind in enabled_indicators)
    on_installed_tab = "installed" in content.lower()

    log_verbose(f"Plugin found: {plugin_found}, Key found: {plugin_key_found}, Enabled: {enabled_found}, On Installed tab: {on_installed_tab}", ctx.verbose)

    # Exit Claude - close dialogs first
    log_verbose("Exiting Claude Code...", ctx.verbose)
    tmux._run_tmux(["send-keys", "-t", tmux.target, "Escape"])
    time.sleep(1)
    tmux._run_tmux(["send-keys", "-t", tmux.target, "Escape"])
    time.sleep(1)

    # Send /exit command
    tmux._run_tmux(["send-keys", "-t", tmux.target, "C-u"])
    time.sleep(0.3)
    tmux._run_tmux(["send-keys", "-t", tmux.target, "/exit"])
    time.sleep(1.5)
    tmux._run_tmux(["send-keys", "-t", tmux.target, "Enter"])
    time.sleep(3)

    # Wait for shell prompt
    if not tmux.wait_for_prompt(timeout=10):
        log_verbose("Warning: didn't see shell prompt, trying Ctrl-C", ctx.verbose)
        tmux._run_tmux(["send-keys", "-t", tmux.target, "C-c"])
        time.sleep(2)

    # Determine success
    if plugin_found or plugin_key_found:
        if enabled_found or on_installed_tab:
            log_success(f"Plugin '{ctx.plugin}' verified in Claude Code TUI")
        else:
            log_success(f"Plugin '{ctx.plugin}' found in TUI (enabled status unclear)")
        return True
    else:
        log_fail(f"Plugin '{ctx.plugin}' not found in TUI")
        log_verbose(f"Searched for: {ctx.plugin} or {ctx.plugin_key}", ctx.verbose)
        return False


def test_idempotent(ctx: TestContext) -> bool:
    """Test that running twice doesn't break anything."""
    log_test("test_idempotent")

    # Run again
    result = subprocess.run(
        [sys.executable, str(ctx.script_path),
         "-p", ctx.plugin, "-m", ctx.marketplace,
         "-d", str(ctx.test_dir),
         "-y"],
        capture_output=True, text=True
    )

    log_verbose(f"stdout:\n{result.stdout}", ctx.verbose)

    # Should either succeed or warn about already installed
    if result.returncode != 0:
        log_fail(f"second run returned non-zero: {result.returncode}")
        return False

    # Verify settings still valid
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


# ============================================================================
# TEST REGISTRY
# ============================================================================

TESTS: dict[str, Callable[[TestContext], bool]] = {
    "test_script_help": test_script_help,
    "test_dry_run": test_dry_run,
    "test_real_install": test_real_install,
    "test_backup_created": test_backup_created,
    "test_claude_verify": test_claude_verify,
    "test_idempotent": test_idempotent,
}

# Tests that are flaky and should be retried
FLAKY_TESTS = {"test_claude_verify"}


def run_with_retries(func: Callable[[TestContext], bool], ctx: TestContext, max_retries: int) -> bool:
    """Run a test with retries for flaky tests."""
    for attempt in range(1, max_retries + 1):
        if attempt > 1:
            log_info(f"Retry {attempt}/{max_retries}...")
            # Ensure clean state before retry
            ctx.ensure_shell_ready()
            time.sleep(1)

        try:
            result = func(ctx)
            if result:
                return True
            # Test failed, will retry if attempts remain
            if attempt < max_retries:
                log_verbose(f"Test failed, will retry ({attempt}/{max_retries})", ctx.verbose)
        except Exception as e:
            log_verbose(f"Test raised exception: {e}", ctx.verbose)
            if attempt >= max_retries:
                raise

    return False

# Default test order
DEFAULT_TEST_ORDER = [
    "test_script_help",
    "test_dry_run",
    "test_real_install",
    "test_backup_created",
    "test_claude_verify",
    "test_idempotent",
]


def list_tests() -> None:
    """Print available tests."""
    print("\nAvailable tests:\n")
    for name in DEFAULT_TEST_ORDER:
        func = TESTS[name]
        doc = func.__doc__ or "No description"
        print(f"  {color(name, Colors.CYAN)}")
        print(f"    {doc.strip()}\n")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Test script for fix-selected-plugin.py",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
EXAMPLES:
  # Run all tests (creates isolated tmux session)
  ./fix-selected-plugin.test.py

  # Run on existing tmux window
  ./fix-selected-plugin.test.py -t claudetmp:1

  # Run specific tests
  ./fix-selected-plugin.test.py test_dry_run test_real_install

  # Verbose output
  ./fix-selected-plugin.test.py -v

  # List available tests
  ./fix-selected-plugin.test.py -l
"""
    )

    parser.add_argument(
        "tests", nargs="*",
        help="Specific tests to run (default: all)"
    )

    parser.add_argument(
        "-p", "--plugin",
        default="superpowers",
        help="Plugin name to test (default: superpowers)"
    )

    parser.add_argument(
        "-m", "--marketplace",
        default="superpowers-marketplace",
        help="Marketplace name (default: superpowers-marketplace)"
    )

    parser.add_argument(
        "-d", "--directory",
        help="Test directory (default: creates temp dir)"
    )

    parser.add_argument(
        "-t", "--tmux-target",
        help="Existing tmux target window (e.g., claudetmp:1)"
    )

    parser.add_argument(
        "-S", "--socket",
        default="test-fix-claude-plugin",
        help="tmux socket name for isolated session (default: test-fix-claude-plugin)"
    )

    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose output"
    )

    parser.add_argument(
        "-l", "--list",
        action="store_true",
        help="List available tests and exit"
    )

    parser.add_argument(
        "--keep-temp",
        action="store_true",
        help="Don't cleanup temp directory after tests"
    )

    parser.add_argument(
        "--skip-tui",
        action="store_true",
        help="Skip TUI verification tests (test_claude_verify is flaky)"
    )

    parser.add_argument(
        "--tui-retries",
        type=int,
        default=3,
        help="Number of retries for flaky TUI tests (default: 3)"
    )

    args = parser.parse_args()

    if args.list:
        list_tests()
        return 0

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

    # Handle --skip-tui flag
    if args.skip_tui and "test_claude_verify" in tests_to_run:
        tests_to_run.remove("test_claude_verify")
        log_info("Skipping TUI tests (--skip-tui)")
        args.skipped_tui = True
    else:
        args.skipped_tui = False

    # Print banner
    print(color("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    fix-selected-plugin.py TEST SUITE                         ║
╚══════════════════════════════════════════════════════════════════════════════╝
""", Colors.CYAN))

    # Create context
    try:
        ctx = TestContext(args)
    except FileNotFoundError as e:
        print(f"{color('ERROR', Colors.RED)}: {e}")
        return 1

    log_info(f"Plugin: {ctx.plugin_key}")
    log_info(f"Test directory: {ctx.test_dir}")
    log_info(f"tmux target: {ctx.tmux.target}")
    log_info(f"Tests to run: {', '.join(tests_to_run)}")

    # Ensure test directory exists and navigate there in tmux
    ctx.test_dir.mkdir(parents=True, exist_ok=True)

    # Run tests
    try:
        for name in tests_to_run:
            func = TESTS[name]
            try:
                # Use retries for flaky tests
                if name in FLAKY_TESTS:
                    retries = ctx.tui_retries
                    log_verbose(f"Flaky test, will retry up to {retries} times", ctx.verbose)
                    result = run_with_retries(func, ctx, retries)
                else:
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

    # Summary
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
