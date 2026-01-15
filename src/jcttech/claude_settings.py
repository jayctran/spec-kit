"""Configure Claude Code settings at project level.

This module handles setting up:
- claude-mem plugin for memory/context tracking
- GitHub MCP server for issue creation and repo interaction
"""

import json
import re
import subprocess
from pathlib import Path
from typing import Any


def parse_git_remote(project_path: Path) -> dict[str, str] | None:
    """Parse git remote origin URL to extract owner/repo.

    Supports formats:
    - https://github.com/owner/repo.git
    - https://github.com/owner/repo
    - git@github.com:owner/repo.git
    - git@github.com:owner/repo
    - ssh://git@github.com/owner/repo.git

    Args:
        project_path: Path to the project directory

    Returns:
        {"owner": "jcttech", "repo": "my-project"} or None if not parseable
    """
    try:
        result = subprocess.run(
            ["git", "config", "--get", "remote.origin.url"],
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=10,
        )

        if result.returncode != 0:
            return None

        url = result.stdout.strip()
        if not url:
            return None

        # Try different URL patterns
        patterns = [
            # HTTPS: https://github.com/owner/repo.git or https://github.com/owner/repo
            r"https?://(?:www\.)?github\.com/([^/]+)/([^/\.]+)(?:\.git)?/?$",
            # SSH: git@github.com:owner/repo.git or git@github.com:owner/repo
            r"git@github\.com:([^/]+)/([^/\.]+)(?:\.git)?$",
            # SSH with protocol: ssh://git@github.com/owner/repo.git
            r"ssh://git@github\.com/([^/]+)/([^/\.]+)(?:\.git)?$",
        ]

        for pattern in patterns:
            match = re.match(pattern, url)
            if match:
                return {"owner": match.group(1), "repo": match.group(2)}

        return None

    except (subprocess.TimeoutExpired, OSError, FileNotFoundError):
        return None


def _deep_merge(base: dict, override: dict) -> dict:
    """Deep merge two dictionaries, with override taking precedence."""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def configure_claude_settings(
    project_path: Path,
    *,
    enable_claude_mem: bool = True,
    enable_github_mcp: bool = True,
    console: Any | None = None,
) -> dict:
    """Configure .claude/settings.json with plugins and MCP servers.

    This function creates or updates the project-level Claude Code settings
    to enable the claude-mem plugin and GitHub MCP server.

    The GitHub MCP server uses HTTP-based auth via the GitHub Copilot API,
    which determines repo context at runtime from the working directory.

    Args:
        project_path: Path to the project directory
        enable_claude_mem: Whether to enable the claude-mem plugin
        enable_github_mcp: Whether to enable the GitHub MCP server
        console: Optional Rich console for output

    Returns:
        Dict with configuration results:
        {
            "settings_path": Path,
            "claude_mem_enabled": bool,
            "github_mcp_enabled": bool,
        }
    """
    result = {
        "settings_path": None,
        "claude_mem_enabled": False,
        "github_mcp_enabled": False,
    }

    # Create .claude directory if it doesn't exist
    claude_dir = project_path / ".claude"
    claude_dir.mkdir(parents=True, exist_ok=True)

    settings_path = claude_dir / "settings.json"
    result["settings_path"] = settings_path

    # Load existing settings if present
    existing_settings = {}
    if settings_path.exists():
        try:
            with open(settings_path) as f:
                existing_settings = json.load(f)
        except (json.JSONDecodeError, OSError):
            existing_settings = {}

    # Build new settings
    new_settings = {}

    # Configure claude-mem plugin
    if enable_claude_mem:
        new_settings.setdefault("enabledPlugins", {})
        new_settings["enabledPlugins"]["claude-mem@thedotmack"] = True
        result["claude_mem_enabled"] = True
        if console:
            console.print("  [green]✓[/green] claude-mem plugin enabled")

    # Configure GitHub MCP server (HTTP-based via GitHub Copilot API)
    if enable_github_mcp:
        new_settings.setdefault("mcpServers", {})
        new_settings["mcpServers"]["github"] = {
            "type": "http",
            "url": "https://api.githubcopilot.com/mcp/",
            "headers": {
                "Authorization": "Bearer ${GITHUB_PERSONAL_ACCESS_TOKEN}"
            },
        }

        # Add permissions for GitHub MCP
        new_settings.setdefault("permissions", {})
        new_settings["permissions"].setdefault("allow", [])
        if "mcp__github__*" not in new_settings["permissions"]["allow"]:
            new_settings["permissions"]["allow"].append("mcp__github__*")

        result["github_mcp_enabled"] = True
        if console:
            console.print("  [green]✓[/green] GitHub MCP server configured")

    # Merge with existing settings (new settings take precedence for conflicts)
    merged_settings = _deep_merge(existing_settings, new_settings)

    # Write the settings file
    try:
        with open(settings_path, "w") as f:
            json.dump(merged_settings, f, indent=2)
            f.write("\n")  # Trailing newline
    except OSError as e:
        if console:
            console.print(f"  [yellow]Warning: Could not write settings: {e}[/yellow]")
        return result

    return result


def configure_claude_settings_if_enabled(
    project_path: Path,
    *,
    config: dict | None = None,
    console: Any | None = None,
) -> dict | None:
    """Configure Claude settings based on project config.

    This is the main entry point called by the wrapper after init completes.
    It reads settings from .specify/config.yml.

    Args:
        project_path: Root path of the initialized project
        config: Optional pre-loaded config dict
        console: Optional Rich console for output

    Returns:
        Configuration result dict, or None if disabled
    """
    from jcttech.config import load_config

    if config is None:
        config = load_config(project_path)

    claude_config = config.get("claude_settings", {})

    # Check if either feature is enabled
    enable_claude_mem = claude_config.get("enable_claude_mem", True)
    enable_github_mcp = claude_config.get("enable_github_mcp", True)

    if not enable_claude_mem and not enable_github_mcp:
        return None

    return configure_claude_settings(
        project_path,
        enable_claude_mem=enable_claude_mem,
        enable_github_mcp=enable_github_mcp,
        console=console,
    )
