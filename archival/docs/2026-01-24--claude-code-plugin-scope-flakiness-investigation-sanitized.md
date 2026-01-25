# Claude Code Plugin Scope Flakiness Investigation

**Date:** 2026-01-24

## Problem Summary

Per-repository plugin installation in Claude Code is **flaky** - sometimes works, sometimes doesn't. There's also no reliable way to install plugins **globally always** (enabled for all projects by default).

## Observed Symptom (Captured from tmux session)

```
❯ /plugin marketplace add obra/superpowers-marketplace
  ⎿  Error: Marketplace 'superpowers-marketplace' is already installed. Please remove it first
     using '/plugin marketplace remove superpowers-marketplace' if you want to re-install it.

❯ /plugin install superpowers@superpowers-marketplace
  ⎿  Plugin 'superpowers@claude-plugins-official' is already installed. Use '/plugin' to manage
     existing plugins.

❯ /plugin update superpowers
─────────────────────────────────────────────────────────────────────────────────────────────
 Plugins  Discover   Installed   Marketplaces  (←/→ or tab to cycle)

 ╭─────────────────────────────────────────────────────────────────────────────────────────╮
 │ ⌕ Search…                                                                               │
 ╰─────────────────────────────────────────────────────────────────────────────────────────╯

   User
 ❯ rust-analyzer-lsp Plugin · claude-plugins-official · ✔ enabled

  type to search · Space to toggle · Enter to details · Esc to back
```

**Key observations:**

1. Marketplace says "already installed" even when trying to reinstall
2. Plugin install says "already installed" but points to **wrong marketplace** (`claude-plugins-official` instead of `superpowers-marketplace`)
3. Only `rust-analyzer-lsp` shows in Installed tab - the superpowers plugin is NOT available despite claiming to be installed

---

## Related GitHub Issues Found

### Most Directly Relevant (Same Symptom)

| Issue | Title | State | Link |
|-------|-------|-------|------|
| **#20390** | `/plugin install` reports "already installed" for plugins installed in different projects with local scope | OPEN | https://github.com/anthropics/claude-code/issues/20390 |
| **#20077** | Plugin management scope conflict prevents usage across projects | OPEN | https://github.com/anthropics/claude-code/issues/20077 |
| **#18322** | Plugin marketplace shows 'installed' for project-scoped plugins from other projects | OPEN | https://github.com/anthropics/claude-code/issues/18322 |
| **#19743** | `/plugins Discover` hides plugins installed at project scope in other projects | OPEN | https://github.com/anthropics/claude-code/issues/19743 |
| **#14185** | Project-scoped plugins: install command fails for new projects, Discovery tab incorrectly hides plugin | OPEN | https://github.com/anthropics/claude-code/issues/14185 |
| **#14202** | Project-scoped plugins incorrectly detected as installed globally | OPEN (11 comments) | https://github.com/anthropics/claude-code/issues/14202 |

### Related Plugin System Issues

| Issue | Title | State | Link |
|-------|-------|-------|------|
| #16585 | Plugins from third-party marketplaces don't appear in /plugin list | OPEN | https://github.com/anthropics/claude-code/issues/16585 |
| #14815 | Plugins show as "(installed)" in marketplace but don't appear in Installed tab | OPEN | https://github.com/anthropics/claude-code/issues/14815 |
| #15642 | Plugin cache: CLAUDE_PLUGIN_ROOT points to stale version after plugin update | OPEN | https://github.com/anthropics/claude-code/issues/15642 |
| #14061 | `/plugin update` does not invalidate plugin cache | OPEN (duplicate) | https://github.com/anthropics/claude-code/issues/14061 |
| #19899 | Cached plugin overrides local plugin with same name | OPEN | https://github.com/anthropics/claude-code/issues/19899 |
| #18161 | Plugin checkbox toggle unresponsive in /plugins UI | OPEN | https://github.com/anthropics/claude-code/issues/18161 |

---

## Actual State from ~/.claude/plugins/installed_plugins.json

```json
{
  "version": 2,
  "plugins": {
    "superpowers@superpowers-marketplace": [
      {
        "scope": "local",
        "projectPath": "/home/user/projects/project-a",
        "installPath": "~/.claude/plugins/cache/superpowers-marketplace/superpowers/4.0.3",
        "version": "4.0.3",
        ...
      }
    ],
    "rust-analyzer-lsp@claude-plugins-official": [
      {
        "scope": "user",  // <-- GLOBAL, works everywhere
        ...
      }
    ],
    "superpowers@claude-plugins-official": [
      {
        "scope": "local",
        "projectPath": "/home/user/projects/project-b",
        ...
      }
    ]
  }
}
```

**Critical observation:** There are TWO separate superpowers entries:

1. `superpowers@superpowers-marketplace` - installed for one project
2. `superpowers@claude-plugins-official` - installed for a different project

When user runs `/plugin install superpowers@superpowers-marketplace` in a THIRD project, error says:
> `Plugin 'superpowers@claude-plugins-official' is already installed.`

This reveals **TWO bugs:**

1. **Wrong plugin name resolution** - System confuses `superpowers@superpowers-marketplace` with `superpowers@claude-plugins-official` (matching on plugin name, ignoring marketplace)
2. **Scope confusion** - Says "already installed" when it's only installed for different projects

**Marketplaces are correctly configured** (known_marketplaces.json):

```json
{
  "claude-plugins-official": { "source": "github", "repo": "anthropics/claude-plugins-official" },
  "superpowers-marketplace": { "source": "github", "repo": "obra/superpowers-marketplace" }
}
```

**Plugin exists in BOTH marketplace caches:**

```
~/.claude/plugins/cache/
├── claude-plugins-official/
│   ├── rust-analyzer-lsp/
│   └── superpowers/     <-- exists here
└── superpowers-marketplace/
    └── superpowers/     <-- AND here
```

This is the ROOT CAUSE: `superpowers` exists in BOTH marketplaces, and the plugin resolution logic is matching on **plugin name only**, ignoring the marketplace qualifier in the fully-qualified name `superpowers@superpowers-marketplace`.

---

## Root Cause Analysis (from issue investigations)

The fundamental issue is **inconsistent scope checking** across plugin operations:

| Operation | Checks projectPath? | Behavior |
|-----------|---------------------|----------|
| Marketplaces "(installed)" indicator | ❌ No | Shows installed globally |
| Install command | ❌ No | Refuses if exists globally |
| Installed tab listing | ✓ Yes | Correctly filters by project |

**Result:** The install/discover logic checks if a plugin key exists anywhere in `~/.claude/plugins/installed_plugins.json`, but doesn't verify if it's installed for the **current** projectPath.

---

## User Pain Points

1. **Cannot reinstall plugin in new project** - gets "already installed" error
2. **Cannot add plugins globally by default** - no `--scope user --default` or similar
3. **UI shows incorrect status** - "installed" but plugin not functional
4. **Workaround requires manual JSON editing** - error-prone and undocumented

---

## Workarounds (from GitHub issues)

### Workaround 1: Manual `installed_plugins.json` Edit

Add new project entry to existing plugin array in `~/.claude/plugins/installed_plugins.json`:

```json
{
  "plugins": {
    "superpowers@superpowers-marketplace": [
      {
        "scope": "local",
        "projectPath": "/path/to/existing/project",
        ...
      },
      {
        "scope": "local",
        "projectPath": "/path/to/new/project",
        "installPath": "~/.claude/plugins/cache/superpowers-marketplace/superpowers/unknown",
        "version": "unknown",
        "installedAt": "2026-01-24T00:00:00.000Z",
        "lastUpdated": "2026-01-24T00:00:00.000Z"
      }
    ]
  }
}
```

### Workaround 2: Remove and Reinstall

```bash
/plugin uninstall superpowers@superpowers-marketplace
/plugin install superpowers@superpowers-marketplace
```

### Workaround 3: Create Project Settings Manually

Create `.claude/settings.json` in target project:

```json
{
  "enabledPlugins": {
    "superpowers@superpowers-marketplace": true
  }
}
```

---

## Feature Gap: Global Plugin Installation

**Current state:** No way to install a plugin that's automatically enabled for all projects.

**Desired feature:**

```bash
/plugin install superpowers --scope global --always-enabled
```

Or in settings:

```json
{
  "globallyEnabledPlugins": ["superpowers@superpowers-marketplace"]
}
```

**Related issues to track:** None found specifically for this feature. May need to file new issue.

---

## Recommendation: Where to Respond

**Primary recommendation:** Comment on **#14202** (11 comments, most comprehensive discussion)

This issue has:

* Most community engagement
* Clear root cause analysis
* Detailed workarounds
* Multiple platforms affected

**Draft comment template:**

```markdown
AI Assistant:

Adding another data point to this cluster of issues:

**Symptom:** When running `/plugin install superpowers@superpowers-marketplace`:
- Error: `Plugin 'superpowers@claude-plugins-official' is already installed`
- Note the **wrong marketplace** in error message (`claude-plugins-official` vs `superpowers-marketplace`)
- Plugin not functional in current project despite "installed" status

This suggests the scope confusion extends beyond projectPath to **marketplace resolution** as well.

**Related issues experiencing same cluster of symptoms:**
- #20390, #20077, #18322, #19743, #14185

**Feature gap:** Would also benefit from a way to install plugins as "globally always enabled" (`--scope global --default`) to avoid per-project installation friction entirely.

Environment: Claude Code v2.1.19, Linux
```

**Alternative:** If filing new issue, cross-reference all related issues above.

---

## Next Steps for Debugging

1. **Capture `installed_plugins.json`** to see actual stored state
2. **Check `.claude/settings.json`** in both user home and project directory
3. **Try explicit uninstall then reinstall** in the affected session
4. **Capture any error logs** from `~/.claude/debug/`

---

## Related Documentation Gaps

* Plugin scope semantics not clearly documented
* No troubleshooting guide for "installed but not working"
* Global/always-enabled plugins not documented (doesn't exist?)

---

## FINAL RECOMMENDATION

### Option A: Comment on existing issue #14202 (Recommended)

This issue has the most engagement (11 comments) and covers the same root cause. Comment should include:

1. **New data point:** Plugin name collision across marketplaces (`superpowers@superpowers-marketplace` vs `superpowers@claude-plugins-official`)
2. **Evidence:** Error message shows wrong marketplace (`claude-plugins-official` when installing from `superpowers-marketplace`)
3. **Cross-reference:** Link to cluster of related issues (#20390, #20077, #18322, #19743, #14185)
4. **Feature request:** Global always-enabled plugins

### Option B: File NEW issue (if distinct enough)

Title: `[BUG] Plugin install matches wrong marketplace when same plugin name exists in multiple marketplaces`

This is arguably a **distinct bug** from the scope issues - it's about marketplace name resolution, not just projectPath checking.

### Draft GitHub Comment (for #14202):

```markdown
AI Assistant:

Adding another dimension to this cluster of issues:

## Plugin Name Collision Across Marketplaces

When `superpowers` exists in BOTH `claude-plugins-official` AND `superpowers-marketplace`:

1. Run `/plugin install superpowers@superpowers-marketplace` in Project C
2. Error: `Plugin 'superpowers@claude-plugins-official' is already installed`

**Note the WRONG marketplace** in the error message.

## State from installed_plugins.json

```json
{
  "superpowers@superpowers-marketplace": [{ "projectPath": "/path/to/project-a", "scope": "local" }],
  "superpowers@claude-plugins-official": [{ "projectPath": "/path/to/project-b", "scope": "local" }]
}
```

Both entries exist with different marketplaces, but install command matches only on plugin name, ignoring the marketplace qualifier.

## Cache confirms plugin exists in both marketplaces

```
~/.claude/plugins/cache/
├── claude-plugins-official/superpowers/
└── superpowers-marketplace/superpowers/
```

This suggests the plugin resolution is stripping the marketplace suffix when checking if already installed.

**Related issues:** #20390, #20077, #18322, #19743, #14185

**Environment:** Claude Code v2.1.19, Linux
```

---

## Immediate Workaround for User

To install superpowers in a new project, manually edit `~/.claude/plugins/installed_plugins.json`:

```bash
# Add new project entry to the superpowers@superpowers-marketplace array
jq '.plugins["superpowers@superpowers-marketplace"] += [{
  "scope": "local",
  "projectPath": "/path/to/your/project",
  "installPath": "~/.claude/plugins/cache/superpowers-marketplace/superpowers/4.0.3",
  "version": "4.0.3",
  "installedAt": "'$(date -Iseconds)'",
  "lastUpdated": "'$(date -Iseconds)'"
}]' ~/.claude/plugins/installed_plugins.json > /tmp/installed_plugins_fixed.json
```

Then restart Claude Code.

---

## WORKAROUND VERIFIED WORKING (2026-01-24)

After applying the manual JSON edit and creating `.claude/settings.json` with `enabledPlugins`:

**BEFORE (broken):**

```
   User
 ❯ rust-analyzer-lsp Plugin · claude-plugins-official · ✔ enabled
```

**AFTER (fixed):**

```
   Local
 ❯ superpowers Plugin · superpowers-marketplace · ✔ enabled

   User
   rust-analyzer-lsp Plugin · claude-plugins-official · ✔ enabled
```

The plugin now appears in Installed tab and is enabled for this specific project.
