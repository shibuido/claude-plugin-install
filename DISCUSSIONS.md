# External Discussions & Links

Central reference for all external URLs where claude-plugin-install or the underlying Claude Code plugin bug is discussed. Update this file when new threads or mentions appear.

## Upstream Bug Reports (Claude Code)

The two primary bugs causing plugin installation failures:

| Issue | Description | Status |
|-------|-------------|--------|
| [#20593](https://github.com/anthropics/claude-code/issues/20593) | Wrong marketplace matching -- plugin name resolution ignores `@marketplace` qualifier | Open |
| [#14202](https://github.com/anthropics/claude-code/issues/14202) | Project scope confusion -- scope checking doesn't filter by `projectPath` | Open |

## Related Upstream Issues

Other issues in `anthropics/claude-code` related to plugin installation and scope handling:

| Issue | Description | URL |
|-------|-------------|-----|
| [#20390](https://github.com/anthropics/claude-code/issues/20390) | Related plugin installation issues | https://github.com/anthropics/claude-code/issues/20390 |
| [#20077](https://github.com/anthropics/claude-code/issues/20077) | Plugin scope issues | https://github.com/anthropics/claude-code/issues/20077 |
| [#19743](https://github.com/anthropics/claude-code/issues/19743) | Plugin installation problems | https://github.com/anthropics/claude-code/issues/19743 |
| [#18322](https://github.com/anthropics/claude-code/issues/18322) | Project-scoped plugins | https://github.com/anthropics/claude-code/issues/18322 |
| [#14185](https://github.com/anthropics/claude-code/issues/14185) | Plugin scope handling | https://github.com/anthropics/claude-code/issues/14185 |

## Community Issues

Tracking issues in the superpowers ecosystem:

| Issue | Repository | Description | URL |
|-------|------------|-------------|-----|
| [#355](https://github.com/obra/superpowers/issues/355) | obra/superpowers | Tracking issue for superpowers users | https://github.com/obra/superpowers/issues/355 |
| [#11](https://github.com/obra/superpowers-marketplace/issues/11) | obra/superpowers-marketplace | Tracking issue for marketplace | https://github.com/obra/superpowers-marketplace/issues/11 |

## Original Prototype

The initial workaround was published as a GitHub Gist before being developed into this tool:

* **Gist:** [gwpl/cd6dcd899ca0acce1b4a1bc486d56a9e](https://gist.github.com/gwpl/cd6dcd899ca0acce1b4a1bc486d56a9e) -- contains `fix-superpowers-plugin.py` (hardcoded version) and `fix-selected-plugin.py` (generic version with `-p PLUGIN -m MARKETPLACE` flags)

## This Tool

* **Repository:** https://github.com/shibuido/claude-plugin-install
* **Issues:** https://github.com/shibuido/claude-plugin-install/issues
* **Raw download:** `curl -fsSL https://raw.githubusercontent.com/shibuido/claude-plugin-install/master/claude-plugin-install -o claude-plugin-install`
