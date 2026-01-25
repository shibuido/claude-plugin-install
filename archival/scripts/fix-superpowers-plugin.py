#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║           CLAUDE CODE SUPERPOWERS PLUGIN INSTALLATION FIX                    ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                              ║
║  PURPOSE:                                                                    ║
║  Workaround for Claude Code plugin installation bug where plugins with       ║
║  the same name in different marketplaces cause installation failures.        ║
║                                                                              ║
║  THE BUG:                                                                    ║
║  When "superpowers" exists in BOTH claude-plugins-official AND               ║
║  superpowers-marketplace, the install command matches on plugin name only,   ║
║  ignoring the marketplace qualifier. This causes:                            ║
║    - Wrong marketplace in error messages                                     ║
║    - "Already installed" errors for different plugins                        ║
║    - Flaky per-repository installation                                       ║
║                                                                              ║
║  SAFETY DESIGN PRINCIPLES:                                                   ║
║  1. BACKUP FIRST: All files are backed up before any modifications           ║
║  2. VERIFY ASSUMPTIONS: Script checks file structure before proceeding       ║
║  3. INTERACTIVE BY DEFAULT: Asks for confirmation at each step               ║
║  4. VERBOSE LOGGING: Full visibility into what's happening                   ║
║  5. FAIL-SAFE: On any error, provides debug info for issue reporting         ║
║  6. NO DESTRUCTIVE OPS: Only adds entries, never removes existing ones       ║
║                                                                              ║
║  RELATED ISSUES:                                                             ║
║  - https://github.com/anthropics/claude-code/issues/20593                    ║
║    (Bug: wrong marketplace matching)                                         ║
║  - https://github.com/anthropics/claude-code/issues/14202                    ║
║    (Bug: projectPath scope issues)                                           ║
║  - https://github.com/obra/superpowers-marketplace/issues/11                 ║
║    (Tracking: workaround & info)                                             ║
║  - https://github.com/obra/superpowers/issues/355                            ║
║    (Pointer: visibility for users)                                           ║
║                                                                              ║
║  USAGE:                                                                       ║
║    ./fix-superpowers-plugin.py [OPTIONS]                                     ║
║    uv run fix-superpowers-plugin.py [OPTIONS]                                ║
║                                                                              ║
║  Run from the project directory where you want to install superpowers.       ║
║                                                                              ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                              ║
║  WHAT THIS SCRIPT DOES:                                                      ║
║                                                                              ║
║  1. MODIFIES: ~/.claude/plugins/installed_plugins.json                       ║
║     - Adds new entry to "superpowers@superpowers-marketplace" array:         ║
║       {                                                                      ║
║         "scope": "local",           // or "user" for global                  ║
║         "projectPath": "/your/project/path",                                 ║
║         "installPath": "~/.claude/plugins/cache/superpowers-marketplace/...",║
║         "version": "4.x.x",                                                  ║
║         "installedAt": "ISO8601_TIMESTAMP",                                  ║
║         "lastUpdated": "ISO8601_TIMESTAMP"                                   ║
║       }                                                                      ║
║                                                                              ║
║  2. CREATES/MODIFIES: Project settings file (depends on --scope):            ║
║     - project-local:  .claude/settings.local.json  (default, gitignored)     ║
║     - project-shared: .claude/settings.json        (committed to git)        ║
║     - user:           ~/.claude/settings.json      (global)                  ║
║                                                                              ║
║     Adds to settings:                                                        ║
║       {                                                                      ║
║         "enabledPlugins": {                                                  ║
║           "superpowers@superpowers-marketplace": true                        ║
║         }                                                                    ║
║       }                                                                      ║
║                                                                              ║
║  PREREQUISITES (verified by script):                                         ║
║  - superpowers-marketplace registered in ~/.claude/plugins/known_marketplaces║
║  - Plugin cache exists at ~/.claude/plugins/cache/superpowers-marketplace/   ║
║                                                                              ║
║  If prerequisites missing, run first:                                        ║
║    /plugin marketplace add obra/superpowers-marketplace                      ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import argparse
import json
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

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
    """Wrap text in color codes."""
    return f"{c}{text}{Colors.RESET}"

def log_info(msg: str) -> None:
    print(f"{color('[INFO]', Colors.BLUE)} {msg}")

def log_success(msg: str) -> None:
    print(f"{color('[OK]', Colors.GREEN)} {msg}")

def log_warn(msg: str) -> None:
    print(f"{color('[WARN]', Colors.YELLOW)} {msg}")

def log_error(msg: str) -> None:
    print(f"{color('[ERROR]', Colors.RED)} {msg}", file=sys.stderr)

def log_step(msg: str) -> None:
    print(f"\n{color('▶', Colors.CYAN)} {color(msg, Colors.BOLD)}")

def log_verbose(msg: str, verbose: bool) -> None:
    if verbose:
        print(f"{color('[DEBUG]', Colors.MAGENTA)} {msg}")

def print_banner() -> None:
    """Print script banner."""
    print(color("""
╔══════════════════════════════════════════════════════════════════════════════╗
║        CLAUDE CODE SUPERPOWERS PLUGIN INSTALLATION FIX                       ║
║                                                                              ║
║  This script applies a workaround for the plugin name collision bug.         ║
║  All files will be backed up before modification.                            ║
╚══════════════════════════════════════════════════════════════════════════════╝
""", Colors.CYAN))

def print_debug_info(error_context: str, locals_snapshot: dict[str, Any]) -> None:
    """Print debug information for issue reporting."""
    print(color("""
╔══════════════════════════════════════════════════════════════════════════════╗
║  DEBUG INFORMATION - Please include this when reporting issues               ║
╚══════════════════════════════════════════════════════════════════════════════╝
""", Colors.RED))

    debug_info = {
        "timestamp": datetime.now().isoformat(),
        "python_version": sys.version,
        "platform": sys.platform,
        "cwd": os.getcwd(),
        "error_context": error_context,
        "home": str(Path.home()),
        "relevant_state": {k: str(v) for k, v in locals_snapshot.items() if not k.startswith('_')}
    }

    print("```json")
    print(json.dumps(debug_info, indent=2))
    print("```")
    print(f"\n{color('Please report at:', Colors.YELLOW)} https://github.com/obra/superpowers-marketplace/issues/11")

def ask_confirmation(prompt: str, non_interactive: bool) -> bool:
    """Ask user for confirmation unless in non-interactive mode."""
    if non_interactive:
        log_info(f"Non-interactive mode: auto-confirming '{prompt}'")
        return True

    response = input(f"\n{color('?', Colors.YELLOW)} {prompt} [y/N]: ").strip().lower()
    return response in ('y', 'yes')

def backup_file(filepath: Path, verbose: bool) -> Optional[Path]:
    """Create a backup of a file with ISO8601 timestamp."""
    if not filepath.exists():
        log_verbose(f"File does not exist, no backup needed: {filepath}", verbose)
        return None

    timestamp = datetime.now().strftime("%Y-%m-%d--%H-%M-%S")
    backup_path = filepath.with_suffix(f"{filepath.suffix}.bak.{timestamp}")

    log_verbose(f"Creating backup: {filepath} -> {backup_path}", verbose)
    shutil.copy2(filepath, backup_path)
    log_success(f"Backed up: {backup_path}")
    return backup_path

def get_paths(scope: str, project_path: Path) -> dict[str, Path]:
    """Get relevant file paths based on scope."""
    home = Path.home()
    claude_home = home / ".claude"

    paths = {
        "installed_plugins": claude_home / "plugins" / "installed_plugins.json",
        "known_marketplaces": claude_home / "plugins" / "known_marketplaces.json",
        "plugin_cache_superpowers": claude_home / "plugins" / "cache" / "superpowers-marketplace" / "superpowers",
    }

    # Settings file location depends on scope
    if scope == "user":
        paths["settings"] = claude_home / "settings.json"
    elif scope == "project-shared":
        paths["settings"] = project_path / ".claude" / "settings.json"
    else:  # project-local (default)
        paths["settings"] = project_path / ".claude" / "settings.local.json"

    paths["project_claude_dir"] = project_path / ".claude"

    return paths

def verify_assumptions(paths: dict[str, Path], verbose: bool) -> tuple[bool, list[str]]:
    """Verify all assumptions about file structure. Returns (success, errors)."""
    errors = []

    log_step("Verifying assumptions...")

    # Check installed_plugins.json exists
    if not paths["installed_plugins"].exists():
        errors.append(f"installed_plugins.json not found at: {paths['installed_plugins']}")
    else:
        log_success(f"Found installed_plugins.json")
        log_verbose(f"  Path: {paths['installed_plugins']}", verbose)

    # Check known_marketplaces.json exists
    if not paths["known_marketplaces"].exists():
        errors.append(f"known_marketplaces.json not found at: {paths['known_marketplaces']}")
    else:
        log_success(f"Found known_marketplaces.json")

        # Verify superpowers-marketplace is registered
        try:
            with open(paths["known_marketplaces"]) as f:
                marketplaces = json.load(f)
            if "superpowers-marketplace" not in marketplaces:
                errors.append("superpowers-marketplace not found in known_marketplaces.json. "
                            "Run: /plugin marketplace add obra/superpowers-marketplace")
            else:
                log_success("superpowers-marketplace is registered")
                log_verbose(f"  Config: {json.dumps(marketplaces['superpowers-marketplace'], indent=2)}", verbose)
        except json.JSONDecodeError as e:
            errors.append(f"Invalid JSON in known_marketplaces.json: {e}")

    # Check plugin cache exists
    if not paths["plugin_cache_superpowers"].exists():
        errors.append(f"Plugin cache not found at: {paths['plugin_cache_superpowers']}. "
                     "The marketplace may not have been synced. Try: /plugin marketplace add obra/superpowers-marketplace")
    else:
        log_success(f"Found plugin cache")
        # Find the version
        versions = list(paths["plugin_cache_superpowers"].iterdir())
        if versions:
            log_verbose(f"  Available versions: {[v.name for v in versions]}", verbose)

    return (len(errors) == 0, errors)

def get_plugin_version(paths: dict[str, Path]) -> Optional[str]:
    """Get the latest plugin version from cache."""
    cache_path = paths["plugin_cache_superpowers"]
    if not cache_path.exists():
        return None

    versions = sorted(cache_path.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True)
    if versions:
        return versions[0].name
    return None

def check_already_installed(paths: dict[str, Path], project_path: Path, verbose: bool) -> bool:
    """Check if superpowers@superpowers-marketplace is already installed for this project."""
    if not paths["installed_plugins"].exists():
        return False

    try:
        with open(paths["installed_plugins"]) as f:
            data = json.load(f)

        plugin_key = "superpowers@superpowers-marketplace"
        if plugin_key not in data.get("plugins", {}):
            return False

        installations = data["plugins"][plugin_key]
        project_str = str(project_path)

        for inst in installations:
            if inst.get("scope") == "user":
                log_warn("superpowers@superpowers-marketplace is installed at user scope (globally)")
                return True
            if inst.get("projectPath") == project_str:
                log_warn(f"superpowers@superpowers-marketplace is already installed for this project")
                return True

        return False
    except (json.JSONDecodeError, KeyError) as e:
        log_verbose(f"Error checking installation: {e}", verbose)
        return False

def update_installed_plugins(paths: dict[str, Path], project_path: Path, scope: str, verbose: bool) -> bool:
    """Add entry to installed_plugins.json."""
    filepath = paths["installed_plugins"]

    try:
        with open(filepath) as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        log_error(f"Failed to read {filepath}: {e}")
        return False

    plugin_key = "superpowers@superpowers-marketplace"
    version = get_plugin_version(paths) or "unknown"
    now = datetime.now().isoformat()

    new_entry: dict[str, Any] = {
        "installPath": str(paths["plugin_cache_superpowers"] / version),
        "version": version,
        "installedAt": now,
        "lastUpdated": now,
    }

    if scope == "user":
        new_entry["scope"] = "user"
    else:
        new_entry["scope"] = "local"
        new_entry["projectPath"] = str(project_path)

    # Initialize plugins dict if needed
    if "plugins" not in data:
        data["plugins"] = {}

    # Initialize plugin array if needed
    if plugin_key not in data["plugins"]:
        data["plugins"][plugin_key] = []

    # Add the new entry
    data["plugins"][plugin_key].append(new_entry)

    log_verbose(f"New entry: {json.dumps(new_entry, indent=2)}", verbose)

    try:
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        log_success(f"Updated {filepath}")
        return True
    except IOError as e:
        log_error(f"Failed to write {filepath}: {e}")
        return False

def update_settings(paths: dict[str, Path], scope: str, verbose: bool) -> bool:
    """Add enabledPlugins entry to settings file."""
    filepath = paths["settings"]

    # Read existing or create new
    if filepath.exists():
        try:
            with open(filepath) as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            log_error(f"Invalid JSON in {filepath}: {e}")
            return False
    else:
        data = {}
        # Create parent directory if needed
        filepath.parent.mkdir(parents=True, exist_ok=True)

    # Add enabledPlugins
    if "enabledPlugins" not in data:
        data["enabledPlugins"] = {}

    data["enabledPlugins"]["superpowers@superpowers-marketplace"] = True

    log_verbose(f"Settings will be: {json.dumps(data, indent=2)}", verbose)

    try:
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
            f.write('\n')  # Trailing newline
        log_success(f"Updated {filepath}")
        return True
    except IOError as e:
        log_error(f"Failed to write {filepath}: {e}")
        return False

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Fix superpowers plugin installation for Claude Code",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
SCOPE OPTIONS:
  project-local   Install for current user in this project only (default)
                  Uses: .claude/settings.local.json

  project-shared  Install for all users of this project
                  Uses: .claude/settings.json (committed to git)

  user            Install globally for current user (all projects)
                  Uses: ~/.claude/settings.json

EXAMPLES:
  # Interactive mode (default) - will ask for confirmation
  ./fix-superpowers-plugin.py

  # Non-interactive mode for scripts
  ./fix-superpowers-plugin.py -y

  # Install for all project users
  ./fix-superpowers-plugin.py --scope project-shared

  # Verbose output for debugging
  ./fix-superpowers-plugin.py -v

RELATED ISSUES:
  https://github.com/anthropics/claude-code/issues/20593
  https://github.com/anthropics/claude-code/issues/14202
  https://github.com/obra/superpowers-marketplace/issues/11
  https://github.com/obra/superpowers/issues/355
"""
    )

    parser.add_argument(
        "-y", "--yes", "--non-interactive",
        dest="non_interactive",
        action="store_true",
        help="Non-interactive mode: skip all confirmation prompts"
    )

    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose/debug output"
    )

    parser.add_argument(
        "--scope",
        choices=["project-local", "project-shared", "user"],
        default="project-local",
        help="Installation scope (default: project-local)"
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes"
    )

    parser.add_argument(
        "--project-path",
        type=Path,
        default=Path.cwd(),
        help="Project path (default: current directory)"
    )

    args = parser.parse_args()

    # Print banner
    print_banner()

    project_path = args.project_path.resolve()
    paths = get_paths(args.scope, project_path)

    log_info(f"Project path: {project_path}")
    log_info(f"Scope: {args.scope}")

    if args.dry_run:
        log_warn("DRY RUN MODE - No changes will be made")

    # === IMPORTANT WARNING ===
    log_step("Pre-flight checks")
    print(color("""
┌──────────────────────────────────────────────────────────────────────────────┐
│  ⚠️  IMPORTANT: Please close Claude Code in this directory before proceeding  │
│                                                                              │
│  This script modifies .claude/settings files. If Claude Code is running,     │
│  there may be a race condition where your changes get overwritten.           │
│                                                                              │
│  To close Claude Code:                                                       │
│    - In the Claude Code TUI, type /exit or press Ctrl+C                      │
│    - Or close the terminal/tmux pane running Claude Code                     │
│                                                                              │
│  Don't worry - all files will be backed up before any modifications!         │
└──────────────────────────────────────────────────────────────────────────────┘
""", Colors.YELLOW))

    if not ask_confirmation("Have you closed Claude Code in this directory?", args.non_interactive):
        log_info("Please close Claude Code and run this script again.")
        return 0

    # === VERIFY ASSUMPTIONS ===
    success, errors = verify_assumptions(paths, args.verbose)

    if not success:
        log_error("Assumption verification failed!")
        for err in errors:
            log_error(f"  - {err}")
        print_debug_info("Assumption verification failed", {
            "paths": {k: str(v) for k, v in paths.items()},
            "errors": errors,
            "project_path": str(project_path),
            "scope": args.scope,
        })
        return 1

    # === CHECK IF ALREADY INSTALLED ===
    log_step("Checking current installation status")

    if check_already_installed(paths, project_path, args.verbose):
        if not ask_confirmation("Plugin appears to be already installed. Continue anyway?", args.non_interactive):
            log_info("Exiting without changes.")
            return 0
    else:
        log_success("Plugin not yet installed for this project/scope")

    # === SHOW WHAT WILL BE MODIFIED ===
    log_step("Files to be modified")

    files_to_modify = [
        paths["installed_plugins"],
        paths["settings"],
    ]

    for f in files_to_modify:
        status = "exists" if f.exists() else "will be created"
        print(f"  - {f} ({status})")

    if args.dry_run:
        log_info("DRY RUN: Would modify the above files")
        return 0

    if not ask_confirmation("Proceed with modifications?", args.non_interactive):
        log_info("Exiting without changes.")
        return 0

    # === CREATE BACKUPS ===
    log_step("Creating backups")

    backups = []
    for f in files_to_modify:
        backup = backup_file(f, args.verbose)
        if backup:
            backups.append(backup)

    if not backups:
        log_info("No existing files to back up")

    # === APPLY MODIFICATIONS ===
    log_step("Applying modifications")

    # Update installed_plugins.json
    log_info("Updating installed_plugins.json...")
    if not update_installed_plugins(paths, project_path, args.scope, args.verbose):
        log_error("Failed to update installed_plugins.json")
        print_debug_info("Failed to update installed_plugins.json", {
            "paths": {k: str(v) for k, v in paths.items()},
            "project_path": str(project_path),
            "scope": args.scope,
        })
        return 1

    # Update settings file
    log_info(f"Updating {paths['settings'].name}...")
    if not update_settings(paths, args.scope, args.verbose):
        log_error(f"Failed to update {paths['settings']}")
        print_debug_info("Failed to update settings", {
            "paths": {k: str(v) for k, v in paths.items()},
            "project_path": str(project_path),
            "scope": args.scope,
        })
        return 1

    # === SUCCESS ===
    print(color("""
╔══════════════════════════════════════════════════════════════════════════════╗
║  ✅ SUCCESS! Plugin installation workaround applied.                         ║
╚══════════════════════════════════════════════════════════════════════════════╝
""", Colors.GREEN))

    print("Next steps:")
    print(f"  1. Start Claude Code in this directory: {color('claude', Colors.CYAN)}")
    print(f"  2. Run {color('/plugin', Colors.CYAN)} and check the Installed tab")
    print(f"  3. You should see: {color('superpowers Plugin · superpowers-marketplace · ✔ enabled', Colors.GREEN)}")

    if backups:
        print(f"\nBackups created:")
        for b in backups:
            print(f"  - {b}")

    return 0

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n")
        log_info("Interrupted by user")
        sys.exit(130)
    except Exception as e:
        log_error(f"Unexpected error: {e}")
        import traceback
        print_debug_info(f"Unexpected exception: {e}", {
            "traceback": traceback.format_exc(),
        })
        sys.exit(1)
