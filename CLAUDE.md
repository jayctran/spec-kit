# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Spec Kit is an open-source toolkit for **Spec-Driven Development (SDD)** - a methodology where specifications are written first and used to generate implementations. The main deliverable is `specify-cli`, a Python CLI tool that bootstraps SDD projects with templates and slash commands for 15+ AI coding assistants.

## Development Commands

```bash
# Run CLI directly (fastest feedback loop)
python -m src.specify_cli --help
python -m src.specify_cli init demo-project --ai claude --ignore-agent-tools

# Editable install for isolated testing
uv venv && source .venv/bin/activate
uv pip install -e .
specify --help

# Run with uvx from repo root
uvx --from . specify init demo-project --ai claude --ignore-agent-tools

# Test from any directory using absolute path
uvx --from /path/to/spec-kit specify init demo-project --ai claude

# Build wheel locally
uv build

# Basic import check (no test suite exists)
python -c "import specify_cli; print('Import OK')"
```

## Architecture

### Single-File CLI Implementation
The entire CLI lives in `src/specify_cli/__init__.py` (~1,400 lines). Key components:

- **`AGENT_CONFIG` dict** (line ~125): Configuration for all 15+ supported AI agents - name, folder path, install URL, CLI requirement
- **`StepTracker` class** (line ~245): Live-updating tree-based progress display using Rich
- **`select_with_arrows()`** (line ~350): Interactive keyboard navigation for agent/script selection
- **`download_template_from_github()`** (line ~637): Fetches latest release assets from GitHub API with rate-limit handling
- **`download_and_extract_template()`** (line ~751): Extracts templates and merges with existing directories
- **`init()`** (line ~945): Main init command orchestrating the full bootstrap flow
- **`check()`** (line ~1243): Validates installed tools (git, AI CLIs, VS Code)
- **`version()`** (line ~1286): Displays CLI and template versions

### Template Distribution
Templates are distributed via GitHub Releases, not bundled in the package:
- `templates/` - Markdown templates for specs, plans, tasks, checklists
- `templates/commands/` - Slash command definitions (specify, plan, tasks, implement, etc.)
- `scripts/bash/` and `scripts/powershell/` - Helper scripts for project setup
- `memory/` - Constitution template for project principles

### Release Workflow
`.github/workflows/release.yml` monitors changes to `memory/`, `scripts/`, `templates/`, and creates tagged releases with per-agent asset packages.

## Key Dependencies

- **typer**: CLI framework
- **rich**: Terminal UI (panels, trees, progress, live display)
- **httpx**: HTTP client for GitHub API
- **readchar**: Cross-platform keyboard input
- **truststore**: SSL/TLS certificate handling

## Environment Variables

- `GH_TOKEN` / `GITHUB_TOKEN`: GitHub API authentication (increases rate limit 60→5000 req/hour)
- `SPECIFY_FEATURE`: Override feature directory detection in non-Git repos

## Adding a New AI Agent

1. Add entry to `AGENT_CONFIG` dict in `src/specify_cli/__init__.py`
2. Create agent-specific folder structure in release assets
3. Document in `AGENTS.md`

## Important Patterns

- **File merging**: `.vscode/settings.json` is deep-merged rather than overwritten
- **Execute permissions**: Shell scripts get `chmod +x` on Unix systems
- **Rate limit handling**: Graceful fallback with user-friendly error messages when GitHub API limits hit
- **Cross-platform**: Both bash (`.sh`) and PowerShell (`.ps1`) script variants available
