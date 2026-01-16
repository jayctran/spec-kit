#!/usr/bin/env bash
# Cascade close parent issues when all children are closed
# Usage: cascade-close.sh --story {number}

set -e
source "$(dirname "${BASH_SOURCE[0]}")/common-jcttech.sh"

STORY_NUMBER=""
JSON_MODE=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        --story)
            STORY_NUMBER="$2"
            shift 2
            ;;
        --json)
            JSON_MODE=true
            shift
            ;;
        *)
            shift
            ;;
    esac
done

# Validate input
if [[ -z "$STORY_NUMBER" ]]; then
    echo "Usage: cascade-close.sh --story {number}" >&2
    exit 1
fi

# Check GitHub CLI auth
check_gh_auth || exit 1

# Get repo
REPO=$(get_github_repo)
if [[ -z "$REPO" ]]; then
    echo "ERROR: Could not determine GitHub repository" >&2
    exit 1
fi

# Get parent Spec from native GitHub parent relationship
PARENT_SPEC=$(gh issue view "$STORY_NUMBER" --repo "$REPO" --json parent -q '.parent.number' 2>/dev/null || echo "")

# Fallback to body parsing for backwards compatibility
if [[ -z "$PARENT_SPEC" ]]; then
    STORY_BODY=$(gh issue view "$STORY_NUMBER" --repo "$REPO" --json body -q '.body' 2>/dev/null)
    PARENT_SPEC=$(echo "$STORY_BODY" | grep -oP 'Parent Spec:\s*#\K\d+' || echo "")
fi

if [[ -z "$PARENT_SPEC" ]]; then
    if $JSON_MODE; then
        echo '{"cascade_triggered":false,"reason":"no_parent_spec"}'
    else
        echo "No parent Spec found for Story #$STORY_NUMBER"
    fi
    exit 0
fi

# Count open Stories under this Spec using native parent relationship
OPEN_STORIES=$(gh issue list --repo "$REPO" --type Story --state open --json number,parent 2>/dev/null \
    | jq "[.[] | select(.parent.number == $PARENT_SPEC)] | length")

# Fallback to body parsing for backwards compatibility if no results
if [[ "$OPEN_STORIES" == "0" || -z "$OPEN_STORIES" ]]; then
    OPEN_STORIES=$(gh issue list --repo "$REPO" --type Story --state open --json body,number 2>/dev/null \
        | jq "[.[] | select(.body | test(\"Parent Spec:\\\\s*#$PARENT_SPEC\"; \"i\"))] | length")
fi

if [[ "$OPEN_STORIES" -eq 0 ]]; then
    # All Stories complete - close the Spec
    if $JSON_MODE; then
        echo -n '{"cascade_triggered":true,"spec_closed":'"$PARENT_SPEC"
    else
        echo "All Stories in Spec #$PARENT_SPEC complete"
        echo "Closing Spec #$PARENT_SPEC..."
    fi

    gh issue close "$PARENT_SPEC" --repo "$REPO" \
        --comment "All Stories completed. Auto-closing Spec." 2>/dev/null

    # Now check parent Epic using native relationship
    PARENT_EPIC=$(gh issue view "$PARENT_SPEC" --repo "$REPO" --json parent -q '.parent.number' 2>/dev/null || echo "")

    # Fallback to body parsing for backwards compatibility
    if [[ -z "$PARENT_EPIC" ]]; then
        SPEC_BODY=$(gh issue view "$PARENT_SPEC" --repo "$REPO" --json body -q '.body' 2>/dev/null)
        PARENT_EPIC=$(echo "$SPEC_BODY" | grep -oP 'Parent Epic:\s*#\K\d+' || echo "")
    fi

    if [[ -n "$PARENT_EPIC" ]]; then
        # Count open Specs under this Epic using native parent relationship
        OPEN_SPECS=$(gh issue list --repo "$REPO" --type Spec --state open --json number,parent 2>/dev/null \
            | jq "[.[] | select(.parent.number == $PARENT_EPIC)] | length")

        # Fallback to body parsing for backwards compatibility
        if [[ "$OPEN_SPECS" == "0" || -z "$OPEN_SPECS" ]]; then
            OPEN_SPECS=$(gh issue list --repo "$REPO" --type Spec --state open --json body,number 2>/dev/null \
                | jq "[.[] | select(.body | test(\"Parent Epic:\\\\s*#$PARENT_EPIC\"; \"i\"))] | length")
        fi

        if [[ "$OPEN_SPECS" -eq 0 ]]; then
            # All Specs complete - close the Epic
            if $JSON_MODE; then
                echo -n ',"epic_closed":'"$PARENT_EPIC"
            else
                echo "All Specs in Epic #$PARENT_EPIC complete"
                echo "Closing Epic #$PARENT_EPIC..."
            fi

            gh issue close "$PARENT_EPIC" --repo "$REPO" \
                --comment "All Specs completed. Auto-closing Epic." 2>/dev/null
        else
            if $JSON_MODE; then
                echo -n ',"epic_open":'"$PARENT_EPIC"',"open_specs":'"$OPEN_SPECS"
            else
                echo "Epic #$PARENT_EPIC still has $OPEN_SPECS open Specs"
            fi
        fi
    fi

    if $JSON_MODE; then
        echo '}'
    fi
else
    # Stories still open
    if $JSON_MODE; then
        echo '{"cascade_triggered":false,"open_stories":'"$OPEN_STORIES"',"parent_spec":'"$PARENT_SPEC"'}'
    else
        echo "$OPEN_STORIES Stories still open under Spec #$PARENT_SPEC"
    fi
fi
