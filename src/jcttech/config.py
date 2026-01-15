"""Configuration loading for JCT Tech fork extensions."""

from pathlib import Path
from typing import Any

import yaml


# Default configuration values
DEFAULT_CONFIG = {
    "org_templates": {
        "source": "jcttech/.github",
        "template_path": ".github/ISSUE_TEMPLATE",
        "include_pr_template": True,
        "enabled": True,
    },
    "github_mcp": {
        "use_org_templates": True,
    },
    "claude_settings": {
        "enable_claude_mem": True,
        "enable_github_mcp": True,
    },
    "fork": {
        "upstream_tag": None,
        "fork_tag": None,
    },
    # Issue tracking configuration
    "issue_tracking": {
        "enabled": True,
        "auto_sync": True,
        "cache_issues": True,
        "cache_closed_days": 7,
    },
    # Draft management configuration
    "drafts": {
        "auto_validate": True,
        "require_parent": True,
    },
    # Documentation paths and behavior
    "docs": {
        "path": ".docs",
        "constitution": ".docs/constitution.md",
        "architecture_md": ".docs/architecture.md",
        "architecture_diagram": ".docs/architecture.excalidraw",
        "decisions": ".docs/decisions.md",
        "auto_update_on_plan": True,
        "auto_update_on_implement": True,
    },
}


def deep_merge(base: dict, override: dict) -> dict:
    """Deep merge two dictionaries, with override taking precedence."""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def load_config(project_path: Path) -> dict[str, Any]:
    """Load configuration from .specify/config.yml with defaults.

    Args:
        project_path: Root path of the project

    Returns:
        Configuration dictionary with defaults applied
    """
    config_path = project_path / ".specify" / "config.yml"

    if config_path.exists():
        try:
            with open(config_path, "r") as f:
                user_config = yaml.safe_load(f) or {}
            return deep_merge(DEFAULT_CONFIG, user_config)
        except (yaml.YAMLError, OSError) as e:
            # Log warning but continue with defaults
            print(f"Warning: Could not load config from {config_path}: {e}")
            return DEFAULT_CONFIG.copy()

    return DEFAULT_CONFIG.copy()


def get_org_template_source(config: dict) -> str | None:
    """Extract org template source from config.

    Returns:
        Repository in "owner/repo" format, or None if disabled
    """
    org_config = config.get("org_templates", {})
    if not org_config.get("enabled", True):
        return None
    return org_config.get("source")


def get_template_path(config: dict) -> str:
    """Get the path within the source repo where templates are stored."""
    return config.get("org_templates", {}).get("template_path", ".github/ISSUE_TEMPLATE")


def should_include_pr_template(config: dict) -> bool:
    """Check if PR template should be fetched."""
    return config.get("org_templates", {}).get("include_pr_template", True)


def is_issue_tracking_enabled(config: dict) -> bool:
    """Check if issue tracking is enabled."""
    return config.get("issue_tracking", {}).get("enabled", True)


def get_docs_path(config: dict) -> str:
    """Get the documentation folder path."""
    return config.get("docs", {}).get("path", ".docs")


def should_auto_update_docs(config: dict, phase: str) -> bool:
    """Check if docs should auto-update for a given phase.

    Args:
        config: Configuration dict
        phase: Either "plan" or "implement"

    Returns:
        True if auto-update is enabled for this phase
    """
    docs_config = config.get("docs", {})
    if phase == "plan":
        return docs_config.get("auto_update_on_plan", True)
    elif phase == "implement":
        return docs_config.get("auto_update_on_implement", True)
    return False


def should_require_parent(config: dict) -> bool:
    """Check if drafts require a parent issue."""
    return config.get("drafts", {}).get("require_parent", True)
