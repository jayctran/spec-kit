"""Story generation for JCT Tech issue-centric workflow.

This module provides functionality for:
- Breaking down specs into implementable stories
- Generating story issue content with task checkboxes
- Creating GitHub story issues from plan drafts
- Formatting stories for the issue template
"""

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def generate_story_body(
    title: str,
    user_story: str,
    description: str,
    tasks: list[str],
    acceptance_criteria: list[str],
    parent_spec: int,
    technical_notes: str | None = None,
) -> str:
    """Generate a story issue body with task checkboxes.

    Args:
        title: Story title
        user_story: "As a... I want... So that..." statement
        description: Detailed description
        tasks: List of task descriptions (will become checkboxes)
        acceptance_criteria: List of acceptance criteria
        parent_spec: Parent spec issue number
        technical_notes: Optional technical notes

    Returns:
        Formatted markdown body for GitHub issue
    """
    lines = [
        f"**Parent Spec**: #{parent_spec}",
        "",
        "## User Story",
        "",
        user_story if user_story else "_As a [user type], I want [action] so that [benefit]._",
        "",
        "## Description",
        "",
        description if description else "_[Detailed description of the story...]_",
        "",
        "## Tasks",
        "",
    ]

    # Add task checkboxes
    if tasks:
        for task in tasks:
            lines.append(f"- [ ] {task}")
    else:
        lines.append("- [ ] [Task 1]")
        lines.append("- [ ] [Task 2]")

    lines.extend([
        "",
        "## Acceptance Criteria",
        "",
    ])

    # Add acceptance criteria checkboxes
    if acceptance_criteria:
        for criterion in acceptance_criteria:
            lines.append(f"- [ ] {criterion}")
    else:
        lines.append("- [ ] [Criterion 1]")
        lines.append("- [ ] [Criterion 2]")

    if technical_notes:
        lines.extend([
            "",
            "## Technical Notes",
            "",
            technical_notes,
        ])

    return "\n".join(lines)


def generate_story_title(story_title: str) -> str:
    """Generate a properly formatted story title.

    Args:
        story_title: Raw story title

    Returns:
        Formatted title with [Story] prefix
    """
    # Clean up title
    title = story_title.strip()

    # Remove existing prefixes
    for prefix in ["Story:", "[Story]", "Story -"]:
        if title.lower().startswith(prefix.lower()):
            title = title[len(prefix):].strip()

    return f"[Story] {title}"


def stories_from_plan_draft(plan_content: str, parent_spec: int) -> list[dict]:
    """Extract story definitions from plan draft content.

    Args:
        plan_content: Full plan markdown content
        parent_spec: Parent spec issue number

    Returns:
        List of story dicts ready for issue creation
    """
    stories = []

    # Find all story sections
    # Pattern matches: ### Story N: Title
    story_pattern = r"###\s+Story\s+(\d+):\s+(.+?)(?=\n###\s+Story|\n##\s+[A-Z]|\n---\s*$|$)"
    matches = re.finditer(story_pattern, plan_content, re.DOTALL)

    for match in matches:
        story_num = int(match.group(1))
        story_block = match.group(0)

        # Extract title from first line
        first_line = story_block.split("\n")[0]
        title_match = re.search(r"###\s+Story\s+\d+:\s+(.+)", first_line)
        title = title_match.group(1).strip() if title_match else f"Story {story_num}"

        # Extract user story
        user_story = ""
        user_story_match = re.search(
            r"\*\*User Story\*\*:\s*(.+?)(?=\n\n|\n\*\*|\Z)",
            story_block,
            re.DOTALL,
        )
        if user_story_match:
            user_story = user_story_match.group(1).strip()

        # Extract description
        description = ""
        desc_match = re.search(
            r"\*\*Description\*\*:\s*(.+?)(?=\n\*\*Tasks|\n\*\*Acceptance|\Z)",
            story_block,
            re.DOTALL,
        )
        if desc_match:
            description = desc_match.group(1).strip()

        # Extract tasks
        tasks = _extract_checkbox_items(story_block, "Tasks")

        # Extract acceptance criteria
        criteria = _extract_checkbox_items(story_block, "Acceptance Criteria")

        # Extract technical notes if present
        technical_notes = None
        notes_match = re.search(
            r"\*\*Technical Notes\*\*:\s*(.+?)(?=\n\*\*|\n###|\n---|\Z)",
            story_block,
            re.DOTALL,
        )
        if notes_match:
            technical_notes = notes_match.group(1).strip()

        stories.append({
            "number": story_num,
            "title": generate_story_title(title),
            "user_story": user_story,
            "description": description,
            "tasks": tasks,
            "acceptance_criteria": criteria,
            "technical_notes": technical_notes,
            "parent_spec": parent_spec,
            "body": generate_story_body(
                title=title,
                user_story=user_story,
                description=description,
                tasks=tasks,
                acceptance_criteria=criteria,
                parent_spec=parent_spec,
                technical_notes=technical_notes,
            ),
            "type": "Story",
            "labels": ["status:draft"],
        })

    return stories


def _extract_checkbox_items(content: str, section_name: str) -> list[str]:
    """Extract checkbox items from a named section.

    Args:
        content: Content to search
        section_name: Name of section (e.g., "Tasks", "Acceptance Criteria")

    Returns:
        List of checkbox item texts (without checkbox markers)
    """
    items = []

    # Find section
    pattern = rf"\*\*{section_name}\*\*:\s*\n((?:\s*-\s*\[.\]\s*.+\n?)+)"
    match = re.search(pattern, content)

    if match:
        section_content = match.group(1)
        for line in section_content.split("\n"):
            item_match = re.match(r"\s*-\s*\[.\]\s*(.+)", line)
            if item_match:
                items.append(item_match.group(1).strip())

    return items


def update_story_task_status(
    story_body: str,
    task_index: int,
    completed: bool = True,
) -> str:
    """Update a task checkbox in a story body.

    Args:
        story_body: Current story issue body
        task_index: 0-based index of task to update
        completed: Whether to mark as completed

    Returns:
        Updated story body
    """
    lines = story_body.split("\n")
    task_count = 0

    for i, line in enumerate(lines):
        if re.match(r"\s*-\s*\[[ xX]\]", line):
            if task_count == task_index:
                # Update this task
                if completed:
                    lines[i] = re.sub(r"\[[ ]\]", "[x]", line)
                else:
                    lines[i] = re.sub(r"\[[xX]\]", "[ ]", line)
                break
            task_count += 1

    return "\n".join(lines)


def count_story_tasks(story_body: str) -> dict[str, int]:
    """Count tasks in a story body.

    Args:
        story_body: Story issue body

    Returns:
        Dict with total, completed, and remaining counts
    """
    total = 0
    completed = 0

    for line in story_body.split("\n"):
        if re.match(r"\s*-\s*\[[ ]\]", line):
            total += 1
        elif re.match(r"\s*-\s*\[[xX]\]", line):
            total += 1
            completed += 1

    return {
        "total": total,
        "completed": completed,
        "remaining": total - completed,
    }


def is_story_complete(story_body: str) -> bool:
    """Check if all tasks in a story are complete.

    Args:
        story_body: Story issue body

    Returns:
        True if all tasks are checked
    """
    counts = count_story_tasks(story_body)
    return counts["total"] > 0 and counts["remaining"] == 0


def generate_spec_breakdown_summary(stories: list[dict]) -> str:
    """Generate a summary of stories from a spec breakdown.

    Args:
        stories: List of story dicts

    Returns:
        Markdown summary string
    """
    lines = [
        "## Story Breakdown Summary",
        "",
        f"Generated {len(stories)} stories from spec:",
        "",
        "| # | Story | Tasks | Criteria |",
        "|---|-------|-------|----------|",
    ]

    for i, story in enumerate(stories, 1):
        title = story.get("title", "Untitled")
        task_count = len(story.get("tasks", []))
        criteria_count = len(story.get("acceptance_criteria", []))
        lines.append(f"| {i} | {title} | {task_count} | {criteria_count} |")

    total_tasks = sum(len(s.get("tasks", [])) for s in stories)
    total_criteria = sum(len(s.get("acceptance_criteria", [])) for s in stories)

    lines.extend([
        "",
        f"**Total Tasks**: {total_tasks}",
        f"**Total Acceptance Criteria**: {total_criteria}",
    ])

    return "\n".join(lines)


def estimate_story_complexity(story: dict) -> str:
    """Estimate story complexity based on tasks and criteria.

    Args:
        story: Story dict

    Returns:
        Complexity level: "S", "M", "L", or "XL"
    """
    task_count = len(story.get("tasks", []))
    criteria_count = len(story.get("acceptance_criteria", []))
    total = task_count + criteria_count

    if total <= 4:
        return "S"
    elif total <= 8:
        return "M"
    elif total <= 12:
        return "L"
    else:
        return "XL"


def suggest_story_dependencies(stories: list[dict]) -> list[tuple[int, int]]:
    """Suggest dependencies between stories based on task content.

    Args:
        stories: List of story dicts

    Returns:
        List of (dependent_index, dependency_index) tuples
    """
    dependencies = []

    # Common dependency keywords
    setup_keywords = ["setup", "initialize", "create", "configure", "install"]
    dependent_keywords = ["use", "extend", "modify", "update", "integrate"]

    for i, story in enumerate(stories):
        story_text = " ".join(story.get("tasks", []) + [story.get("title", "")]).lower()

        # If story contains dependent keywords, look for setup stories
        if any(kw in story_text for kw in dependent_keywords):
            for j, other_story in enumerate(stories):
                if i == j:
                    continue
                other_text = " ".join(other_story.get("tasks", []) + [other_story.get("title", "")]).lower()
                if any(kw in other_text for kw in setup_keywords):
                    dependencies.append((i, j))
                    break

    return dependencies
