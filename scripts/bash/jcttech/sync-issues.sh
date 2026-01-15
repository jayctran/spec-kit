#!/usr/bin/env bash
# Sync local issue index with GitHub Issues
# Usage: sync-issues.sh [--json]

set -e

# Source common functions
source "$(dirname "${BASH_SOURCE[0]}")/common-jcttech.sh"

# Parse arguments
JSON_MODE=false
VERBOSE=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        --json)
            JSON_MODE=true
            shift
            ;;
        --verbose|-v)
            VERBOSE=true
            shift
            ;;
        *)
            shift
            ;;
    esac
done

# Check prerequisites
check_gh_auth || exit 1

REPO=$(get_github_repo)
if [[ -z "$REPO" ]]; then
    echo "ERROR: Could not determine GitHub repository from git remote" >&2
    exit 1
fi

REPO_ROOT=$(get_repo_root)
ISSUES_DIR="$REPO_ROOT/.specify/issues"
INDEX_PATH="$ISSUES_DIR/index.md"
CACHE_DIR="$ISSUES_DIR/cache"

mkdir -p "$ISSUES_DIR"
mkdir -p "$CACHE_DIR"

# Fetch issues by type
fetch_issues_by_label() {
    local label="$1"
    gh issue list --repo "$REPO" --label "$label" --state all --limit 100 \
        --json number,title,state,labels,assignees,createdAt,updatedAt,body 2>/dev/null || echo "[]"
}

# Fetch all relevant issues
$VERBOSE && echo "Fetching issues from $REPO..."

EPICS=$(fetch_issues_by_label "type:epic")
SPECS=$(fetch_issues_by_label "type:spec")
STORIES=$(fetch_issues_by_label "type:story")
TASKS=$(fetch_issues_by_label "type:task")
BUGS=$(fetch_issues_by_label "type:bug")

# Count issues
EPIC_COUNT=$(echo "$EPICS" | jq 'length')
SPEC_COUNT=$(echo "$SPECS" | jq 'length')
STORY_COUNT=$(echo "$STORIES" | jq 'length')
TASK_COUNT=$(echo "$TASKS" | jq 'length')
BUG_COUNT=$(echo "$BUGS" | jq 'length')
TOTAL_COUNT=$((EPIC_COUNT + SPEC_COUNT + STORY_COUNT + TASK_COUNT + BUG_COUNT))

$VERBOSE && echo "Found: $EPIC_COUNT epics, $SPEC_COUNT specs, $STORY_COUNT stories, $TASK_COUNT tasks, $BUG_COUNT bugs"

# Generate new index.md
TIMESTAMP=$(get_iso_timestamp)

generate_index() {
    cat << EOF
# Issue Index

> Last synced: ${TIMESTAMP}
> Repository: ${REPO}

## Hierarchy

EOF

    # Process epics
    if [[ "$EPIC_COUNT" -gt 0 ]]; then
        echo "$EPICS" | jq -r '.[] | "### Epic: \(.title) (#\(.number))\n**Status**: \(.state) | **Labels**: \(.labels | map(.name) | join(", "))\n"'

        # For each epic, find its specs
        echo "$EPICS" | jq -r '.[].number' | while read epic_num; do
            local epic_title=$(echo "$EPICS" | jq -r ".[] | select(.number == $epic_num) | .title")

            # Find specs that reference this epic as parent
            local child_specs=$(echo "$SPECS" | jq "[.[] | select(.body | test(\"Parent Epic:.*#$epic_num\"; \"i\"))]")
            local spec_count=$(echo "$child_specs" | jq 'length')

            if [[ "$spec_count" -gt 0 ]]; then
                echo "#### Specs"
                echo "| # | Title | Status | Stories |"
                echo "|---|-------|--------|---------|"

                echo "$child_specs" | jq -r '.[] | "| #\(.number) | [\(.title)](https://github.com/'$REPO'/issues/\(.number)) | \(.state) | - |"'
            fi
        done
    else
        echo "_No issues tracked yet. Use \`/jcttech.epic\` to create your first epic._"
    fi

    cat << EOF

---

## Drafts (Not Yet Pushed)

EOF

    # List drafts
    local drafts_dir="$REPO_ROOT/.specify/drafts"
    local has_drafts=false

    if [[ -d "$drafts_dir" ]]; then
        echo "| Draft | Type | Ready |"
        echo "|-------|------|-------|"

        for type_dir in "$drafts_dir"/*; do
            [[ -d "$type_dir" ]] || continue
            local draft_type=$(basename "$type_dir")

            for draft_file in "$type_dir"/*.md; do
                [[ -f "$draft_file" ]] || continue
                has_drafts=true
                local draft_name=$(basename "$draft_file")
                local ready=$(grep -q "^ready_to_push: true" "$draft_file" && echo "yes" || echo "no")
                echo "| [$draft_name](../drafts/$draft_type/$draft_name) | $draft_type | $ready |"
            done
        done
    fi

    if ! $has_drafts; then
        echo "_No drafts yet. Use \`/jcttech.specify\` to create a spec draft._"
    fi

    cat << EOF

---

## Metadata
\`\`\`yaml
sync_version: 1
last_full_sync: "${TIMESTAMP}"
issues_cached: ${TOTAL_COUNT}
drafts_pending: 0
\`\`\`
EOF
}

# Write index
generate_index > "$INDEX_PATH"

# Cache individual issues
$VERBOSE && echo "Caching issues..."

cache_issues() {
    local issues="$1"
    local issue_type="$2"

    echo "$issues" | jq -c '.[]' | while read -r issue; do
        local num=$(echo "$issue" | jq -r '.number')
        local title=$(echo "$issue" | jq -r '.title')
        local body=$(echo "$issue" | jq -r '.body // ""')
        local state=$(echo "$issue" | jq -r '.state')

        local cache_file="$CACHE_DIR/${issue_type}-${num}.md"
        cat > "$cache_file" << EOF
---
issue_number: ${num}
type: ${issue_type}
state: ${state}
cached_at: "${TIMESTAMP}"
---

# ${title}

${body}
EOF
    done
}

cache_issues "$EPICS" "epic"
cache_issues "$SPECS" "spec"
cache_issues "$STORIES" "story"
cache_issues "$TASKS" "task"
cache_issues "$BUGS" "bug"

# Output result
if $JSON_MODE; then
    cat << EOF
{
  "sync_time": "${TIMESTAMP}",
  "repository": "${REPO}",
  "index_path": "${INDEX_PATH}",
  "epics": ${EPIC_COUNT},
  "specs": ${SPEC_COUNT},
  "stories": ${STORY_COUNT},
  "tasks": ${TASK_COUNT},
  "bugs": ${BUG_COUNT},
  "total": ${TOTAL_COUNT}
}
EOF
else
    echo "Sync complete: ${TIMESTAMP}"
    echo "Index: ${INDEX_PATH}"
    echo "Issues cached: ${TOTAL_COUNT}"
fi
