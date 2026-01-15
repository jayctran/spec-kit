#!/usr/bin/env bash
# List available drafts with their status
# Usage: list-drafts.sh [--type spec|plan] [--json]

set -e
source "$(dirname "${BASH_SOURCE[0]}")/common-jcttech.sh"

JSON_MODE=false
DRAFT_TYPE=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --json) JSON_MODE=true; shift ;;
        --type) DRAFT_TYPE="$2"; shift 2 ;;
        -h|--help)
            echo "Usage: list-drafts.sh [--type spec|plan] [--json]"
            echo ""
            echo "Options:"
            echo "  --type TYPE    Filter by draft type (spec or plan)"
            echo "  --json         Output in JSON format"
            exit 0
            ;;
        *) shift ;;
    esac
done

REPO_ROOT=$(get_repo_root)
DRAFTS_BASE="$REPO_ROOT/.specify/drafts"

# Determine which types to list
if [[ -n "$DRAFT_TYPE" ]]; then
    TYPES=("$DRAFT_TYPE")
else
    TYPES=("spec" "plan")
fi

# Collect draft info
drafts_json=()
draft_count=0

for type in "${TYPES[@]}"; do
    DRAFTS_DIR="$DRAFTS_BASE/$type"

    [[ -d "$DRAFTS_DIR" ]] || continue

    for draft_file in "$DRAFTS_DIR"/*.md; do
        [[ -f "$draft_file" ]] || continue

        name=$(basename "$draft_file")
        title=$(get_frontmatter_value "$draft_file" "title" | sed 's/^"//' | sed 's/"$//')
        ready=$(get_frontmatter_value "$draft_file" "ready_to_push")
        parent_epic=$(get_frontmatter_value "$draft_file" "parent_epic")
        draft_id=$(get_frontmatter_value "$draft_file" "draft_id")
        status=$(get_frontmatter_value "$draft_file" "status")

        # Handle null/empty values
        [[ "$parent_epic" == "null" ]] && parent_epic=""
        [[ "$ready" == "true" ]] && ready_display="yes" || ready_display="no"

        if $JSON_MODE; then
            # Escape quotes in title
            title_escaped=$(echo "$title" | sed 's/"/\\"/g')
            draft_json="{\"name\":\"$name\",\"type\":\"$type\",\"title\":\"$title_escaped\",\"draft_id\":\"$draft_id\",\"ready_to_push\":$ready,\"parent_epic\":\"$parent_epic\",\"status\":\"$status\",\"path\":\"$draft_file\"}"
            drafts_json+=("$draft_json")
        else
            echo "[$type] $name"
            echo "  Title: $title"
            echo "  Draft ID: $draft_id"
            echo "  Ready to push: $ready_display"
            [[ -n "$parent_epic" ]] && echo "  Parent Epic: #$parent_epic"
            echo ""
        fi

        ((draft_count++))
    done
done

if $JSON_MODE; then
    if [[ ${#drafts_json[@]} -eq 0 ]]; then
        echo '{"drafts":[],"count":0}'
    else
        # Join array with commas
        joined=$(IFS=,; echo "${drafts_json[*]}")
        echo "{\"drafts\":[$joined],\"count\":$draft_count}"
    fi
else
    if [[ $draft_count -eq 0 ]]; then
        echo "No drafts found."
        [[ -n "$DRAFT_TYPE" ]] && echo "Try: /jcttech.specify to create a new $DRAFT_TYPE draft"
    else
        echo "---"
        echo "Total: $draft_count draft(s)"
    fi
fi
