#!/usr/bin/env bash
# Create a new draft spec or plan
# Usage: create-draft.sh --type spec|plan --title "Title" [--parent-epic N]

set -e

# Source common functions
source "$(dirname "${BASH_SOURCE[0]}")/common-jcttech.sh"

# Parse arguments
JSON_MODE=false
DRAFT_TYPE="spec"
TITLE=""
PARENT_EPIC=""
DESCRIPTION=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --json)
            JSON_MODE=true
            shift
            ;;
        --type)
            DRAFT_TYPE="$2"
            shift 2
            ;;
        --title)
            TITLE="$2"
            shift 2
            ;;
        --parent-epic)
            PARENT_EPIC="$2"
            shift 2
            ;;
        --description)
            DESCRIPTION="$2"
            shift 2
            ;;
        *)
            # Treat remaining args as title if not set
            if [[ -z "$TITLE" ]]; then
                TITLE="$1"
            fi
            shift
            ;;
    esac
done

# Validate required arguments
if [[ -z "$TITLE" ]]; then
    echo "ERROR: Title is required" >&2
    echo "Usage: create-draft.sh --type spec|plan --title \"Title\" [--parent-epic N]" >&2
    exit 1
fi

# Setup paths
REPO_ROOT=$(get_repo_root)
DRAFTS_DIR="$REPO_ROOT/.specify/drafts/$DRAFT_TYPE"
mkdir -p "$DRAFTS_DIR"

# Generate draft identifiers
DRAFT_NUM=$(get_next_draft_number "$DRAFT_TYPE")
SHORT_NAME=$(create_short_name "$TITLE")
DRAFT_ID="${DRAFT_TYPE}-${DRAFT_NUM}-${SHORT_NAME}"
TIMESTAMP=$(get_iso_timestamp)

# Determine filename
if [[ "$DRAFT_TYPE" == "plan" ]]; then
    FILENAME="${DRAFT_NUM}-${SHORT_NAME}-plan.md"
else
    FILENAME="${DRAFT_NUM}-${SHORT_NAME}.md"
fi

DRAFT_PATH="$DRAFTS_DIR/$FILENAME"

# Generate content based on type
if [[ "$DRAFT_TYPE" == "spec" ]]; then
    cat > "$DRAFT_PATH" << EOF
---
draft_id: ${DRAFT_ID}
type: spec
title: "${TITLE}"
created: "${TIMESTAMP}"
modified: "${TIMESTAMP}"
status: draft
ready_to_push: false
parent_epic: ${PARENT_EPIC:-null}
validation:
  passed: false
  issues: []
---

# Spec: ${TITLE}

## Overview

${DESCRIPTION:-"[Describe the feature or change being specified...]"}

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
EOF

elif [[ "$DRAFT_TYPE" == "plan" ]]; then
    cat > "$DRAFT_PATH" << EOF
---
draft_id: ${DRAFT_ID}
type: plan
title: "Plan: ${TITLE}"
created: "${TIMESTAMP}"
modified: "${TIMESTAMP}"
status: draft
parent_spec: ${PARENT_EPIC:-null}
stories_generated: false
---

# Implementation Plan: ${TITLE}

**Parent Spec**: #${PARENT_EPIC:-"[SPEC_NUMBER]"}

## Implementation Approach

${DESCRIPTION:-"[Describe the overall approach to implementing this spec...]"}

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
EOF
fi

# Output result
if $JSON_MODE; then
    declare -A result=(
        ["DRAFT_PATH"]="$DRAFT_PATH"
        ["DRAFT_ID"]="$DRAFT_ID"
        ["DRAFT_NUM"]="$DRAFT_NUM"
        ["DRAFT_TYPE"]="$DRAFT_TYPE"
        ["SHORT_NAME"]="$SHORT_NAME"
    )
    output_json result
else
    echo "Draft created: $DRAFT_PATH"
    echo "Draft ID: $DRAFT_ID"
fi
