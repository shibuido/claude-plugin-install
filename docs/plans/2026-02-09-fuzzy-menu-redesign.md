# Fuzzy Menu Redesign Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the 59-item numbered list with a fuzzy-searchable menu using sk/fzf, with a threshold-limited fallback menu.

**Architecture:** `display_menu()` builds structured items, delegates to `_menu_fuzzy()` (sk or fzf) or `_menu_fallback()` (current logic + threshold + comma multi-select). Tool detection via `shutil.which()`. Multi-select supported in all modes.

**Tech Stack:** Python 3.10+, subprocess for sk/fzf, no new dependencies.

---

### Task 1: Fuzzy Finder Detection

**Files:**
- Modify: `claude-plugin-install` (MenuHandler class)

**Step 1: Write detection function**

Add to `MenuHandler`:

```python
@staticmethod
def _detect_fuzzy_finder() -> Optional[str]:
    """Detect available fuzzy finder: sk -> fzf -> None."""
    if shutil.which("sk"):
        return "sk"
    if shutil.which("fzf"):
        return "fzf"
    return None
```

**Step 2: Verify manually**

```bash
python3 -c "import shutil; print(shutil.which('sk'), shutil.which('fzf'))"
```

**Step 3: Commit**

```bash
git add claude-plugin-install
git commit -m "feat: Add fuzzy finder detection (sk -> fzf -> fallback)"
```

---

### Task 2: Build Menu Items

**Files:**
- Modify: `claude-plugin-install` (MenuHandler class)

**Step 1: Write item builder**

Add `_build_menu_items()` that returns a sorted list of dicts. Each dict has:
- `idx`: sequential number (1-based)
- `key`: plugin@marketplace string
- `tag`: `"i"` for installed, `"a"` for available
- `installed`: bool
- `scopes`: list of scopes (for installed) or empty
- `description`: from cache or empty string
- `use_count`: int
- `last_used`: ISO string or empty
- `line`: formatted display string

**Sorting order:**
1. Installed plugins (alphabetical by key)
2. Previously-used plugins (use_count desc, last_used desc)
3. Never-used plugins (alphabetical by key)

**Line format:**

```
 1i. superpowers@superpowers-marketplace        :: Core skills library: TDD, debugging...
 2a. playwright@claude-plugins-official          :: Browser automation and end-to-end...
```

Pad the number to consistent width. The `::` separator is used for parsing back.

**Step 2: Verify items are built correctly**

```bash
python3 claude-plugin-install -v 2>&1 | head -5  # just test it launches
```

**Step 3: Commit**

```bash
git add claude-plugin-install
git commit -m "feat: Add _build_menu_items with sorted tagged lines"
```

---

### Task 3: Fuzzy Finder Menu

**Files:**
- Modify: `claude-plugin-install` (MenuHandler class)

**Step 1: Write _menu_fuzzy()**

```python
@staticmethod
def _menu_fuzzy(items: list[dict], finder: str, repo_path: Path) -> Optional[list[dict]]:
    """Run sk/fzf with multi-select, return selected items."""
    lines = [item["line"] for item in items]
    input_text = "\n".join(lines)

    cmd = [
        finder, "-m",
        "--ansi",
        "--reverse",
        "--prompt", "Plugin> ",
        "--header", "TAB=toggle  ENTER=confirm  ESC=quit",
    ]

    result = subprocess.run(
        cmd, input=input_text, capture_output=True, text=True
    )

    if result.returncode != 0 or not result.stdout.strip():
        return None  # ESC or empty

    selected_lines = result.stdout.strip().split("\n")
    # Parse each line: extract key from before ::
    selected = []
    for sel_line in selected_lines:
        for item in items:
            if item["line"].strip() == sel_line.strip():
                selected.append(item)
                break
    return selected if selected else None
```

**Step 2: Test with sk manually**

```bash
python3 claude-plugin-install  # should launch sk
```

**Step 3: Commit**

```bash
git add claude-plugin-install
git commit -m "feat: Add _menu_fuzzy with sk/fzf multi-select"
```

---

### Task 4: Fallback Menu with Threshold and Comma Multi-Select

**Files:**
- Modify: `claude-plugin-install` (MenuHandler class)

**Step 1: Add CPI_MENU_LIMIT constant**

```python
MENU_LIMIT_DEFAULT = 15
```

Read from env: `int(os.environ.get("CPI_MENU_LIMIT", MENU_LIMIT_DEFAULT))`

**Step 2: Write _menu_fallback()**

Based on current `display_menu()` logic but with:
- Installed plugins always shown (no limit)
- Available plugins capped at `CPI_MENU_LIMIT`
- If more exist: `"... and N more plugins. Install sk or fzf for fuzzy search."`
- Input parsing supports comma-separated numbers: `15,18,23,42`
- Returns list of selected items (single or multi)

**Step 3: Test fallback mode**

```bash
# Force fallback by temporarily hiding sk/fzf
PATH=/usr/bin/no-sk python3 claude-plugin-install
```

**Step 4: Commit**

```bash
git add claude-plugin-install
git commit -m "feat: Add fallback menu with CPI_MENU_LIMIT and comma multi-select"
```

---

### Task 5: Refactor display_menu() to Orchestrate

**Files:**
- Modify: `claude-plugin-install` (MenuHandler class)

**Step 1: Rewrite display_menu()**

```python
@staticmethod
def display_menu(repo_path: Path) -> Optional[list[dict]]:
    """Display interactive menu, return selected item(s)."""
    items = MenuHandler._build_menu_items(repo_path)
    if not items:
        print("  No plugins available. Run: cache sync")
        return None

    finder = MenuHandler._detect_fuzzy_finder()
    if finder:
        return MenuHandler._menu_fuzzy(items, finder, repo_path)
    else:
        return MenuHandler._menu_fallback(items, repo_path)
```

**Step 2: Update return type**

`display_menu()` now returns `Optional[list[dict]]` instead of `Optional[dict]`. Update `cmd_interactive_menu()` to handle list of selections.

**Step 3: Handle multi-select in cmd_interactive_menu()**

- All `a.` (available) selections -> batch install each
- All `i.` (installed) selections -> offer manage/uninstall for each
- Mixed -> ask user what action to apply
- Single selection -> current behavior

**Step 4: Test end-to-end**

```bash
python3 claude-plugin-install  # sk mode
CPI_MENU_LIMIT=5 PATH=/usr/bin/no-sk python3 claude-plugin-install  # fallback
```

**Step 5: Commit**

```bash
git add claude-plugin-install
git commit -m "feat: Refactor display_menu to orchestrate fuzzy/fallback renderers"
```

---

### Task 6: E2E Test for Fuzzy Menu

**Files:**
- Create: `testing/tests/16-fuzzy-menu/test.sh`
- Create: `testing/tests/16-fuzzy-menu/fixture/.gitkeep`

**Step 1: Write test with mock fuzzy finder**

Create a mock `sk` script in the test that auto-selects the first line:

```bash
#!/bin/sh
# Mock sk: read input, output first line
head -1
```

Test verifies:
- Fuzzy finder is detected and used
- Selection is parsed correctly
- Fallback works when mock is removed

**Step 2: Write fallback threshold test**

Populate cache with 25 plugins, verify only CPI_MENU_LIMIT are shown.

**Step 3: Test comma multi-select in fallback**

Feed `1,2,3` via tmux, verify multiple items returned.

**Step 4: Run and commit**

```bash
chmod +x testing/tests/16-fuzzy-menu/test.sh
./testing/run_tests.sh 16-fuzzy-menu
git add testing/tests/16-fuzzy-menu/
git commit -m "test: Add E2E test for fuzzy menu and fallback threshold"
```

---

### Task 7: Documentation Update

**Files:**
- Modify: `README.md`
- Modify: `testing/TESTING_DEVELOPER_GUIDELINES.md`

**Step 1: Update README**

- Add section about fuzzy search: sk/fzf auto-detection
- Document `CPI_MENU_LIMIT` env var
- Document multi-select (TAB in sk/fzf, comma in fallback)

**Step 2: Update test guidelines table**

Add test 16 to the organization table.

**Step 3: Commit**

```bash
git add README.md testing/TESTING_DEVELOPER_GUIDELINES.md
git commit -m "docs: Document fuzzy menu, CPI_MENU_LIMIT, and multi-select"
```
