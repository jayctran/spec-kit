# JCT Tech Fork Changes

This document describes the changes made in the JCT Tech fork of [github/spec-kit](https://github.com/github/spec-kit).

## Overview

This fork adds **organization template integration** and **Claude Code setup** to the standard spec-kit functionality:

- Fetches GitHub issue templates from `jcttech/.github` during `specify init`
- Configures claude-mem plugin for memory/context tracking
- Configures GitHub MCP server (auto-detected from git remote)
- Provides template-aware issue creation via GitHub MCP
- Uses a wrapper approach to minimize merge conflicts with upstream

## Fork Structure

All fork-specific code is in **new files** - upstream files are not modified (except `pyproject.toml`):

```
src/
├── specify_cli/           # UPSTREAM - unchanged
│   └── __init__.py
└── jcttech/               # FORK - new package
    ├── __init__.py        # Package marker
    ├── wrapper.py         # CLI wrapper entry point
    ├── config.py          # Config loading (.specify/config.yml)
    ├── org_templates.py   # Template fetching from GitHub
    └── claude_settings.py # Claude-mem and GitHub MCP setup

templates/
├── commands/              # UPSTREAM - unchanged
└── jcttech/               # FORK - new templates
    └── commands/
        └── createissue.md # Template-aware issue creation

.github/workflows/scripts/
├── create-release-packages.sh  # UPSTREAM - unchanged
└── jcttech-release.sh          # FORK - wrapper for release packaging
```

## Changes to pyproject.toml

Only 3 additive changes:

1. **Added `pyyaml` dependency** - For config file parsing
2. **Changed entry point** - `specify = "jcttech.wrapper:main"` (was `specify_cli:main`)
3. **Added package** - `"src/jcttech"` to wheel packages list

## Tag Naming Convention

- **Upstream tags**: `v0.0.90`, `v0.0.91`, etc.
- **Fork tags**: `jcttech-v0.0.90`, `jcttech-v0.0.91`, etc.

## Sync Workflow

### Initial Setup

```bash
git remote add upstream https://github.com/github/spec-kit.git
git fetch upstream --tags
```

### Upgrading to New Upstream Version

```bash
# Fetch latest upstream tags
git fetch upstream --tags

# Merge the new upstream tag
git merge tags/v0.0.91

# Resolve any conflicts in pyproject.toml (re-apply our 3 changes)
# - Add pyyaml to dependencies
# - Change entry point to jcttech.wrapper:main
# - Add src/jcttech to packages

# Tag the fork release
git tag jcttech-v0.0.91
git push origin main --tags
```

### Expected Merge Conflicts

| File | Likelihood | Resolution |
|------|------------|------------|
| `pyproject.toml` | Low-Medium | Re-apply 3 additive changes |
| Other files | None | Fork code is in separate files |

## Features Added

### Organization Template Fetching

After `specify init`, the CLI fetches issue templates from `jcttech/.github`:

- `epic.yml` - Cross-cutting initiatives
- `spec.yml` - Technical specifications
- `story.yml` - Implementable work units
- `task.yml` - Granular work items
- `bug.yml` - Defects and regressions
- `pull_request_template.md` - PR template

Templates are stored in `.specify/org-templates/` in the initialized project.

### Configuration File

Projects include `.specify/config.yml`:

```yaml
org_templates:
  source: "jcttech/.github"
  template_path: ".github/ISSUE_TEMPLATE"
  include_pr_template: true
  enabled: true

claude_settings:
  enable_claude_mem: true
  enable_github_mcp: true

github_mcp:
  use_org_templates: true

fork:
  upstream_tag: "v0.0.90"
  fork_tag: "jcttech-v0.0.90"
```

### Claude Code Settings

After `specify init`, the CLI configures `.claude/settings.json` with:

- **claude-mem plugin**: Enabled for memory/context tracking across sessions
- **GitHub MCP server**: HTTP-based via GitHub Copilot API (repo context determined at runtime)

Generated `.claude/settings.json`:
```json
{
  "enabledPlugins": {
    "claude-mem@thedotmack": true
  },
  "mcpServers": {
    "github": {
      "type": "http",
      "url": "https://api.githubcopilot.com/mcp/",
      "headers": {
        "Authorization": "Bearer ${GITHUB_PERSONAL_ACCESS_TOKEN}"
      }
    }
  },
  "permissions": {
    "allow": ["mcp__github__*"]
  }
}
```

### New CLI Options

```bash
# Skip organization templates
specify init my-project --ai claude --skip-org-templates

# Skip Claude settings configuration
specify init my-project --ai claude --skip-claude-settings

# Skip both
specify init my-project --ai claude --skip-org-templates --skip-claude-settings
```

### Template-Aware Issue Creation

The `/speckit.createissue` command creates GitHub issues using the fetched organization templates with proper field mapping.

## Building Fork Releases

```bash
# Build release packages with fork-specific enhancements
.github/workflows/scripts/jcttech-release.sh jcttech-v0.0.90
```

This:
1. Runs upstream `create-release-packages.sh`
2. Adds `.specify/config.yml` to each package
3. Adds JCT Tech command templates
4. Renames packages to use fork version

## Testing

```bash
# Import check
uv run python -c "from jcttech.wrapper import main; print('OK')"
uv run python -c "from jcttech.claude_settings import configure_claude_settings; print('OK')"

# CLI test with git repo
mkdir /tmp/test-project && cd /tmp/test-project
git init && git remote add origin https://github.com/jcttech/test-repo.git
specify init --here --ai claude --force

# Verify org templates fetched
ls .specify/org-templates/

# Verify Claude settings configured
cat .claude/settings.json
```

## Maintainers

- JCT Tech team
