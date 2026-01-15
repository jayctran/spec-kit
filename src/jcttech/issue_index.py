"""Issue index management for JCT Tech issue-centric workflow.

This module provides functionality for:
- Generating index.md from GitHub issues
- Parsing and updating the issue hierarchy
- Managing issue cache for offline reference
- Tracking drafts pending push
"""

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml


# Issue types in hierarchy order
ISSUE_TYPES = ["epic", "spec", "story", "task", "bug"]


def get_index_path(project_path: Path) -> Path:
    """Get the path to the issue index file."""
    return project_path / ".specify" / "issues" / "index.md"


def get_cache_path(project_path: Path) -> Path:
    """Get the path to the issue cache directory."""
    return project_path / ".specify" / "issues" / "cache"


def get_drafts_path(project_path: Path) -> Path:
    """Get the path to the drafts directory."""
    return project_path / ".specify" / "drafts"


def initialize_index_structure(project_path: Path) -> dict[str, Path]:
    """Initialize the issue tracking directory structure.

    Creates:
    - .specify/issues/index.md
    - .specify/issues/cache/
    - .specify/drafts/spec/
    - .specify/drafts/plan/

    Returns:
        Dict with paths created
    """
    paths_created = {}

    # Create issues directory
    issues_dir = project_path / ".specify" / "issues"
    issues_dir.mkdir(parents=True, exist_ok=True)
    paths_created["issues_dir"] = issues_dir

    # Create cache directory
    cache_dir = issues_dir / "cache"
    cache_dir.mkdir(exist_ok=True)
    paths_created["cache_dir"] = cache_dir

    # Create drafts directories
    drafts_dir = project_path / ".specify" / "drafts"
    (drafts_dir / "spec").mkdir(parents=True, exist_ok=True)
    (drafts_dir / "plan").mkdir(parents=True, exist_ok=True)
    paths_created["drafts_dir"] = drafts_dir

    # Create initial index.md if it doesn't exist
    index_path = issues_dir / "index.md"
    if not index_path.exists():
        index_path.write_text(generate_empty_index())
        paths_created["index_md"] = index_path

    return paths_created


def generate_empty_index() -> str:
    """Generate an empty index.md template."""
    now = datetime.now(timezone.utc).isoformat()
    return f"""# Issue Index

> Last synced: Never
> Repository: [Not configured]

## Hierarchy

_No issues tracked yet. Use `/jcttech.epic` to create your first epic._

---

## Drafts (Not Yet Pushed)

_No drafts yet. Use `/jcttech.specify` to create a spec draft._

---

## Metadata
```yaml
sync_version: 1
last_full_sync: null
issues_cached: 0
drafts_pending: 0
created_at: "{now}"
```
"""


def parse_index_metadata(index_content: str) -> dict[str, Any]:
    """Parse metadata from index.md content.

    Args:
        index_content: Full content of index.md

    Returns:
        Parsed metadata dict
    """
    # Extract YAML block from metadata section
    match = re.search(r"## Metadata\s*```yaml\s*(.*?)\s*```", index_content, re.DOTALL)
    if match:
        try:
            return yaml.safe_load(match.group(1)) or {}
        except yaml.YAMLError:
            pass
    return {}


def update_index_metadata(
    index_content: str,
    updates: dict[str, Any],
) -> str:
    """Update metadata in index.md content.

    Args:
        index_content: Current index content
        updates: Metadata fields to update

    Returns:
        Updated index content
    """
    # Parse existing metadata
    metadata = parse_index_metadata(index_content)
    metadata.update(updates)

    # Generate new YAML block
    yaml_content = yaml.dump(metadata, default_flow_style=False).strip()

    # Replace in content
    pattern = r"(## Metadata\s*```yaml\s*)(.*?)(\s*```)"

    def replacer(m):
        return f"{m.group(1)}{yaml_content}{m.group(3)}"

    return re.sub(pattern, replacer, index_content, flags=re.DOTALL)


def build_hierarchy_from_issues(issues: list[dict]) -> dict[str, Any]:
    """Build hierarchical structure from flat issue list.

    Args:
        issues: List of issue dicts with number, title, labels, body, state

    Returns:
        Nested hierarchy dict: {epics: [{..., specs: [{..., stories: [...]}]}]}
    """
    hierarchy = {"epics": []}
    issue_map = {}

    # First pass: categorize issues by type
    for issue in issues:
        issue_type = _detect_issue_type(issue)
        issue["_type"] = issue_type
        issue["_children"] = []
        issue_map[issue["number"]] = issue

    # Second pass: build parent-child relationships
    for issue in issues:
        parent_num = _extract_parent_number(issue)
        if parent_num and parent_num in issue_map:
            issue_map[parent_num]["_children"].append(issue)
        elif issue["_type"] == "epic":
            hierarchy["epics"].append(issue)

    return hierarchy


def _detect_issue_type(issue: dict) -> str:
    """Detect issue type from labels or title prefix."""
    labels = [l.get("name", l) if isinstance(l, dict) else l for l in issue.get("labels", [])]

    # Check labels first
    for label in labels:
        label_lower = label.lower()
        if "epic" in label_lower or label_lower == "type:epic":
            return "epic"
        if "spec" in label_lower or label_lower == "type:spec":
            return "spec"
        if "story" in label_lower or label_lower == "type:story":
            return "story"
        if "task" in label_lower or label_lower == "type:task":
            return "task"
        if "bug" in label_lower or label_lower == "type:bug":
            return "bug"

    # Check title prefix
    title = issue.get("title", "").lower()
    if title.startswith("[epic]") or title.startswith("epic:"):
        return "epic"
    if title.startswith("[spec]") or title.startswith("spec:"):
        return "spec"
    if title.startswith("[story]") or title.startswith("story:"):
        return "story"
    if title.startswith("[task]") or title.startswith("task:"):
        return "task"
    if title.startswith("[bug]") or title.startswith("bug:"):
        return "bug"

    return "unknown"


def _extract_parent_number(issue: dict) -> int | None:
    """Extract parent issue number from issue body.

    Looks for patterns like:
    - Parent Epic: #123
    - Parent Spec: #456
    - Related Issue: #789
    """
    body = issue.get("body", "") or ""

    patterns = [
        r"Parent Epic:\s*#(\d+)",
        r"Parent Spec:\s*#(\d+)",
        r"Parent Story:\s*#(\d+)",
        r"Related Issue:\s*#(\d+)",
        r"Parent:\s*#(\d+)",
    ]

    for pattern in patterns:
        match = re.search(pattern, body, re.IGNORECASE)
        if match:
            return int(match.group(1))

    return None


def generate_index_markdown(
    hierarchy: dict[str, Any],
    repo_name: str,
    drafts: list[dict] | None = None,
) -> str:
    """Generate index.md content from hierarchy.

    Args:
        hierarchy: Nested issue hierarchy
        repo_name: Repository name (owner/repo format)
        drafts: Optional list of pending drafts

    Returns:
        Generated markdown content
    """
    now = datetime.now(timezone.utc).isoformat()
    lines = [
        "# Issue Index",
        "",
        f"> Last synced: {now}",
        f"> Repository: {repo_name}",
        "",
        "## Hierarchy",
        "",
    ]

    epics = hierarchy.get("epics", [])
    if not epics:
        lines.append("_No issues tracked yet. Use `/jcttech.epic` to create your first epic._")
    else:
        for epic in epics:
            lines.extend(_format_epic(epic, repo_name))

    lines.extend([
        "",
        "---",
        "",
        "## Drafts (Not Yet Pushed)",
        "",
    ])

    if drafts:
        lines.append("| Draft | Type | Ready |")
        lines.append("|-------|------|-------|")
        for draft in drafts:
            ready = "yes" if draft.get("ready_to_push") else "no"
            lines.append(f"| [{draft['name']}](../drafts/{draft['type']}/{draft['name']}) | {draft['type']} | {ready} |")
    else:
        lines.append("_No drafts yet. Use `/jcttech.specify` to create a spec draft._")

    lines.extend([
        "",
        "---",
        "",
        "## Metadata",
        "```yaml",
        f"sync_version: 1",
        f"last_full_sync: \"{now}\"",
        f"issues_cached: {_count_issues(hierarchy)}",
        f"drafts_pending: {len(drafts) if drafts else 0}",
        "```",
    ])

    return "\n".join(lines)


def _format_epic(epic: dict, repo_name: str) -> list[str]:
    """Format an epic and its children for markdown."""
    lines = []
    number = epic["number"]
    title = epic.get("title", "Untitled")
    state = epic.get("state", "open")
    labels = ", ".join(
        l.get("name", l) if isinstance(l, dict) else l
        for l in epic.get("labels", [])
    )

    lines.append(f"### Epic: {title} (#{number})")
    lines.append(f"**Status**: {state} | **Labels**: {labels}")
    lines.append("")

    # Get specs from children
    specs = [c for c in epic.get("_children", []) if c.get("_type") == "spec"]
    if specs:
        lines.append("#### Specs")
        lines.append("| # | Title | Status | Stories | Progress |")
        lines.append("|---|-------|--------|---------|----------|")

        for spec in specs:
            spec_num = spec["number"]
            spec_title = spec.get("title", "Untitled")
            spec_state = spec.get("state", "open")
            stories = [c for c in spec.get("_children", []) if c.get("_type") == "story"]
            story_count = len(stories)
            completed = sum(1 for s in stories if s.get("state") == "closed")
            progress = f"{completed}/{story_count}" if story_count else "0/0"
            url = f"https://github.com/{repo_name}/issues/{spec_num}"

            lines.append(f"| #{spec_num} | [{spec_title}]({url}) | {spec_state} | {story_count} | {progress} |")

        # Add story details for each spec
        for spec in specs:
            stories = [c for c in spec.get("_children", []) if c.get("_type") == "story"]
            if stories:
                lines.extend(_format_spec_stories(spec, stories, repo_name))

    lines.append("")
    return lines


def _format_spec_stories(spec: dict, stories: list[dict], repo_name: str) -> list[str]:
    """Format stories under a spec."""
    lines = []
    spec_num = spec["number"]
    spec_title = spec.get("title", "Untitled")

    lines.append("")
    lines.append(f"##### Spec #{spec_num}: {spec_title}")
    lines.append("| # | Story | Status | Tasks | Assignee |")
    lines.append("|---|-------|--------|-------|----------|")

    for story in stories:
        story_num = story["number"]
        story_title = story.get("title", "Untitled")
        story_state = story.get("state", "open")
        url = f"https://github.com/{repo_name}/issues/{story_num}"

        # Count tasks from checkboxes in body
        task_count = _count_tasks_in_body(story.get("body", ""))
        assignee = _get_assignee(story)

        lines.append(f"| #{story_num} | [{story_title}]({url}) | {story_state} | {task_count} | {assignee} |")

    return lines


def _count_tasks_in_body(body: str) -> int:
    """Count task checkboxes in issue body."""
    if not body:
        return 0
    # Match both checked and unchecked task items
    return len(re.findall(r"^\s*-\s*\[[ xX]\]", body, re.MULTILINE))


def _get_assignee(issue: dict) -> str:
    """Get assignee display string."""
    assignees = issue.get("assignees", [])
    if assignees:
        names = [a.get("login", a) if isinstance(a, dict) else a for a in assignees[:2]]
        result = ", ".join(f"@{n}" for n in names)
        if len(assignees) > 2:
            result += f" +{len(assignees) - 2}"
        return result
    return "-"


def _count_issues(hierarchy: dict) -> int:
    """Count total issues in hierarchy."""
    count = 0
    for epic in hierarchy.get("epics", []):
        count += 1
        count += _count_children(epic)
    return count


def _count_children(issue: dict) -> int:
    """Recursively count child issues."""
    count = len(issue.get("_children", []))
    for child in issue.get("_children", []):
        count += _count_children(child)
    return count


def list_drafts(project_path: Path) -> list[dict]:
    """List all pending drafts.

    Returns:
        List of draft metadata dicts
    """
    drafts = []
    drafts_dir = get_drafts_path(project_path)

    for draft_type in ["spec", "plan"]:
        type_dir = drafts_dir / draft_type
        if not type_dir.exists():
            continue

        for draft_file in type_dir.glob("*.md"):
            draft_info = parse_draft_frontmatter(draft_file)
            draft_info["path"] = draft_file
            draft_info["name"] = draft_file.name
            draft_info["type"] = draft_type
            drafts.append(draft_info)

    return drafts


def parse_draft_frontmatter(draft_path: Path) -> dict[str, Any]:
    """Parse YAML frontmatter from a draft file.

    Args:
        draft_path: Path to the draft markdown file

    Returns:
        Parsed frontmatter dict
    """
    content = draft_path.read_text()

    # Extract YAML frontmatter
    match = re.match(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
    if match:
        try:
            return yaml.safe_load(match.group(1)) or {}
        except yaml.YAMLError:
            pass

    return {}


def cache_issue(project_path: Path, issue: dict) -> Path:
    """Cache an issue's content for offline reference.

    Args:
        project_path: Project root path
        issue: Issue dict to cache

    Returns:
        Path to cached file
    """
    cache_dir = get_cache_path(project_path)
    cache_dir.mkdir(parents=True, exist_ok=True)

    issue_type = issue.get("_type", "unknown")
    issue_num = issue["number"]

    cache_file = cache_dir / f"{issue_type}-{issue_num}.md"

    # Generate cached content
    content = [
        "---",
        f"issue_number: {issue_num}",
        f"type: {issue_type}",
        f"state: {issue.get('state', 'unknown')}",
        f"cached_at: \"{datetime.now(timezone.utc).isoformat()}\"",
        "---",
        "",
        f"# {issue.get('title', 'Untitled')}",
        "",
        issue.get("body", ""),
    ]

    cache_file.write_text("\n".join(content))
    return cache_file
