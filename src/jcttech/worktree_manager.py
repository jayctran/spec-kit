"""Git worktree management for Story implementation.

This module provides functionality for:
- Creating isolated worktrees for Story development
- Managing worktree lifecycle (create, check, cleanup)
- Tracking worktree status (clean/dirty)
- Generating branch names from issue numbers and titles
"""

import re
import subprocess
from pathlib import Path
from typing import Any


WORKTREES_DIR = "worktrees"
BRANCH_MAX_LENGTH = 50
BRANCH_PATTERN = re.compile(r"^(\d+)-(.+)$")


def get_worktrees_dir(project_path: Path) -> Path:
    """Get the worktrees directory path.

    Args:
        project_path: Project root path

    Returns:
        Path to worktrees directory
    """
    return project_path / WORKTREES_DIR


def generate_branch_name(issue_number: int, title: str) -> str:
    """Generate a branch name from issue number and title.

    Args:
        issue_number: GitHub issue number
        title: Issue title (will be slugified)

    Returns:
        Branch name like "102-jwt-token-service"
    """
    # Remove [Story] prefix, slugify title
    slug = title.lower()
    slug = re.sub(r"^\[story\]\s*", "", slug, flags=re.IGNORECASE)
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = slug.strip("-")

    # Limit length
    max_slug_length = BRANCH_MAX_LENGTH - len(str(issue_number)) - 1
    slug = slug[:max_slug_length].rstrip("-")

    return f"{issue_number}-{slug}"


def get_worktree_path(project_path: Path, branch_name: str) -> Path:
    """Get the full path to a worktree.

    Args:
        project_path: Project root path
        branch_name: Branch name (used as directory name)

    Returns:
        Full path to worktree directory
    """
    return get_worktrees_dir(project_path) / branch_name


def worktree_exists(project_path: Path, issue_number: int) -> tuple[bool, Path | None, str | None]:
    """Check if a worktree exists for an issue.

    Args:
        project_path: Project root path
        issue_number: GitHub issue number

    Returns:
        Tuple of (exists, path, branch_name)
    """
    worktrees_dir = get_worktrees_dir(project_path)
    if not worktrees_dir.exists():
        return False, None, None

    # Find directory starting with issue number
    for path in worktrees_dir.iterdir():
        if path.is_dir() and path.name.startswith(f"{issue_number}-"):
            return True, path, path.name
    return False, None, None


def get_worktree_status(worktree_path: Path) -> dict[str, Any]:
    """Get detailed git status for a worktree.

    Args:
        worktree_path: Path to worktree

    Returns:
        Dict with is_clean, modified_files, untracked_files, staged_files
    """
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True,
            cwd=worktree_path,
            check=True,
        )
    except subprocess.CalledProcessError:
        return {
            "is_clean": True,
            "modified_files": [],
            "untracked_files": [],
            "staged_files": [],
        }

    lines = result.stdout.strip().split("\n") if result.stdout.strip() else []
    modified = [line[3:] for line in lines if line.startswith(" M") or line.startswith("M ")]
    untracked = [line[3:] for line in lines if line.startswith("??")]
    staged = [line[3:] for line in lines if line[0] in "MADRC"]

    return {
        "is_clean": len(lines) == 0,
        "modified_files": modified,
        "untracked_files": untracked,
        "staged_files": staged,
    }


def create_worktree(
    project_path: Path,
    issue_number: int,
    title: str,
    base_branch: str = "main",
) -> dict[str, Any]:
    """Create a new worktree for a Story.

    Args:
        project_path: Project root path
        issue_number: Story issue number
        title: Story title
        base_branch: Branch to base off (default: main)

    Returns:
        Dict with worktree_path, branch_name, created (bool), resumed (bool)
    """
    # Check if already exists
    exists, existing_path, existing_branch = worktree_exists(project_path, issue_number)
    if exists:
        status = get_worktree_status(existing_path)
        return {
            "worktree_path": existing_path,
            "branch_name": existing_branch,
            "created": False,
            "resumed": True,
            "status": "dirty" if not status["is_clean"] else "clean",
        }

    branch_name = generate_branch_name(issue_number, title)
    worktree_path = get_worktree_path(project_path, branch_name)

    # Ensure worktrees directory exists
    get_worktrees_dir(project_path).mkdir(exist_ok=True)

    # Ensure worktrees is in .gitignore
    _ensure_gitignore(project_path)

    # Check if branch exists remotely
    try:
        result = subprocess.run(
            ["git", "ls-remote", "--heads", "origin", branch_name],
            capture_output=True,
            text=True,
            cwd=project_path,
        )
        branch_exists_remotely = bool(result.stdout.strip())
    except subprocess.CalledProcessError:
        branch_exists_remotely = False

    if branch_exists_remotely:
        # Branch exists remotely - fetch and create worktree from it
        subprocess.run(
            ["git", "fetch", "origin", branch_name],
            cwd=project_path,
            capture_output=True,
        )
        subprocess.run(
            ["git", "worktree", "add", str(worktree_path), f"origin/{branch_name}"],
            check=True,
            cwd=project_path,
            capture_output=True,
        )
        from_remote = True
    else:
        # Create new branch from base
        subprocess.run(
            ["git", "worktree", "add", "-b", branch_name, str(worktree_path), base_branch],
            check=True,
            cwd=project_path,
            capture_output=True,
        )
        from_remote = False

    return {
        "worktree_path": worktree_path,
        "branch_name": branch_name,
        "created": True,
        "resumed": False,
        "from_remote": from_remote,
        "status": "clean",
    }


def list_worktrees(project_path: Path) -> list[dict[str, Any]]:
    """List all active Story worktrees.

    Args:
        project_path: Project root path

    Returns:
        List of worktree info dicts with issue linkage
    """
    worktrees_dir = get_worktrees_dir(project_path)
    worktrees = []

    try:
        result = subprocess.run(
            ["git", "worktree", "list", "--porcelain"],
            capture_output=True,
            text=True,
            cwd=project_path,
            check=True,
        )
    except subprocess.CalledProcessError:
        return worktrees

    current: dict[str, Any] = {}

    for line in result.stdout.split("\n"):
        if line.startswith("worktree "):
            if current:
                worktrees.append(current)
            current = {"path": line[9:]}
        elif line.startswith("HEAD "):
            current["head"] = line[5:]
        elif line.startswith("branch "):
            current["branch"] = line[7:].replace("refs/heads/", "")
        elif line.startswith("detached"):
            current["detached"] = True

    if current:
        worktrees.append(current)

    # Filter to only our worktrees directory and add issue info
    worktrees_dir_str = str(worktrees_dir)
    story_worktrees = []

    for wt in worktrees:
        if wt.get("path", "").startswith(worktrees_dir_str):
            branch = wt.get("branch", "")
            match = BRANCH_PATTERN.match(branch)
            if match:
                wt["issue_number"] = int(match.group(1))
                wt["status"] = get_worktree_status(Path(wt["path"]))
                story_worktrees.append(wt)

    return story_worktrees


def remove_worktree(
    project_path: Path,
    issue_number: int,
    force: bool = False,
) -> dict[str, Any]:
    """Remove a worktree after completion.

    Args:
        project_path: Project root
        issue_number: Story issue number
        force: Force remove even if dirty

    Returns:
        Dict with removed (bool), reason, path, branch
    """
    exists, worktree_path, branch_name = worktree_exists(project_path, issue_number)
    if not exists:
        return {"removed": False, "reason": "not_found"}

    status = get_worktree_status(worktree_path)
    if not status["is_clean"] and not force:
        return {
            "removed": False,
            "reason": "dirty",
            "modified_files": status["modified_files"],
        }

    # Remove worktree
    cmd = ["git", "worktree", "remove", str(worktree_path)]
    if force:
        cmd.insert(3, "--force")

    try:
        subprocess.run(cmd, cwd=project_path, check=True, capture_output=True)
    except subprocess.CalledProcessError as e:
        return {"removed": False, "reason": "error", "error": str(e)}

    # Check if branch is merged and can be deleted
    try:
        result = subprocess.run(
            ["git", "branch", "--merged", "main"],
            capture_output=True,
            text=True,
            cwd=project_path,
        )
        if branch_name in result.stdout:
            subprocess.run(
                ["git", "branch", "-d", branch_name],
                cwd=project_path,
                capture_output=True,
            )
    except subprocess.CalledProcessError:
        pass  # Branch deletion is best-effort

    return {
        "removed": True,
        "path": str(worktree_path),
        "branch": branch_name,
    }


def get_commits_ahead(project_path: Path, issue_number: int) -> int:
    """Get number of commits ahead of origin for a worktree.

    Args:
        project_path: Project root path
        issue_number: Story issue number

    Returns:
        Number of commits ahead (0 if worktree doesn't exist or error)
    """
    exists, worktree_path, branch_name = worktree_exists(project_path, issue_number)
    if not exists:
        return 0

    try:
        result = subprocess.run(
            ["git", "rev-list", "--count", f"HEAD", f"^origin/{branch_name}"],
            capture_output=True,
            text=True,
            cwd=worktree_path,
        )
        return int(result.stdout.strip()) if result.stdout.strip() else 0
    except (subprocess.CalledProcessError, ValueError):
        return 0


def _ensure_gitignore(project_path: Path) -> None:
    """Ensure worktrees directory is in .gitignore.

    Args:
        project_path: Project root path
    """
    gitignore = project_path / ".gitignore"
    entry = f"{WORKTREES_DIR}/"

    if gitignore.exists():
        content = gitignore.read_text()
        if entry not in content:
            with gitignore.open("a") as f:
                if not content.endswith("\n"):
                    f.write("\n")
                f.write(f"{entry}\n")
    else:
        gitignore.write_text(f"{entry}\n")
