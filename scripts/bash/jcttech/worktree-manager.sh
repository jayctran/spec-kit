#!/usr/bin/env bash
# Git worktree management for Story implementation
# Provides isolated worktrees for parallel Story development

set -e
source "$(dirname "${BASH_SOURCE[0]}")/common-jcttech.sh"

# Configuration
WORKTREES_DIR="worktrees"
BRANCH_MAX_LENGTH=50

# Get worktrees directory path
get_worktrees_path() {
    local repo_root=$(get_repo_root)
    echo "$repo_root/$WORKTREES_DIR"
}

# Generate branch name from issue number and title
# Usage: generate_branch_name 102 "[Story] Add JWT Token Service"
# Returns: 102-add-jwt-token-service
generate_branch_name() {
    local issue_number="$1"
    local title="$2"

    # Remove [Story] prefix and create slug
    local slug=$(echo "$title" | \
        sed -E 's/^\[Story\]\s*//i' | \
        tr '[:upper:]' '[:lower:]' | \
        sed 's/[^a-z0-9]/-/g' | \
        sed 's/-\+/-/g' | \
        sed 's/^-//' | \
        sed 's/-$//')

    # Limit total length
    local max_slug_length=$((BRANCH_MAX_LENGTH - ${#issue_number} - 1))
    slug="${slug:0:$max_slug_length}"
    slug="${slug%-}"  # Remove trailing dash if present

    echo "${issue_number}-${slug}"
}

# Check if worktree exists for an issue
# Usage: check_worktree 102
# Returns JSON: {"exists": true/false, "path": "...", "branch": "...", "status": "clean/dirty"}
check_worktree() {
    local issue_number="$1"
    local worktrees_dir=$(get_worktrees_path)

    if [[ ! -d "$worktrees_dir" ]]; then
        echo '{"exists":false}'
        return 0
    fi

    # Find directory starting with issue number
    for dir in "$worktrees_dir"/${issue_number}-*/; do
        if [[ -d "$dir" ]]; then
            local branch=$(basename "$dir")
            local status="clean"
            local modified_files=""

            # Check git status in worktree
            if [[ -n "$(git -C "$dir" status --porcelain 2>/dev/null)" ]]; then
                status="dirty"
                modified_files=$(git -C "$dir" status --porcelain | head -5 | tr '\n' ',' | sed 's/,$//')
            fi

            echo "{\"exists\":true,\"path\":\"${dir%/}\",\"branch\":\"$branch\",\"status\":\"$status\",\"modified_files\":\"$modified_files\"}"
            return 0
        fi
    done

    echo '{"exists":false}'
}

# Create worktree for a Story
# Usage: create_worktree 102 "[Story] Add JWT Token Service" [base_branch]
create_worktree() {
    local issue_number="$1"
    local title="$2"
    local base_branch="${3:-main}"
    local repo_root=$(get_repo_root)

    # Check if worktree already exists
    local existing=$(check_worktree "$issue_number")
    if [[ "$(echo "$existing" | jq -r '.exists')" == "true" ]]; then
        local existing_path=$(echo "$existing" | jq -r '.path')
        local existing_branch=$(echo "$existing" | jq -r '.branch')
        local existing_status=$(echo "$existing" | jq -r '.status')
        echo "{\"created\":false,\"resumed\":true,\"path\":\"$existing_path\",\"branch\":\"$existing_branch\",\"status\":\"$existing_status\"}"
        return 0
    fi

    # Generate branch name
    local branch_name=$(generate_branch_name "$issue_number" "$title")
    local worktree_path="$(get_worktrees_path)/$branch_name"

    # Ensure worktrees directory exists
    mkdir -p "$(get_worktrees_path)"

    # Ensure worktrees is in .gitignore
    local gitignore="$repo_root/.gitignore"
    if ! grep -q "^${WORKTREES_DIR}/$" "$gitignore" 2>/dev/null; then
        echo "${WORKTREES_DIR}/" >> "$gitignore"
    fi

    # Check if branch exists remotely
    if git ls-remote --heads origin "$branch_name" 2>/dev/null | grep -q "$branch_name"; then
        # Branch exists remotely - fetch and create worktree from it
        git fetch origin "$branch_name" 2>/dev/null || true
        git worktree add "$worktree_path" "origin/$branch_name" 2>/dev/null
        echo "{\"created\":true,\"resumed\":false,\"path\":\"$worktree_path\",\"branch\":\"$branch_name\",\"from_remote\":true}"
    else
        # Create new branch from base
        git worktree add -b "$branch_name" "$worktree_path" "$base_branch" 2>/dev/null
        echo "{\"created\":true,\"resumed\":false,\"path\":\"$worktree_path\",\"branch\":\"$branch_name\",\"from_remote\":false}"
    fi
}

# List all active worktrees with metadata
# Usage: list_worktrees
list_worktrees() {
    local repo_root=$(get_repo_root)
    local worktrees_dir=$(get_worktrees_path)

    echo '['
    local first=true

    # Parse git worktree list output
    while IFS= read -r line; do
        local path=$(echo "$line" | awk '{print $1}')

        # Only include worktrees in our worktrees directory
        if [[ "$path" == "$worktrees_dir"/* ]]; then
            local branch=$(basename "$path")
            local issue_number=$(echo "$branch" | grep -oP '^\d+' || echo "")

            if [[ -n "$issue_number" ]]; then
                local status="clean"
                local modified_count=0

                if [[ -n "$(git -C "$path" status --porcelain 2>/dev/null)" ]]; then
                    status="dirty"
                    modified_count=$(git -C "$path" status --porcelain 2>/dev/null | wc -l)
                fi

                if $first; then
                    first=false
                else
                    echo ','
                fi

                echo -n "{\"issue_number\":$issue_number,\"branch\":\"$branch\",\"path\":\"$path\",\"status\":\"$status\",\"modified_count\":$modified_count}"
            fi
        fi
    done < <(git worktree list 2>/dev/null)

    echo ''
    echo ']'
}

# Get worktree path for switching
# Usage: switch_worktree 102
switch_worktree() {
    local issue_number="$1"
    local result=$(check_worktree "$issue_number")

    if [[ "$(echo "$result" | jq -r '.exists')" == "true" ]]; then
        echo "$result" | jq -r '.path'
    else
        echo "ERROR: No worktree found for issue #$issue_number" >&2
        return 1
    fi
}

# Remove worktree after completion
# Usage: cleanup_worktree 102 [--force]
cleanup_worktree() {
    local issue_number="$1"
    local force=""
    [[ "$2" == "--force" ]] && force="--force"

    local result=$(check_worktree "$issue_number")

    if [[ "$(echo "$result" | jq -r '.exists')" != "true" ]]; then
        echo '{"removed":false,"reason":"not_found"}'
        return 0
    fi

    local path=$(echo "$result" | jq -r '.path')
    local status=$(echo "$result" | jq -r '.status')
    local branch=$(echo "$result" | jq -r '.branch')

    # Check if dirty and not forced
    if [[ "$status" == "dirty" && -z "$force" ]]; then
        echo '{"removed":false,"reason":"dirty","modified_files":"'"$(echo "$result" | jq -r '.modified_files')"'"}'
        return 1
    fi

    # Remove worktree
    if [[ -n "$force" ]]; then
        git worktree remove "$path" --force 2>/dev/null
    else
        git worktree remove "$path" 2>/dev/null
    fi

    # Optionally prune the branch if merged
    # Check if branch is merged into main
    if git branch --merged main 2>/dev/null | grep -q "$branch"; then
        git branch -d "$branch" 2>/dev/null || true
    fi

    echo '{"removed":true,"path":"'"$path"'","branch":"'"$branch"'"}'
}

# Get worktree status details
# Usage: get_worktree_status 102
get_worktree_status() {
    local issue_number="$1"
    local result=$(check_worktree "$issue_number")

    if [[ "$(echo "$result" | jq -r '.exists')" != "true" ]]; then
        echo '{"error":"not_found"}'
        return 1
    fi

    local path=$(echo "$result" | jq -r '.path')

    # Get detailed status
    local modified=$(git -C "$path" status --porcelain 2>/dev/null | grep '^ M\|^M ' | wc -l || echo 0)
    local untracked=$(git -C "$path" status --porcelain 2>/dev/null | grep '^??' | wc -l || echo 0)
    local staged=$(git -C "$path" status --porcelain 2>/dev/null | grep '^[MADRC]' | wc -l || echo 0)
    local ahead=$(git -C "$path" rev-list --count HEAD ^origin/$(echo "$result" | jq -r '.branch') 2>/dev/null || echo 0)

    echo "{\"path\":\"$path\",\"modified\":$modified,\"untracked\":$untracked,\"staged\":$staged,\"commits_ahead\":$ahead}"
}

# Main CLI interface
main() {
    local action=""
    local issue_number=""
    local title=""
    local force=""
    local json_mode=false

    while [[ $# -gt 0 ]]; do
        case "$1" in
            --check)
                action="check"
                issue_number="$2"
                shift 2
                ;;
            --create)
                action="create"
                issue_number="$2"
                shift 2
                ;;
            --title)
                title="$2"
                shift 2
                ;;
            --list)
                action="list"
                shift
                ;;
            --switch)
                action="switch"
                issue_number="$2"
                shift 2
                ;;
            --cleanup)
                action="cleanup"
                issue_number="$2"
                shift 2
                ;;
            --status)
                action="status"
                issue_number="$2"
                shift 2
                ;;
            --force)
                force="--force"
                shift
                ;;
            --json)
                json_mode=true
                shift
                ;;
            *)
                shift
                ;;
        esac
    done

    case "$action" in
        check)
            check_worktree "$issue_number"
            ;;
        create)
            if [[ -z "$title" ]]; then
                echo '{"error":"title_required"}' >&2
                exit 1
            fi
            create_worktree "$issue_number" "$title"
            ;;
        list)
            list_worktrees
            ;;
        switch)
            switch_worktree "$issue_number"
            ;;
        cleanup)
            cleanup_worktree "$issue_number" "$force"
            ;;
        status)
            get_worktree_status "$issue_number"
            ;;
        *)
            echo "Usage: worktree-manager.sh [--check|--create|--list|--switch|--cleanup|--status] [options]" >&2
            echo "" >&2
            echo "Commands:" >&2
            echo "  --check {issue_number}              Check if worktree exists" >&2
            echo "  --create {issue_number} --title \"{title}\"  Create new worktree" >&2
            echo "  --list                              List all active worktrees" >&2
            echo "  --switch {issue_number}             Get path to worktree" >&2
            echo "  --cleanup {issue_number} [--force]  Remove worktree" >&2
            echo "  --status {issue_number}             Get detailed worktree status" >&2
            exit 1
            ;;
    esac
}

# Only run main if script is executed directly (not sourced)
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
