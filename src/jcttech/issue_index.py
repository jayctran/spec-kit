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
    return project_path / ".docs" / "issues-index.md"


def get_cache_path(project_path: Path) -> Path:
    """Get the path to the issue cache directory."""
    return project_path / ".specify" / "issues" / "cache"


def get_drafts_path(project_path: Path) -> Path:
    """Get the path to the drafts directory."""
    return project_path / ".specify" / "drafts"


def initialize_index_structure(project_path: Path) -> dict[str, Path]:
    """Initialize the issue tracking directory structure.

    Creates:
    - .docs/issues-index.md
    - .specify/issues/cache/
    - .specify/drafts/spec/
    - .specify/drafts/plan/

    Returns:
        Dict with paths created
    """
    paths_created = {}

    # Create .docs directory for index
    docs_dir = project_path / ".docs"
    docs_dir.mkdir(parents=True, exist_ok=True)
    paths_created["docs_dir"] = docs_dir

    # Create issues cache directory
    cache_dir = project_path / ".specify" / "issues" / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    paths_created["cache_dir"] = cache_dir

    # Create drafts directories
    drafts_dir = project_path / ".specify" / "drafts"
    (drafts_dir / "spec").mkdir(parents=True, exist_ok=True)
    (drafts_dir / "plan").mkdir(parents=True, exist_ok=True)
    paths_created["drafts_dir"] = drafts_dir

    # Create initial issues-index.md if it doesn't exist
    index_path = docs_dir / "issues-index.md"
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


# =============================================================================
# Analysis Support Functions
# =============================================================================

# Vague terms that should be quantified
VAGUE_TERMS = [
    "fast", "quick", "slow", "scalable", "secure", "robust", "intuitive",
    "flexible", "efficient", "reliable", "high-performance", "low-latency",
    "user-friendly", "easy", "simple", "complex", "many", "few", "large",
    "small", "often", "sometimes", "rarely", "soon", "later",
]

# Common term groups that might drift
TERM_GROUPS = [
    ["user", "account", "customer", "client", "member"],
    ["token", "jwt", "credential", "auth", "session"],
    ["api", "endpoint", "service", "route", "resource"],
    ["error", "exception", "failure", "fault"],
    ["create", "add", "new", "register"],
    ["delete", "remove", "destroy", "drop"],
]


def load_cached_issues(
    project_path: Path,
    issue_type: str | None = None,
) -> list[dict]:
    """Load issues from cache directory.

    Args:
        project_path: Project root path
        issue_type: Optional filter (epic, spec, story, task, bug)

    Returns:
        List of parsed issue dicts
    """
    cache_dir = get_cache_path(project_path)
    if not cache_dir.exists():
        return []

    issues = []
    pattern = f"{issue_type}-*.md" if issue_type else "*.md"

    for cache_file in cache_dir.glob(pattern):
        issue_data = parse_cached_issue(cache_file)
        if issue_data:
            issues.append(issue_data)

    return issues


def parse_cached_issue(cache_path: Path) -> dict[str, Any] | None:
    """Parse a cached issue file.

    Args:
        cache_path: Path to cached issue file

    Returns:
        Parsed issue dict or None
    """
    content = cache_path.read_text()

    # Extract frontmatter
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n?", content, re.DOTALL)
    if not match:
        return None

    try:
        frontmatter = yaml.safe_load(match.group(1)) or {}
    except yaml.YAMLError:
        return None

    body = content[match.end():]

    # Extract title from body
    title_match = re.match(r"#\s+(.+)", body)
    title = title_match.group(1).strip() if title_match else cache_path.stem

    return {
        "number": frontmatter.get("issue_number"),
        "type": frontmatter.get("type"),
        "state": frontmatter.get("state"),
        "cached_at": frontmatter.get("cached_at"),
        "title": title,
        "body": body,
        "path": cache_path,
    }


def extract_requirements_from_spec(issue_body: str) -> list[dict]:
    """Extract requirements from a spec issue body.

    Args:
        issue_body: The issue body markdown

    Returns:
        List of requirement dicts with id, text, type
    """
    requirements = []

    # Find Requirements section
    req_match = re.search(
        r"##\s*Requirements\s*\n(.*?)(?=\n##\s+[A-Z]|\Z)",
        issue_body,
        re.DOTALL | re.IGNORECASE
    )
    if not req_match:
        return requirements

    req_section = req_match.group(1)

    # Extract checkbox items
    for i, match in enumerate(re.finditer(r"^\s*-\s*\[[ xX]?\]\s*(.+)$", req_section, re.MULTILINE)):
        text = match.group(1).strip()
        # Determine type based on context
        req_type = "non-functional" if any(
            kw in text.lower()
            for kw in ["performance", "security", "scalab", "reliab", "latency"]
        ) else "functional"

        requirements.append({
            "id": f"REQ-{i+1:03d}",
            "text": text,
            "type": req_type,
        })

    return requirements


def extract_acceptance_criteria(issue_body: str) -> list[dict]:
    """Extract acceptance criteria from an issue body.

    Args:
        issue_body: The issue body markdown

    Returns:
        List of criteria dicts with id, text, verified
    """
    criteria = []

    # Find Acceptance Criteria section
    ac_match = re.search(
        r"##\s*Acceptance Criteria\s*\n(.*?)(?=\n##\s+[A-Z]|\Z)",
        issue_body,
        re.DOTALL | re.IGNORECASE
    )
    if not ac_match:
        return criteria

    ac_section = ac_match.group(1)

    # Extract checkbox items
    for i, match in enumerate(re.finditer(r"^\s*-\s*\[([ xX]?)\]\s*(.+)$", ac_section, re.MULTILINE)):
        verified = match.group(1).lower() == "x"
        text = match.group(2).strip()
        criteria.append({
            "id": f"AC-{i+1:03d}",
            "text": text,
            "verified": verified,
        })

    return criteria


def extract_tasks_from_story(issue_body: str) -> list[dict]:
    """Extract tasks from a story issue body.

    Args:
        issue_body: The issue body markdown

    Returns:
        List of task dicts with id, text, completed
    """
    tasks = []

    # Find Tasks section
    tasks_match = re.search(
        r"(?:\*\*Tasks\*\*|##\s*Tasks)\s*:?\s*\n(.*?)(?=\n\*\*|\n##\s+[A-Z]|\Z)",
        issue_body,
        re.DOTALL | re.IGNORECASE
    )
    if not tasks_match:
        # Try to find any checkbox list
        tasks_match = re.search(
            r"((?:^\s*-\s*\[[ xX]?\]\s*.+$\n?)+)",
            issue_body,
            re.MULTILINE
        )

    if not tasks_match:
        return tasks

    tasks_section = tasks_match.group(1)

    for i, match in enumerate(re.finditer(r"^\s*-\s*\[([ xX]?)\]\s*(.+)$", tasks_section, re.MULTILINE)):
        completed = match.group(1).lower() == "x"
        text = match.group(2).strip()
        tasks.append({
            "id": f"TASK-{i+1:03d}",
            "text": text,
            "completed": completed,
        })

    return tasks


def analyze_coverage(
    specs: list[dict],
    stories: list[dict],
) -> dict[str, Any]:
    """Analyze requirement coverage across specs and stories.

    Args:
        specs: List of spec issues
        stories: List of story issues

    Returns:
        Coverage analysis results
    """
    results = {
        "total_specs": len(specs),
        "total_stories": len(stories),
        "coverage_by_spec": {},
        "uncovered_requirements": [],
        "orphan_stories": [],
        "overall_coverage_percent": 0,
    }

    total_requirements = 0
    total_covered = 0

    for spec in specs:
        spec_num = spec["number"]
        body = spec.get("body", "")
        requirements = extract_requirements_from_spec(body)

        # Find stories linked to this spec
        linked_stories = []
        for story in stories:
            story_body = story.get("body", "")
            if (f"Parent Spec: #{spec_num}" in story_body or
                f"parent_spec: {spec_num}" in story_body or
                f"Spec #{spec_num}" in story_body):
                linked_stories.append(story)

        # Calculate coverage
        story_count = len(linked_stories)
        req_count = len(requirements)
        total_requirements += req_count

        # Simple coverage heuristic: stories should cover requirements
        # More stories = better coverage, up to the number of requirements
        covered = min(story_count, req_count)
        total_covered += covered

        coverage_percent = (covered / req_count * 100) if req_count > 0 else 100

        results["coverage_by_spec"][spec_num] = {
            "title": spec.get("title", "Untitled"),
            "requirements": req_count,
            "stories": story_count,
            "coverage_percent": round(coverage_percent, 1),
            "uncovered": req_count - covered,
        }

        # Track uncovered requirements
        if covered < req_count:
            for req in requirements[covered:]:
                results["uncovered_requirements"].append({
                    "spec": spec_num,
                    "requirement": req,
                })

    # Find orphan stories (not linked to any spec)
    for story in stories:
        story_body = story.get("body", "")
        has_parent = any(
            f"Parent Spec: #{spec['number']}" in story_body or
            f"parent_spec: {spec['number']}" in story_body
            for spec in specs
        )
        if not has_parent:
            results["orphan_stories"].append({
                "number": story["number"],
                "title": story.get("title", "Untitled"),
            })

    # Overall coverage
    if total_requirements > 0:
        results["overall_coverage_percent"] = round(
            total_covered / total_requirements * 100, 1
        )

    return results


def detect_terminology_drift(issues: list[dict]) -> list[dict]:
    """Detect terminology inconsistencies across issues.

    Args:
        issues: List of all issue dicts

    Returns:
        List of drift findings
    """
    findings = []
    all_text = " ".join(i.get("body", "").lower() for i in issues)

    for group in TERM_GROUPS:
        used_terms = [t for t in group if t in all_text]
        if len(used_terms) > 1:
            # Check if multiple terms from same group are used
            findings.append({
                "category": "terminology_drift",
                "severity": "MEDIUM",
                "terms": used_terms,
                "recommendation": f"Standardize on one of: {', '.join(used_terms)}",
            })

    return findings


def detect_vague_language(issues: list[dict]) -> list[dict]:
    """Detect vague language that should be quantified.

    Args:
        issues: List of all issue dicts

    Returns:
        List of vague language findings
    """
    findings = []

    for issue in issues:
        body = issue.get("body", "")
        body_lower = body.lower()
        issue_num = issue.get("number", "?")

        for term in VAGUE_TERMS:
            if term in body_lower:
                # Find context around term
                pattern = rf"[^.]*\b{re.escape(term)}\b[^.]*\."
                matches = re.findall(pattern, body, re.IGNORECASE)
                if matches:
                    findings.append({
                        "category": "vague_language",
                        "severity": "MEDIUM",
                        "issue": issue_num,
                        "term": term,
                        "context": matches[0][:100].strip(),
                        "recommendation": f"Quantify '{term}' with specific metrics",
                    })

    return findings


def detect_placeholders(issues: list[dict]) -> list[dict]:
    """Detect placeholder content that needs completion.

    Args:
        issues: List of all issue dicts

    Returns:
        List of placeholder findings
    """
    findings = []
    placeholder_patterns = [
        (r"\[NEEDS CLARIFICATION\]", "Explicit clarification marker"),
        (r"\[Requirement \d+\]", "Template placeholder requirement"),
        (r"\[Criterion \d+\]", "Template placeholder criterion"),
        (r"\[TODO[:\]]", "TODO marker"),
        (r"\?\?\?", "Unknown marker"),
        (r"\[TBD\]", "To be determined marker"),
    ]

    for issue in issues:
        body = issue.get("body", "")
        issue_num = issue.get("number", "?")

        for pattern, description in placeholder_patterns:
            if re.search(pattern, body, re.IGNORECASE):
                findings.append({
                    "category": "placeholder",
                    "severity": "HIGH",
                    "issue": issue_num,
                    "pattern": description,
                    "recommendation": f"Replace placeholder content in issue #{issue_num}",
                })

    return findings


def validate_hierarchy(issues: list[dict]) -> list[dict]:
    """Validate issue hierarchy integrity.

    Args:
        issues: List of all issue dicts

    Returns:
        List of hierarchy findings
    """
    findings = []
    issue_numbers = {i.get("number") for i in issues if i.get("number")}

    for issue in issues:
        body = issue.get("body", "")
        issue_type = issue.get("type", "unknown")
        issue_num = issue.get("number", "?")

        # Check for parent references
        parent_patterns = [
            (r"Parent Epic:\s*#(\d+)", "epic"),
            (r"Parent Spec:\s*#(\d+)", "spec"),
            (r"Parent Story:\s*#(\d+)", "story"),
        ]

        has_parent = False
        for pattern, parent_type in parent_patterns:
            match = re.search(pattern, body, re.IGNORECASE)
            if match:
                has_parent = True
                parent_num = int(match.group(1))
                if parent_num not in issue_numbers:
                    findings.append({
                        "category": "broken_reference",
                        "severity": "CRITICAL",
                        "issue": issue_num,
                        "parent": parent_num,
                        "recommendation": f"Parent #{parent_num} not found in cache - sync issues",
                    })

        # Specs should have parent epic
        if issue_type == "spec" and not has_parent:
            findings.append({
                "category": "orphan_issue",
                "severity": "HIGH",
                "issue": issue_num,
                "type": "spec",
                "recommendation": f"Spec #{issue_num} has no parent Epic - add parent reference",
            })

        # Stories should have parent spec
        if issue_type == "story" and not has_parent:
            findings.append({
                "category": "orphan_issue",
                "severity": "HIGH",
                "issue": issue_num,
                "type": "story",
                "recommendation": f"Story #{issue_num} has no parent Spec - add parent reference",
            })

    return findings


def generate_analysis_report(
    project_path: Path,
    scope: str | None = None,
) -> dict[str, Any]:
    """Generate a comprehensive analysis report.

    Args:
        project_path: Project root path
        scope: Optional scope filter (epic number, spec number, or None for all)

    Returns:
        Analysis report dict with findings and metrics
    """
    # Load all cached issues
    all_issues = load_cached_issues(project_path)
    if not all_issues:
        return {
            "error": "No cached issues found. Run /jcttech.sync first.",
            "findings": [],
            "metrics": {},
        }

    # Filter by scope if provided
    if scope:
        try:
            scope_num = int(scope.replace("#", ""))
            # Find the scope issue and its children
            scope_issue = next(
                (i for i in all_issues if i.get("number") == scope_num),
                None
            )
            if scope_issue:
                # For now, keep all issues (proper filtering would follow hierarchy)
                pass
        except ValueError:
            pass

    # Categorize issues
    epics = [i for i in all_issues if i.get("type") == "epic"]
    specs = [i for i in all_issues if i.get("type") == "spec"]
    stories = [i for i in all_issues if i.get("type") == "story"]
    tasks = [i for i in all_issues if i.get("type") == "task"]
    bugs = [i for i in all_issues if i.get("type") == "bug"]

    # Run all detection passes
    findings = []
    findings.extend(detect_terminology_drift(all_issues))
    findings.extend(detect_vague_language(all_issues))
    findings.extend(detect_placeholders(all_issues))
    findings.extend(validate_hierarchy(all_issues))

    # Analyze coverage
    coverage = analyze_coverage(specs, stories)

    # Add coverage findings
    for spec_num, cov_data in coverage["coverage_by_spec"].items():
        if cov_data["coverage_percent"] < 100:
            findings.append({
                "category": "coverage_gap",
                "severity": "HIGH" if cov_data["coverage_percent"] < 50 else "MEDIUM",
                "issue": spec_num,
                "coverage": cov_data["coverage_percent"],
                "recommendation": f"Spec #{spec_num} has {cov_data['uncovered']} uncovered requirements - create stories",
            })

    for orphan in coverage["orphan_stories"]:
        findings.append({
            "category": "orphan_story",
            "severity": "MEDIUM",
            "issue": orphan["number"],
            "recommendation": f"Story #{orphan['number']} is not linked to a Spec",
        })

    # Sort findings by severity
    severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
    findings.sort(key=lambda f: severity_order.get(f.get("severity", "LOW"), 4))

    # Calculate metrics
    metrics = {
        "total_issues": len(all_issues),
        "epics": len(epics),
        "specs": len(specs),
        "stories": len(stories),
        "tasks": len(tasks),
        "bugs": len(bugs),
        "overall_coverage": coverage["overall_coverage_percent"],
        "critical_findings": sum(1 for f in findings if f.get("severity") == "CRITICAL"),
        "high_findings": sum(1 for f in findings if f.get("severity") == "HIGH"),
        "medium_findings": sum(1 for f in findings if f.get("severity") == "MEDIUM"),
        "low_findings": sum(1 for f in findings if f.get("severity") == "LOW"),
    }

    return {
        "scope": scope or "all",
        "analyzed_at": datetime.now(timezone.utc).isoformat(),
        "findings": findings,
        "metrics": metrics,
        "coverage": coverage,
    }
