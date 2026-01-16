"""JCT Tech fork wrapper for specify-cli with organization template integration.

This wrapper provides the default `specify` entry point with enhanced functionality:
- Fetches organization templates from jcttech/.github after init
- Configures claude-mem plugin and GitHub MCP server
- Provides template-aware GitHub issue creation
"""

import functools
import os
from pathlib import Path
from typing import Callable

import typer

# Import the original specify_cli module
import specify_cli

from jcttech.org_templates import fetch_org_templates_if_configured
from jcttech.claude_settings import configure_claude_settings_if_enabled
from jcttech.issue_index import initialize_index_structure
from jcttech.config import load_config, get_docs_path


def _get_github_token() -> str | None:
    """Get GitHub token from environment."""
    return (os.getenv("GH_TOKEN") or os.getenv("GITHUB_TOKEN") or "").strip() or None


def _wrap_init_command(original_init: Callable) -> Callable:
    """Wrap the original init command to add org template fetching.

    This wrapper calls the original init command and then fetches
    organization templates if configured.
    """

    @functools.wraps(original_init)
    def wrapped_init(
        project_name: str = typer.Argument(
            None,
            help="Name for your new project directory (optional if using --here, or use '.' for current directory)",
        ),
        ai_assistant: str = typer.Option(
            None,
            "--ai",
            help="AI assistant to use: claude, gemini, copilot, cursor-agent, qwen, opencode, codex, windsurf, kilocode, auggie, codebuddy, amp, shai, q, bob, or qoder",
        ),
        script_type: str = typer.Option(None, "--script", help="Script type to use: sh or ps"),
        ignore_agent_tools: bool = typer.Option(
            False, "--ignore-agent-tools", help="Skip checks for AI agent tools like Claude Code"
        ),
        no_git: bool = typer.Option(False, "--no-git", help="Skip git repository initialization"),
        here: bool = typer.Option(
            False,
            "--here",
            help="Initialize project in the current directory instead of creating a new one",
        ),
        force: bool = typer.Option(
            False, "--force", help="Force merge/overwrite when using --here (skip confirmation)"
        ),
        skip_tls: bool = typer.Option(
            False, "--skip-tls", help="Skip SSL/TLS verification (not recommended)"
        ),
        debug: bool = typer.Option(
            False,
            "--debug",
            help="Show verbose diagnostic output for network and extraction failures",
        ),
        github_token: str = typer.Option(
            None,
            "--github-token",
            help="GitHub token to use for API requests (or set GH_TOKEN or GITHUB_TOKEN environment variable)",
        ),
        # JCT Tech fork additions
        skip_org_templates: bool = typer.Option(
            False,
            "--skip-org-templates",
            help="Skip fetching organization templates (JCT Tech fork feature)",
        ),
    ):
        """Initialize a new Specify project from the latest template.

        This is the JCT Tech fork wrapper that adds organization template
        fetching after the standard init process.
        """
        # Determine project path before calling original init
        if project_name == ".":
            project_path = Path.cwd()
            here_flag = True
        elif here:
            project_path = Path.cwd()
            here_flag = True
        else:
            project_path = Path(project_name).resolve() if project_name else None
            here_flag = False

        # Call the original init command
        # We need to invoke it through the typer context to maintain proper CLI behavior
        try:
            original_init(
                project_name=project_name,
                ai_assistant=ai_assistant,
                script_type=script_type,
                ignore_agent_tools=ignore_agent_tools,
                no_git=no_git,
                here=here,
                force=force,
                skip_tls=skip_tls,
                debug=debug,
                github_token=github_token,
            )
        except SystemExit as e:
            # Re-raise exits from the original command
            raise e

        # After successful init, fetch organization templates
        if not skip_org_templates and project_path and project_path.exists():
            _fetch_org_templates_post_init(
                project_path,
                github_token=github_token or _get_github_token(),
                debug=debug,
            )

    return wrapped_init


def _fetch_org_templates_post_init(
    project_path: Path,
    *,
    github_token: str | None = None,
    debug: bool = False,
) -> None:
    """Fetch organization templates after init completes.

    This is called after the upstream init command finishes successfully.
    """
    console = specify_cli.console

    try:
        result = fetch_org_templates_if_configured(
            project_path,
            github_token=github_token,
            console=console,
        )

        if result:
            if result.get("fetched_files"):
                console.print()
                console.print(
                    f"[bold cyan]Organization templates fetched:[/bold cyan] "
                    f"{len(result['fetched_files'])} files"
                )
                if debug:
                    for f in result["fetched_files"]:
                        console.print(f"  [dim]- {f}[/dim]")

            if result.get("errors"):
                console.print()
                console.print("[yellow]Some templates could not be fetched:[/yellow]")
                for err in result["errors"]:
                    console.print(f"  [dim]- {err}[/dim]")

    except Exception as e:
        # Non-fatal - log warning but don't fail the init
        if debug:
            console.print()
            console.print(f"[yellow]Warning: Could not fetch org templates: {e}[/yellow]")


def _initialize_docs_structure(
    project_path: Path,
    *,
    debug: bool = False,
) -> None:
    """Initialize the .docs/ folder with template files.

    Creates:
    - .docs/constitution.md
    - .docs/architecture.md
    - .docs/decisions.md
    - .docs/architecture.excalidraw (placeholder)
    """
    console = specify_cli.console

    config = load_config(project_path)
    docs_path = project_path / get_docs_path(config)
    docs_path.mkdir(parents=True, exist_ok=True)

    # Create constitution.md
    constitution_path = docs_path / "constitution.md"
    if not constitution_path.exists():
        constitution_path.write_text("""# Project Constitution

## Core Principles

1. [Define your project's core principles here]
2. [These are non-negotiable rules that guide all development]

## Documentation Rules

### Architecture Updates
- **On Plan**: When `/jcttech.plan` creates Stories, update architecture.md
  with new components, services, and integrations
- **On Implement**: When `/jcttech.implement` completes, verify architecture
  matches implementation. Update if different.

### Decision Records
- Record all significant technical decisions in decisions.md
- Link decisions to related Epic/Spec/Story issues
- Mark architectural impact for diagram updates

### Diagram Updates
- Update architecture.excalidraw when:
  - New services or components added
  - Integration patterns change
  - Major refactoring occurs

## Quality Standards

- [Define code quality standards]
- [Testing requirements]
- [Documentation requirements]
""")
        if debug:
            console.print("  [dim]Created constitution.md[/dim]")

    # Create architecture.md
    architecture_path = docs_path / "architecture.md"
    if not architecture_path.exists():
        architecture_path.write_text("""# Architecture Overview

## System Components

_Document your system's major components here._

## Data Flow

_Describe how data flows through your system._

## External Integrations

_List external services and APIs._

## Technology Stack

- **Language**:
- **Framework**:
- **Database**:
- **Infrastructure**:

## Diagrams

See `architecture.excalidraw` for visual diagrams.

---

_Last updated: [Date]_
""")
        if debug:
            console.print("  [dim]Created architecture.md[/dim]")

    # Create decisions.md
    decisions_path = docs_path / "decisions.md"
    if not decisions_path.exists():
        decisions_path.write_text("""# Architecture Decision Records

## Index

| ADR | Title | Status | Date | Related |
|-----|-------|--------|------|---------|

---

_No decisions recorded yet. Use `/jcttech.decision` to record architectural decisions._

---

## Template

When recording a decision, use this format:

```markdown
## ADR-NNN: [Decision Title]

**Status**: proposed | accepted | deprecated | superseded
**Date**: YYYY-MM-DD
**Related Issues**: #issue1, #issue2

### Context
[Why is this decision needed?]

### Options Considered
1. **Option A** - Pros/Cons
2. **Option B** - Pros/Cons

### Decision
[What was decided and why]

### Consequences
- [Positive and negative consequences]

### Architecture Impact
- **Material**: Yes/No
- **Diagram Update**: Required/Not Required
```
""")
        if debug:
            console.print("  [dim]Created decisions.md[/dim]")


def _initialize_issue_tracking_structure(
    project_path: Path,
    *,
    debug: bool = False,
) -> None:
    """Initialize the .specify/issues/ and .specify/drafts/ structure."""
    console = specify_cli.console

    try:
        paths_created = initialize_index_structure(project_path)

        if debug and paths_created:
            console.print()
            console.print("[bold cyan]Issue tracking structure initialized:[/bold cyan]")
            if "index_md" in paths_created:
                console.print("  [dim]Created .specify/issues/index.md[/dim]")
            console.print("  [dim]Created .specify/drafts/spec/[/dim]")
            console.print("  [dim]Created .specify/drafts/plan/[/dim]")

    except Exception as e:
        if debug:
            console.print(f"[yellow]Warning: Could not initialize issue tracking: {e}[/yellow]")


def _configure_claude_settings_post_init(
    project_path: Path,
    *,
    debug: bool = False,
) -> None:
    """Configure Claude Code settings after init completes.

    This sets up:
    - claude-mem plugin for memory/context tracking
    - GitHub MCP server for issue creation (auto-detected from git remote)
    """
    console = specify_cli.console

    try:
        console.print()
        console.print("[bold cyan]Configuring Claude Code settings...[/bold cyan]")

        result = configure_claude_settings_if_enabled(
            project_path,
            console=console,
        )

        if result:
            if debug:
                if result.get("claude_mem_enabled"):
                    console.print("  [dim]claude-mem plugin: enabled[/dim]")
                if result.get("github_mcp_enabled"):
                    console.print("  [dim]GitHub MCP server: configured[/dim]")
                if result.get("github_owner") and result.get("github_repo"):
                    console.print(
                        f"  [dim]Repository: {result['github_owner']}/{result['github_repo']}[/dim]"
                    )

    except Exception as e:
        # Non-fatal - log warning but don't fail the init
        if debug:
            console.print()
            console.print(f"[yellow]Warning: Could not configure Claude settings: {e}[/yellow]")


# Create our own Typer app that wraps the upstream commands
# This is cleaner than monkey-patching and avoids import-time issues
jcttech_app = typer.Typer(
    name="specify",
    help="JCT Tech fork of Specify CLI with organization template integration",
    add_completion=False,
    invoke_without_command=True,
)


@jcttech_app.callback()
def callback(ctx: typer.Context):
    """Show banner when no subcommand is provided."""
    if ctx.invoked_subcommand is None and "--help" not in __import__("sys").argv:
        specify_cli.show_banner()
        specify_cli.console.print(
            specify_cli.Align.center("[dim]Run 'specify --help' for usage information[/dim]")
        )
        specify_cli.console.print()


@jcttech_app.command()
def init(
    project_name: str = typer.Argument(
        None,
        help="Name for your new project directory (optional if using --here, or use '.' for current directory)",
    ),
    ai_assistant: str = typer.Option(
        None,
        "--ai",
        help="AI assistant to use: claude, gemini, copilot, cursor-agent, qwen, opencode, codex, windsurf, kilocode, auggie, codebuddy, amp, shai, q, bob, or qoder",
    ),
    script_type: str = typer.Option(None, "--script", help="Script type to use: sh or ps"),
    ignore_agent_tools: bool = typer.Option(
        False, "--ignore-agent-tools", help="Skip checks for AI agent tools like Claude Code"
    ),
    no_git: bool = typer.Option(False, "--no-git", help="Skip git repository initialization"),
    here: bool = typer.Option(
        False,
        "--here",
        help="Initialize project in the current directory instead of creating a new one",
    ),
    force: bool = typer.Option(
        False, "--force", help="Force merge/overwrite when using --here (skip confirmation)"
    ),
    skip_tls: bool = typer.Option(
        False, "--skip-tls", help="Skip SSL/TLS verification (not recommended)"
    ),
    debug: bool = typer.Option(
        False, "--debug", help="Show verbose diagnostic output for network and extraction failures"
    ),
    github_token: str = typer.Option(
        None,
        "--github-token",
        help="GitHub token to use for API requests (or set GH_TOKEN or GITHUB_TOKEN environment variable)",
    ),
    skip_org_templates: bool = typer.Option(
        False,
        "--skip-org-templates",
        help="Skip fetching organization templates (JCT Tech fork feature)",
    ),
    skip_claude_settings: bool = typer.Option(
        False,
        "--skip-claude-settings",
        help="Skip configuring Claude settings (claude-mem, GitHub MCP)",
    ),
):
    """Initialize a new Specify project from the latest template.

    JCT Tech fork: Also fetches organization templates and configures Claude
    Code settings (claude-mem plugin, GitHub MCP server) after initialization.
    """
    # Determine project path
    if project_name == ".":
        project_path = Path.cwd()
        actual_here = True
        actual_project_name = None
    elif here:
        project_path = Path.cwd()
        actual_here = True
        actual_project_name = None
    else:
        project_path = Path(project_name).resolve() if project_name else None
        actual_here = here
        actual_project_name = project_name

    # Call original init
    specify_cli.init(
        project_name=actual_project_name if not actual_here else None,
        ai_assistant=ai_assistant,
        script_type=script_type,
        ignore_agent_tools=ignore_agent_tools,
        no_git=no_git,
        here=actual_here or project_name == ".",
        force=force,
        skip_tls=skip_tls,
        debug=debug,
        github_token=github_token,
    )

    # Fetch org templates after successful init
    if not skip_org_templates and project_path and project_path.exists():
        _fetch_org_templates_post_init(
            project_path,
            github_token=github_token or _get_github_token(),
            debug=debug,
        )

    # Configure Claude Code settings (claude-mem, GitHub MCP)
    if not skip_claude_settings and project_path and project_path.exists():
        _configure_claude_settings_post_init(
            project_path,
            debug=debug,
        )

    # Initialize .docs/ structure (constitution, architecture, decisions)
    if project_path and project_path.exists():
        specify_cli.console.print()
        specify_cli.console.print("[bold cyan]Initializing documentation structure...[/bold cyan]")
        _initialize_docs_structure(
            project_path,
            debug=debug,
        )

    # Initialize issue tracking structure (.specify/issues/, .specify/drafts/)
    if project_path and project_path.exists():
        specify_cli.console.print()
        specify_cli.console.print("[bold cyan]Initializing issue tracking structure...[/bold cyan]")
        _initialize_issue_tracking_structure(
            project_path,
            debug=debug,
        )


@jcttech_app.command(name="install-commands")
def install_commands(
    ai_assistant: str = typer.Option(
        "claude",
        "--ai",
        help="AI assistant to install commands for: claude, gemini, copilot, cursor-agent, etc.",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        help="Overwrite existing commands",
    ),
    debug: bool = typer.Option(
        False,
        "--debug",
        help="Show verbose output",
    ),
):
    """Install jcttech commands to the current project.

    This copies bundled jcttech command templates to your project's
    agent command directory (e.g., .claude/commands/ for Claude Code).

    Run this in a project directory after `specify init` or to update
    commands in an existing project.
    """
    import importlib.resources
    import shutil

    console = specify_cli.console
    project_path = Path.cwd()

    # Determine command directory based on AI assistant
    cmd_dirs = {
        "claude": ".claude/commands",
        "gemini": ".gemini/commands",
        "copilot": ".github/agents",
        "cursor-agent": ".cursor/commands",
        "qwen": ".qwen/commands",
        "opencode": ".opencode/command",
        "windsurf": ".windsurf/workflows",
        "codex": ".codex/prompts",
        "kilocode": ".kilocode/workflows",
        "auggie": ".augment/commands",
        "roo": ".roo/commands",
        "codebuddy": ".codebuddy/commands",
        "amp": ".agents/commands",
        "shai": ".shai/commands",
        "q": ".amazonq/prompts",
        "bob": ".bob/commands",
        "qoder": ".qoder/commands",
    }

    if ai_assistant not in cmd_dirs:
        console.print(f"[red]Unknown AI assistant: {ai_assistant}[/red]")
        console.print(f"Supported: {', '.join(cmd_dirs.keys())}")
        raise typer.Exit(1)

    cmd_dir = project_path / cmd_dirs[ai_assistant]
    cmd_dir.mkdir(parents=True, exist_ok=True)

    # Determine file extension based on agent
    ext = "md"
    if ai_assistant in ("gemini", "qwen"):
        ext = "toml"
    elif ai_assistant == "copilot":
        ext = "agent.md"

    console.print(f"[bold cyan]Installing jcttech commands for {ai_assistant}...[/bold cyan]")

    # Try to find bundled templates
    try:
        # For installed package, use importlib.resources
        try:
            import jcttech.templates.commands as templates_pkg
            templates_path = Path(importlib.resources.files(templates_pkg))
        except (ImportError, TypeError):
            # Fallback: look in package directory
            jcttech_pkg = Path(__file__).parent
            templates_path = jcttech_pkg / "templates" / "commands"

        if not templates_path.exists():
            # Development mode: use repo templates directly
            repo_root = project_path
            # Try to find repo root by looking for pyproject.toml
            for parent in [project_path] + list(project_path.parents):
                if (parent / "pyproject.toml").exists() and (parent / "templates" / "jcttech" / "commands").exists():
                    templates_path = parent / "templates" / "jcttech" / "commands"
                    break

        if not templates_path.exists():
            console.print("[red]Could not find bundled jcttech command templates.[/red]")
            console.print("Try reinstalling: uv tool install specify-cli --force --from /path/to/spec-kit")
            raise typer.Exit(1)

        installed = 0
        skipped = 0

        for template_file in templates_path.glob("*.md"):
            name = template_file.stem

            # Skip CLAUDE.md marker files
            if name.upper() == "CLAUDE":
                continue

            output_name = f"jcttech.{name}.{ext}"
            output_path = cmd_dir / output_name

            if output_path.exists() and not force:
                if debug:
                    console.print(f"  [dim]Skipping {output_name} (exists)[/dim]")
                skipped += 1
                continue

            # Read and process template
            content = template_file.read_text()

            # For TOML format (gemini, qwen), wrap in TOML structure
            if ext == "toml":
                # Extract description from frontmatter
                import re
                desc_match = re.search(r'^description:\s*(.+)$', content, re.MULTILINE)
                description = desc_match.group(1).strip() if desc_match else name

                # Escape backslashes for TOML
                content = content.replace('\\', '\\\\')

                content = f'description = "{description}"\n\nprompt = """\n{content}\n"""'

            # Replace {ARGS} placeholder
            arg_format = "{{args}}" if ai_assistant in ("gemini", "qwen") else "$ARGUMENTS"
            content = content.replace("{ARGS}", arg_format)

            # Rewrite paths for .specify structure
            content = content.replace("templates/", ".specify/templates/")
            content = content.replace("scripts/", ".specify/scripts/")
            content = content.replace("memory/", ".specify/memory/")

            output_path.write_text(content)
            installed += 1
            if debug:
                console.print(f"  [green]Installed {output_name}[/green]")

        console.print()
        console.print(f"[green]Installed {installed} command(s) to {cmd_dir}[/green]")
        if skipped:
            console.print(f"[dim]Skipped {skipped} existing command(s) (use --force to overwrite)[/dim]")

        # List installed commands
        console.print()
        console.print("[bold]Available jcttech commands:[/bold]")
        for cmd_file in sorted(cmd_dir.glob("jcttech.*")):
            cmd_name = cmd_file.stem.replace(".", " → /")
            console.print(f"  /{cmd_file.stem.replace('.', '.')}")

    except Exception as e:
        console.print(f"[red]Error installing commands: {e}[/red]")
        if debug:
            import traceback
            console.print(traceback.format_exc())
        raise typer.Exit(1)


@jcttech_app.command()
def check():
    """Check that all required tools are installed."""
    specify_cli.check()


@jcttech_app.command()
def version():
    """Show version information."""
    specify_cli.version()


def main():
    """JCT Tech fork entry point."""
    jcttech_app()


if __name__ == "__main__":
    main()
