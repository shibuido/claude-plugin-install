# claude-plugin-install: Project Guidelines

## Documentation Tier System

This project uses a three-tier documentation structure. Each tier has a distinct audience and purpose. Content must be placed in the correct tier.

### Tier 1: README.md (GitHub Landing Page)

First impression for visitors -- scannable in under 30 seconds.

Contains:

* One-liner pitch
* Feature highlights (bullet list)
* Quick start install (curl + uv only)
* Problem context
* Documentation links

Does NOT contain:

* Full CLI reference
* All options
* Troubleshooting
* Internals
* Detailed examples

Target: under ~80 lines.

### Tier 2: claude-plugin-install.README.md (Complete User Manual)

Full reference for users who want to use every feature.

Contains:

* All features
* All options
* All examples
* Troubleshooting
* Scope details
* Interactive mode details

Updated whenever features are added or changed. This is the authoritative source for "how to use every feature".

### Tier 3: claude-plugin-install.DEV_NOTES.md (Developer Internals)

For contributors and debuggers only.

Contains:

* Internal architecture
* Class responsibilities
* Cache formats
* Debugging workflows
* JSONL schemas

Not needed by end users.

## Content Placement Rules

### When adding a new feature

1. Add a one-line bullet in README.md Features section
2. Add full documentation in claude-plugin-install.README.md
3. Add internal details (if any) in claude-plugin-install.DEV_NOTES.md
4. If feature has external links, add to DISCUSSIONS.md

### When fixing a bug

* Update Tier 2 if the fix changes user-visible behavior
* No README.md change needed unless it fixes a documented limitation

## External Links Maintenance

* DISCUSSIONS.md is the living document for all external URLs (issues, gists, forum posts, mentions)
* archival/CONTEXT.md is frozen historical reference
* Only the most important upstream links belong in README.md

## Style Notes

* Use `*` for bullet points (not `-`)
* Always add blank line before lists
* Code examples use `./claude-plugin-install` (not `python3`)
