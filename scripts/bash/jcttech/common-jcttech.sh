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
