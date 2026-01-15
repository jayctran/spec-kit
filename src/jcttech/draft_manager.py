"""Draft management for JCT Tech issue-centric workflow.

This module provides functionality for:
- Creating new spec and plan drafts
- Validating drafts before push to GitHub
- Mapping draft content to GitHub issue templates
- Managing draft lifecycle (create, validate, push)
"""

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml


# Required sections for each draft type
REQUIRED_SECTIONS = {
    "spec": ["Overview", "Requirements", "Acceptance Criteria"],
    "plan": ["Implementation Approach", "Stories"],
}


def get_next_draft_number(project_path: Path, draft_type: str) -> int:
    """Get the next available draft number for a type.

    Args:
        project_path: Project root path
        draft_type: Type of draft (spec, plan)

    Returns:
        Next available draft number
    """
    drafts_dir = project_path / ".specify" / "drafts" / draft_type
    if not drafts_dir.exists():
        return 1

    highest = 0
    for draft_file in drafts_dir.glob("*.md"):
        match = re.match(r"^(\d+)-", draft_file.name)
        if match:
            num = int(match.group(1))
            if num > highest:
                highest = num

    return highest + 1


def generate_draft_id(draft_type: str, number: int, short_name: str) -> str:
    """Generate a unique draft ID.

    Args:
        draft_type: Type of draft (spec, plan)
        number: Draft number
        short_name: Short name slug

    Returns:
        Draft ID string
    """
    return f"{draft_type}-{number:03d}-{short_name}"


def create_short_name(title: str) -> str:
    """Create a short name slug from a title.

    Args:
        title: Human-readable title

    Returns:
        URL-safe short name
    """
    # Convert to lowercase
    slug = title.lower()
    # Replace non-alphanumeric with dashes
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    # Remove leading/trailing dashes
    slug = slug.strip("-")
    # Truncate to 50 chars
    slug = slug[:50]
    # Remove trailing dash if truncated mid-word
    slug = slug.rstrip("-")
    return slug


def create_spec_draft(
    project_path: Path,
    title: str,
    parent_epic: int | None = None,
    description: str | None = None,
) -> Path:
    """Create a new spec draft.

    Args:
        project_path: Project root path
        title: Spec title
        parent_epic: Parent epic issue number
        description: Optional initial description

    Returns:
        Path to created draft file
    """
    drafts_dir = project_path / ".specify" / "drafts" / "spec"
    drafts_dir.mkdir(parents=True, exist_ok=True)

    number = get_next_draft_number(project_path, "spec")
    short_name = create_short_name(title)
    draft_id = generate_draft_id("spec", number, short_name)

    now = datetime.now(timezone.utc).isoformat()
    filename = f"{number:03d}-{short_name}.md"

    content = f"""---
draft_id: {draft_id}
type: spec
title: "{title}"
created: "{now}"
modified: "{now}"
status: draft
ready_to_push: false
parent_epic: {parent_epic if parent_epic else "null"}
validation:
  passed: false
  issues: []
---

# Spec: {title}

## Overview

{description or "[Describe the feature or change being specified...]"}

## Requirements

### Functional Requirements

- [ ] [Requirement 1]
- [ ] [Requirement 2]

### Non-Functional Requirements

- [ ] [Performance requirement]
- [ ] [Security requirement]

## Acceptance Criteria

- [ ] [Criterion 1]
- [ ] [Criterion 2]
- [ ] [Criterion 3]

## Technical Notes

[Any technical considerations, constraints, or dependencies...]

## Open Questions

- [ ] [Question that needs clarification]
"""

    draft_path = drafts_dir / filename
    draft_path.write_text(content)
    return draft_path


def create_plan_draft(
    project_path: Path,
    spec_number: int,
    spec_title: str,
) -> Path:
    """Create a new plan draft linked to a spec.

    Args:
        project_path: Project root path
        spec_number: Parent spec issue number
        spec_title: Parent spec title

    Returns:
        Path to created draft file
    """
    drafts_dir = project_path / ".specify" / "drafts" / "plan"
    drafts_dir.mkdir(parents=True, exist_ok=True)

    number = get_next_draft_number(project_path, "plan")
    short_name = create_short_name(spec_title)
    draft_id = generate_draft_id("plan", number, short_name)

    now = datetime.now(timezone.utc).isoformat()
    filename = f"{number:03d}-{short_name}-plan.md"

    content = f"""---
draft_id: {draft_id}
type: plan
title: "Plan: {spec_title}"
created: "{now}"
modified: "{now}"
status: draft
parent_spec: {spec_number}
stories_generated: false
---

# Implementation Plan: {spec_title}

**Parent Spec**: #{spec_number}

## Implementation Approach

[Describe the overall approach to implementing this spec...]

## Technical Decisions

### Technology Stack

- [Framework/library choice]
- [Database choice if applicable]

### Architecture

[High-level architecture decisions...]

## Stories

The following user stories break down this spec into implementable units:

### Story 1: [Story Title]

**User Story**: As a [user type], I want [action] so that [benefit].

**Description**: [More detailed description...]

**Tasks**:
- [ ] [Task 1]
- [ ] [Task 2]
- [ ] [Task 3]

**Acceptance Criteria**:
- [ ] [Criterion 1]
- [ ] [Criterion 2]

---

### Story 2: [Story Title]

**User Story**: As a [user type], I want [action] so that [benefit].

**Description**: [More detailed description...]

**Tasks**:
- [ ] [Task 1]
- [ ] [Task 2]

**Acceptance Criteria**:
- [ ] [Criterion 1]
- [ ] [Criterion 2]

## Dependencies

- [External dependency 1]
- [Internal dependency 1]

## Risks

- [Risk 1]: [Mitigation strategy]
- [Risk 2]: [Mitigation strategy]
"""

    draft_path = drafts_dir / filename
    draft_path.write_text(content)
    return draft_path


def parse_draft(draft_path: Path) -> dict[str, Any]:
    """Parse a draft file into structured data.

    Args:
        draft_path: Path to draft markdown file

    Returns:
        Dict with frontmatter and body content
    """
    content = draft_path.read_text()

    # Extract frontmatter
    frontmatter = {}
    body = content

    match = re.match(r"^---\s*\n(.*?)\n---\s*\n", content, re.DOTALL)
    if match:
        try:
            frontmatter = yaml.safe_load(match.group(1)) or {}
        except yaml.YAMLError:
            pass
        body = content[match.end():]

    # Extract sections
    sections = {}
    current_section = None
    current_content = []

    for line in body.split("\n"):
        if line.startswith("## "):
            if current_section:
                sections[current_section] = "\n".join(current_content).strip()
            current_section = line[3:].strip()
            current_content = []
        elif current_section:
            current_content.append(line)

    if current_section:
        sections[current_section] = "\n".join(current_content).strip()

    return {
        "frontmatter": frontmatter,
        "body": body,
        "sections": sections,
        "path": draft_path,
    }


def validate_draft(draft_path: Path) -> dict[str, Any]:
    """Validate a draft for completeness.

    Args:
        draft_path: Path to draft file

    Returns:
        Validation result with passed flag and issues list
    """
    parsed = parse_draft(draft_path)
    frontmatter = parsed["frontmatter"]
    sections = parsed["sections"]
    issues = []

    draft_type = frontmatter.get("type", "spec")
    required = REQUIRED_SECTIONS.get(draft_type, [])

    # Check required sections exist
    for section in required:
        if section not in sections:
            issues.append(f"Missing required section: {section}")
        elif not sections[section] or sections[section].startswith("["):
            issues.append(f"Section '{section}' needs content")

    # Check for placeholder markers
    body = parsed["body"]
    if "[NEEDS CLARIFICATION]" in body:
        issues.append("Contains [NEEDS CLARIFICATION] markers - run /jcttech.clarify")
    if "[Requirement" in body or "[Criterion" in body:
        issues.append("Contains placeholder requirements or criteria")

    # Check parent linkage for specs
    if draft_type == "spec":
        parent_epic = frontmatter.get("parent_epic")
        if not parent_epic:
            issues.append("No parent Epic specified - select or create an Epic first")

    # Update frontmatter with validation result
    result = {
        "passed": len(issues) == 0,
        "issues": issues,
        "last_check": datetime.now(timezone.utc).isoformat(),
    }

    return result


def update_draft_validation(draft_path: Path, validation_result: dict) -> None:
    """Update draft frontmatter with validation result.

    Args:
        draft_path: Path to draft file
        validation_result: Validation result dict
    """
    content = draft_path.read_text()

    # Parse frontmatter
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n", content, re.DOTALL)
    if not match:
        return

    try:
        frontmatter = yaml.safe_load(match.group(1)) or {}
    except yaml.YAMLError:
        return

    # Update validation fields
    frontmatter["validation"] = validation_result
    frontmatter["ready_to_push"] = validation_result["passed"]
    frontmatter["modified"] = datetime.now(timezone.utc).isoformat()

    # Regenerate frontmatter
    new_frontmatter = yaml.dump(frontmatter, default_flow_style=False)
    body = content[match.end():]

    new_content = f"---\n{new_frontmatter}---\n{body}"
    draft_path.write_text(new_content)


def map_draft_to_issue_fields(draft_path: Path) -> dict[str, Any]:
    """Map draft content to GitHub issue template fields.

    Args:
        draft_path: Path to draft file

    Returns:
        Dict with title, body, labels, and field mappings
    """
    parsed = parse_draft(draft_path)
    frontmatter = parsed["frontmatter"]
    sections = parsed["sections"]
    draft_type = frontmatter.get("type", "spec")

    # Build title
    title_prefix = draft_type.capitalize()
    title_text = frontmatter.get("title", draft_path.stem)
    if not title_text.lower().startswith(draft_type):
        title = f"[{title_prefix}] {title_text}"
    else:
        title = f"[{title_prefix}] {title_text.split(':', 1)[-1].strip()}"

    # Build body from sections
    body_parts = []

    if draft_type == "spec":
        # Map spec sections
        if "Overview" in sections:
            body_parts.append(f"## Overview\n\n{sections['Overview']}")

        if "Requirements" in sections:
            body_parts.append(f"## Requirements\n\n{sections['Requirements']}")

        if "Acceptance Criteria" in sections:
            body_parts.append(f"## Acceptance Criteria\n\n{sections['Acceptance Criteria']}")

        if "Technical Notes" in sections:
            body_parts.append(f"## Technical Notes\n\n{sections['Technical Notes']}")

        # Add parent reference
        parent_epic = frontmatter.get("parent_epic")
        if parent_epic:
            body_parts.insert(0, f"**Parent Epic**: #{parent_epic}\n")

    elif draft_type == "plan":
        # Plan type - include stories breakdown
        if "Implementation Approach" in sections:
            body_parts.append(f"## Implementation Approach\n\n{sections['Implementation Approach']}")

        if "Technical Decisions" in sections:
            body_parts.append(f"## Technical Decisions\n\n{sections['Technical Decisions']}")

        parent_spec = frontmatter.get("parent_spec")
        if parent_spec:
            body_parts.insert(0, f"**Parent Spec**: #{parent_spec}\n")

    # Determine labels
    labels = [f"type:{draft_type}"]
    if draft_type == "spec":
        labels.append("status:draft")

    return {
        "title": title,
        "body": "\n\n".join(body_parts),
        "labels": labels,
        "draft_type": draft_type,
        "frontmatter": frontmatter,
    }


def extract_stories_from_plan(draft_path: Path) -> list[dict]:
    """Extract story definitions from a plan draft.

    Args:
        draft_path: Path to plan draft

    Returns:
        List of story dicts with title, user_story, tasks, criteria
    """
    parsed = parse_draft(draft_path)
    body = parsed["body"]
    stories = []

    # Find all story sections (### Story N: Title)
    story_pattern = r"###\s+Story\s+\d+:\s+(.+?)(?=\n###\s+Story|\n##\s+[A-Z]|$)"
    story_matches = re.finditer(story_pattern, body, re.DOTALL)

    for match in story_matches:
        story_content = match.group(0)
        title_match = re.match(r"###\s+Story\s+\d+:\s+(.+)", story_content.split("\n")[0])
        title = title_match.group(1).strip() if title_match else "Untitled Story"

        # Extract user story
        user_story_match = re.search(r"\*\*User Story\*\*:\s*(.+)", story_content)
        user_story = user_story_match.group(1).strip() if user_story_match else ""

        # Extract description
        desc_match = re.search(r"\*\*Description\*\*:\s*(.+?)(?=\*\*Tasks\*\*|\*\*Acceptance)", story_content, re.DOTALL)
        description = desc_match.group(1).strip() if desc_match else ""

        # Extract tasks
        tasks = []
        tasks_match = re.search(r"\*\*Tasks\*\*:\s*\n((?:\s*-\s*\[.\]\s*.+\n?)+)", story_content)
        if tasks_match:
            for task_line in tasks_match.group(1).strip().split("\n"):
                task_match = re.match(r"\s*-\s*\[.\]\s*(.+)", task_line)
                if task_match:
                    tasks.append(task_match.group(1).strip())

        # Extract acceptance criteria
        criteria = []
        criteria_match = re.search(r"\*\*Acceptance Criteria\*\*:\s*\n((?:\s*-\s*\[.\]\s*.+\n?)+)", story_content)
        if criteria_match:
            for crit_line in criteria_match.group(1).strip().split("\n"):
                crit_match = re.match(r"\s*-\s*\[.\]\s*(.+)", crit_line)
                if crit_match:
                    criteria.append(crit_match.group(1).strip())

        stories.append({
            "title": title,
            "user_story": user_story,
            "description": description,
            "tasks": tasks,
            "acceptance_criteria": criteria,
        })

    return stories


def archive_draft(project_path: Path, draft_path: Path, issue_number: int) -> Path:
    """Archive a draft after it's been pushed to GitHub.

    Args:
        project_path: Project root path
        draft_path: Path to draft file
        issue_number: Created GitHub issue number

    Returns:
        Path to archived file in cache
    """
    cache_dir = project_path / ".specify" / "issues" / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)

    parsed = parse_draft(draft_path)
    draft_type = parsed["frontmatter"].get("type", "unknown")

    # Create cached version
    cache_file = cache_dir / f"{draft_type}-{issue_number}.md"

    # Update frontmatter with issue number
    content = draft_path.read_text()
    match = re.match(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
    if match:
        try:
            frontmatter = yaml.safe_load(match.group(1)) or {}
            frontmatter["github_issue"] = issue_number
            frontmatter["pushed_at"] = datetime.now(timezone.utc).isoformat()
            frontmatter["status"] = "pushed"

            new_frontmatter = yaml.dump(frontmatter, default_flow_style=False)
            body = content[match.end():]
            content = f"---\n{new_frontmatter}---{body}"
        except yaml.YAMLError:
            pass

    cache_file.write_text(content)

    # Remove original draft
    draft_path.unlink()

    return cache_file
