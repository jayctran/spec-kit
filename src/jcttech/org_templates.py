"""Organization template fetching from GitHub repositories."""

import json
from pathlib import Path
from typing import Any

import httpx
import yaml

from jcttech.config import (
    get_org_template_source,
    get_template_path,
    load_config,
    should_include_pr_template,
)


def _github_auth_headers(github_token: str | None = None) -> dict:
    """Return Authorization header dict only when a non-empty token exists."""
    if github_token:
        return {"Authorization": f"Bearer {github_token}"}
    return {}


def fetch_org_templates(
    org_repo: str,
    dest_dir: Path,
    *,
    template_path: str = ".github/ISSUE_TEMPLATE",
    include_pr_template: bool = True,
    client: httpx.Client | None = None,
    github_token: str | None = None,
    console: Any | None = None,
) -> dict:
    """Fetch organization GitHub issue templates from a repository.

    Args:
        org_repo: Repository in "owner/repo" format (e.g., "jcttech/.github")
        dest_dir: Destination directory for templates (e.g., .specify/org-templates/)
        template_path: Path within the source repo to fetch templates from
        include_pr_template: Whether to also fetch PR template
        client: Optional httpx client (creates one if not provided)
        github_token: Optional GitHub token for authentication
        console: Optional Rich console for output

    Returns:
        Dict with fetched template metadata:
        {
            "source_repo": "jcttech/.github",
            "fetched_files": ["epic.yml", "spec.yml", ...],
            "errors": []
        }
    """
    result = {
        "source_repo": org_repo,
        "fetched_files": [],
        "errors": [],
    }

    # Create destination directory
    dest_dir.mkdir(parents=True, exist_ok=True)

    # Use provided client or create temporary one
    own_client = client is None
    if own_client:
        client = httpx.Client()

    try:
        headers = _github_auth_headers(github_token)
        headers["Accept"] = "application/vnd.github.v3+json"

        # Fetch directory listing from GitHub Contents API
        api_url = f"https://api.github.com/repos/{org_repo}/contents/{template_path}"

        if console:
            console.print(f"[dim]Fetching templates from {org_repo}...[/dim]")

        response = client.get(api_url, headers=headers, timeout=30)

        if response.status_code == 404:
            result["errors"].append(f"Template path not found: {template_path}")
            return result

        if response.status_code == 403:
            result["errors"].append("GitHub API rate limit exceeded. Try using --github-token")
            return result

        if response.status_code != 200:
            result["errors"].append(f"GitHub API error: {response.status_code}")
            return result

        contents = response.json()

        # Handle case where path is a single file vs directory
        if isinstance(contents, dict):
            contents = [contents]

        # Fetch each YAML template file
        for item in contents:
            if item.get("type") != "file":
                continue

            name = item.get("name", "")
            if not name.endswith((".yml", ".yaml", ".md")):
                continue

            download_url = item.get("download_url")
            if not download_url:
                continue

            try:
                file_response = client.get(download_url, headers=headers, timeout=30)
                if file_response.status_code == 200:
                    dest_file = dest_dir / name
                    dest_file.write_text(file_response.text)
                    result["fetched_files"].append(name)
                    if console:
                        console.print(f"  [green]✓[/green] {name}")
                else:
                    result["errors"].append(f"Failed to download {name}: {file_response.status_code}")
            except Exception as e:
                result["errors"].append(f"Error downloading {name}: {e}")

        # Optionally fetch PR template
        if include_pr_template:
            pr_template_paths = [
                ".github/pull_request_template.md",
                ".github/PULL_REQUEST_TEMPLATE.md",
                "pull_request_template.md",
            ]

            for pr_path in pr_template_paths:
                pr_url = f"https://api.github.com/repos/{org_repo}/contents/{pr_path}"
                try:
                    pr_response = client.get(pr_url, headers=headers, timeout=30)
                    if pr_response.status_code == 200:
                        pr_data = pr_response.json()
                        download_url = pr_data.get("download_url")
                        if download_url:
                            content_response = client.get(download_url, timeout=30)
                            if content_response.status_code == 200:
                                dest_file = dest_dir / "pull_request_template.md"
                                dest_file.write_text(content_response.text)
                                result["fetched_files"].append("pull_request_template.md")
                                if console:
                                    console.print("  [green]✓[/green] pull_request_template.md")
                                break
                except Exception:
                    continue

        # Write cache manifest
        manifest = {
            "source_repo": org_repo,
            "template_path": template_path,
            "files": result["fetched_files"],
        }
        manifest_path = dest_dir / ".cache-manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2))

    finally:
        if own_client:
            client.close()

    return result


def parse_issue_template(template_path: Path) -> dict:
    """Parse a GitHub issue template YAML into field schema.

    Args:
        template_path: Path to the .yml template file

    Returns:
        Dict with parsed template structure:
        {
            "name": "Spec",
            "description": "Technical specification",
            "title_prefix": "[Spec] ",
            "labels": ["type:spec"],
            "fields": [
                {"id": "overview", "type": "textarea", "label": "Overview", "required": True},
                ...
            ]
        }
    """
    result = {
        "name": "",
        "description": "",
        "title_prefix": "",
        "labels": [],
        "fields": [],
    }

    try:
        with open(template_path) as f:
            template = yaml.safe_load(f)

        if not template:
            return result

        result["name"] = template.get("name", "")
        result["description"] = template.get("description", "")

        # Extract title prefix from title field
        title = template.get("title", "")
        if title:
            result["title_prefix"] = title

        # Extract labels
        labels = template.get("labels", [])
        if isinstance(labels, list):
            result["labels"] = labels
        elif isinstance(labels, str):
            result["labels"] = [labels]

        # Parse body fields
        body = template.get("body", [])
        for item in body:
            if not isinstance(item, dict):
                continue

            field_type = item.get("type", "")
            field_id = item.get("id", "")
            attributes = item.get("attributes", {})
            validations = item.get("validations", {})

            if field_type in ("markdown",):
                # Skip markdown sections (documentation only)
                continue

            field = {
                "id": field_id,
                "type": field_type,
                "label": attributes.get("label", ""),
                "description": attributes.get("description", ""),
                "placeholder": attributes.get("placeholder", ""),
                "required": validations.get("required", False),
            }

            # Handle dropdown options
            if field_type == "dropdown":
                field["options"] = attributes.get("options", [])
                field["multiple"] = attributes.get("multiple", False)

            # Handle checkboxes
            if field_type == "checkboxes":
                field["options"] = [
                    {"label": opt.get("label", ""), "required": opt.get("required", False)}
                    for opt in attributes.get("options", [])
                ]

            result["fields"].append(field)

    except (yaml.YAMLError, OSError, KeyError) as e:
        result["parse_error"] = str(e)

    return result


def fetch_org_templates_if_configured(
    project_path: Path,
    *,
    client: httpx.Client | None = None,
    github_token: str | None = None,
    console: Any | None = None,
) -> dict | None:
    """Fetch org templates if configured in the project.

    This is the main entry point called by the wrapper after init completes.

    Args:
        project_path: Root path of the initialized project
        client: Optional httpx client
        github_token: Optional GitHub token
        console: Optional Rich console for output

    Returns:
        Fetch result dict, or None if not configured
    """
    config = load_config(project_path)
    source = get_org_template_source(config)

    if not source:
        return None

    dest_dir = project_path / ".specify" / "org-templates"
    template_path = get_template_path(config)
    include_pr = should_include_pr_template(config)

    return fetch_org_templates(
        source,
        dest_dir,
        template_path=template_path,
        include_pr_template=include_pr,
        client=client,
        github_token=github_token,
        console=console,
    )


def get_template_for_issue_type(project_path: Path, issue_type: str) -> dict | None:
    """Get parsed template for a specific issue type.

    Args:
        project_path: Root path of the project
        issue_type: One of "epic", "spec", "story", "task", "bug"

    Returns:
        Parsed template dict, or None if not found
    """
    templates_dir = project_path / ".specify" / "org-templates"

    # Map issue type to potential file names
    type_to_files = {
        "epic": ["epic.yml", "epic.yaml"],
        "spec": ["spec.yml", "spec.yaml", "specification.yml"],
        "story": ["story.yml", "story.yaml", "user-story.yml"],
        "task": ["task.yml", "task.yaml"],
        "bug": ["bug.yml", "bug.yaml", "bug-report.yml"],
    }

    potential_files = type_to_files.get(issue_type.lower(), [f"{issue_type}.yml"])

    for filename in potential_files:
        template_path = templates_dir / filename
        if template_path.exists():
            return parse_issue_template(template_path)

    return None
