#!/usr/bin/env bash
# Common functions for JCT Tech issue-centric workflow scripts

# Source parent common.sh
source "$(dirname "${BASH_SOURCE[0]}")/../common.sh"

# Get the .docs path from project
get_docs_path() {
    local repo_root=$(get_repo_root)
    echo "$repo_root/.docs"
}

# Get the .specify/issues path
get_issues_path() {
    local repo_root=$(get_repo_root)
    echo "$repo_root/.specify/issues"
}

# Get the .specify/drafts path
get_drafts_path() {
    local repo_root=$(get_repo_root)
    echo "$repo_root/.specify/drafts"
}

# Get next draft number for a type
get_next_draft_number() {
    local draft_type="${1:-spec}"
    local drafts_dir="$(get_drafts_path)/$draft_type"
    local highest=0

    if [[ -d "$drafts_dir" ]]; then
        for f in "$drafts_dir"/*.md; do
            [[ -f "$f" ]] || continue
            local num=$(basename "$f" | grep -o '^[0-9]\+' || echo "0")
            [[ "$num" -gt "$highest" ]] && highest=$num
        done
    fi

    printf "%03d" $((highest + 1))
}

# Create a short name slug from title
create_short_name() {
    local title="$1"
    echo "$title" | tr '[:upper:]' '[:lower:]' | \
        sed 's/[^a-z0-9]/-/g' | \
        sed 's/-\+/-/g' | \
        cut -c1-50 | \
        sed 's/-$//'
}

# Check if gh CLI is available and authenticated
check_gh_auth() {
    if ! command -v gh &>/dev/null; then
        echo "ERROR: gh CLI not found. Install from https://cli.github.com/" >&2
        return 1
    fi

    if ! gh auth status &>/dev/null; then
        echo "ERROR: gh CLI not authenticated. Run 'gh auth login'" >&2
        return 1
    fi

    return 0
}

# Get GitHub repository name from git remote
get_github_repo() {
    local remote_url=$(git config --get remote.origin.url 2>/dev/null)
    if [[ -z "$remote_url" ]]; then
        echo ""
        return 1
    fi

    # Extract owner/repo from various URL formats
    local repo=""
    if [[ "$remote_url" =~ github\.com[:/]([^/]+)/([^/.]+)(\.git)?$ ]]; then
        repo="${BASH_REMATCH[1]}/${BASH_REMATCH[2]}"
    fi

    echo "$repo"
}

# Parse YAML frontmatter value from a file
get_frontmatter_value() {
    local file="$1"
    local key="$2"

    # Simple grep-based parsing (works for simple values)
    grep "^${key}:" "$file" 2>/dev/null | sed "s/^${key}:\s*//" | sed 's/^"//' | sed 's/"$//'
}

# Update YAML frontmatter value in a file
update_frontmatter_value() {
    local file="$1"
    local key="$2"
    local value="$3"

    # Use sed to replace the value
    sed -i "s/^${key}:.*/${key}: ${value}/" "$file"
}

# Output JSON for agent consumption
output_json() {
    local -n data=$1
    printf '{'
    local first=true
    for key in "${!data[@]}"; do
        if $first; then
            first=false
        else
            printf ','
        fi
        printf '"%s":"%s"' "$key" "${data[$key]}"
    done
    printf '}\n'
}

# Check if index.md exists
has_index() {
    local index_path="$(get_issues_path)/index.md"
    [[ -f "$index_path" ]]
}

# Get current timestamp in ISO format
get_iso_timestamp() {
    date -Iseconds 2>/dev/null || date +%Y-%m-%dT%H:%M:%S%z
}

# Get worktrees directory path
get_worktrees_path() {
    local repo_root=$(get_repo_root)
    echo "$repo_root/worktrees"
}

# Ensure worktrees directory is in .gitignore
ensure_worktrees_gitignore() {
    local repo_root=$(get_repo_root)
    local gitignore="$repo_root/.gitignore"

    if ! grep -q "^worktrees/$" "$gitignore" 2>/dev/null; then
        echo "worktrees/" >> "$gitignore"
    fi
}

# Get issue number from branch name
# Usage: get_issue_from_branch "102-jwt-token-service"
# Returns: 102
get_issue_from_branch() {
    local branch="$1"
    echo "$branch" | grep -oP '^\d+' || echo ""
}

# Check if worktree exists for an issue
# Usage: has_worktree 102
has_worktree() {
    local issue_number="$1"
    local worktrees_dir="$(get_worktrees_path)"

    if [[ ! -d "$worktrees_dir" ]]; then
        return 1
    fi

    for dir in "$worktrees_dir"/${issue_number}-*/; do
        if [[ -d "$dir" ]]; then
            return 0
        fi
    done

    return 1
}

# Get the .specify/config.yml path
get_config_path() {
    local repo_root=$(get_repo_root)
    echo "$repo_root/.specify/config.yml"
}

# Get the .specify/project-fields.yml path
get_fields_cache_path() {
    local repo_root=$(get_repo_root)
    echo "$repo_root/.specify/project-fields.yml"
}

# Get project number from config
# Usage: get_project_number
get_project_number() {
    local config_file="$(get_config_path)"
    if [[ -f "$config_file" ]]; then
        grep "project:" "$config_file" 2>/dev/null | sed 's/.*project: *//' | tr -d '"' | tr -d "'"
    else
        echo ""
    fi
}

# Get project owner from config
# Usage: get_project_owner
get_project_owner() {
    local config_file="$(get_config_path)"
    if [[ -f "$config_file" ]]; then
        grep "owner:" "$config_file" 2>/dev/null | head -1 | sed 's/.*owner: *//' | tr -d '"' | tr -d "'"
    else
        echo ""
    fi
}

# Get project field ID from cache
# Usage: get_project_field_id "status"
get_project_field_id() {
    local field_name="$1"
    local fields_file="$(get_fields_cache_path)"

    if [[ -f "$fields_file" ]]; then
        # Parse YAML to get field ID (simple grep-based parsing)
        awk -v field="$field_name:" '
            $0 ~ field {found=1; next}
            found && /id:/ {gsub(/.*id: *"?|"?$/, ""); print; exit}
        ' "$fields_file"
    else
        echo ""
    fi
}

# Get project field option ID from cache
# Usage: get_project_field_option_id "status" "inbox"
get_project_field_option_id() {
    local field_name="$1"
    local option_name="$2"
    local fields_file="$(get_fields_cache_path)"

    if [[ -f "$fields_file" ]]; then
        # Parse YAML to get option ID (simple grep-based parsing)
        awk -v field="$field_name:" -v option="$option_name:" '
            $0 ~ field {in_field=1; next}
            in_field && /^  [a-z]/ && !/:$/ {in_field=0}
            in_field && $0 ~ option {gsub(/.*: *"?|"?$/, ""); print; exit}
        ' "$fields_file"
    else
        echo ""
    fi
}

# Check if issue type can exist without a parent
# Usage: is_orphan_allowed "Idea"
# Returns: 0 (true) if orphan allowed, 1 (false) otherwise
is_orphan_allowed() {
    local issue_type="$1"

    case "$issue_type" in
        Epic|Idea)
            return 0  # Epics and Ideas can be orphans
            ;;
        *)
            return 1  # All other types need parents
            ;;
    esac
}

# Add issue to project with optional status
# Usage: add_to_project "123" "inbox"
add_to_project() {
    local issue_number="$1"
    local status="${2:-}"
    local project_num=$(get_project_number)
    local owner=$(get_project_owner)

    if [[ -z "$project_num" || -z "$owner" ]]; then
        echo "WARNING: Project not configured. Run /jcttech.setup-project first." >&2
        return 1
    fi

    # Add to project using gh CLI
    gh project item-add "$project_num" --owner "$owner" --url "$(gh repo view --json url -q '.url')/issues/$issue_number" 2>/dev/null || true

    # If status specified, try to set it (requires project field IDs)
    if [[ -n "$status" ]]; then
        local status_field_id=$(get_project_field_id "status")
        local status_option_id=$(get_project_field_option_id "status" "$status")

        if [[ -n "$status_field_id" && -n "$status_option_id" ]]; then
            # Get the project item ID first
            local item_id=$(gh project item-list "$project_num" --owner "$owner" --format json | \
                jq -r ".items[] | select(.content.number == $issue_number) | .id" 2>/dev/null)

            if [[ -n "$item_id" ]]; then
                gh project item-edit --project-id "$project_num" --id "$item_id" \
                    --field-id "$status_field_id" --single-select-option-id "$status_option_id" 2>/dev/null || true
            fi
        fi
    fi
}

# Add issue to project Inbox column
# Usage: add_to_project_inbox "123"
add_to_project_inbox() {
    local issue_number="$1"
    add_to_project "$issue_number" "inbox"
}
