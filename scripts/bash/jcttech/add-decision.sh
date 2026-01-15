#!/usr/bin/env bash
# Add an Architecture Decision Record to decisions.md
# Usage: add-decision.sh --title "Decision Title" [--status accepted|proposed] [--related "#123, #456"]

set -e

# Source common functions
source "$(dirname "${BASH_SOURCE[0]}")/common-jcttech.sh"

# Parse arguments
JSON_MODE=false
TITLE=""
STATUS="proposed"
RELATED=""
CONTEXT=""
DECISION=""
MATERIAL="No"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --json)
            JSON_MODE=true
            shift
            ;;
        --title)
            TITLE="$2"
            shift 2
            ;;
        --status)
            STATUS="$2"
            shift 2
            ;;
        --related)
            RELATED="$2"
            shift 2
            ;;
        --context)
            CONTEXT="$2"
            shift 2
            ;;
        --decision)
            DECISION="$2"
            shift 2
            ;;
        --material)
            MATERIAL="Yes"
            shift
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

# Validate
if [[ -z "$TITLE" ]]; then
    echo "ERROR: Title is required" >&2
    echo "Usage: add-decision.sh --title \"Decision Title\" [--status accepted] [--related \"#123\"]" >&2
    exit 1
fi

# Setup paths
DOCS_PATH=$(get_docs_path)
DECISIONS_FILE="$DOCS_PATH/decisions.md"

# Ensure file exists
if [[ ! -f "$DECISIONS_FILE" ]]; then
    mkdir -p "$DOCS_PATH"
    cat > "$DECISIONS_FILE" << 'EOF'
# Architecture Decision Records

## Index

| ADR | Title | Status | Date | Related |
|-----|-------|--------|------|---------|

---

EOF
fi

# Get next ADR number
get_next_adr_number() {
    local highest=0
    while IFS= read -r line; do
        if [[ "$line" =~ ^##\ ADR-([0-9]+): ]]; then
            local num="${BASH_REMATCH[1]}"
            num=$((10#$num))
            [[ "$num" -gt "$highest" ]] && highest=$num
        fi
    done < "$DECISIONS_FILE"
    printf "%03d" $((highest + 1))
}

ADR_NUM=$(get_next_adr_number)
TODAY=$(date +%Y-%m-%d)
TIMESTAMP=$(get_iso_timestamp)

# Add entry to index table
# Find the line after the table header and insert new row
INDEX_ENTRY="| $ADR_NUM | $TITLE | $STATUS | $TODAY | ${RELATED:-"-"} |"

# Insert into index table (after the header row)
sed -i "/^|-----|/a $INDEX_ENTRY" "$DECISIONS_FILE"

# Append ADR at the end
cat >> "$DECISIONS_FILE" << EOF

---

## ADR-${ADR_NUM}: ${TITLE}

**Status**: ${STATUS}
**Date**: ${TODAY}
**Related Issues**: ${RELATED:-"None"}

### Context

${CONTEXT:-"[Why is this decision needed?]"}

### Options Considered

1. **Option A** - [Description, Pros, Cons]
2. **Option B** - [Description, Pros, Cons]

### Decision

${DECISION:-"[What was decided and why]"}

### Consequences

- [Positive and negative consequences of this decision]

### Architecture Impact

- **Material**: ${MATERIAL}
- **Diagram Update**: $([ "$MATERIAL" = "Yes" ] && echo "Required" || echo "Not Required")
EOF

# Output result
if $JSON_MODE; then
    cat << EOF
{
  "adr_number": "${ADR_NUM}",
  "title": "${TITLE}",
  "status": "${STATUS}",
  "date": "${TODAY}",
  "file": "${DECISIONS_FILE}",
  "material": "${MATERIAL}"
}
EOF
else
    echo "ADR-${ADR_NUM} added: ${TITLE}"
    echo "File: ${DECISIONS_FILE}"
    if [[ "$MATERIAL" == "Yes" ]]; then
        echo "Note: This decision has architecture impact - consider updating architecture.excalidraw"
    fi
fi
