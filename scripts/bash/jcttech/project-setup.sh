#!/usr/bin/env bash
# Setup GitHub Project board for spec-driven development
# Usage: project-setup.sh [--json] [--project NUMBER] [--create NAME]

set -e

# Source common functions
source "$(dirname "${BASH_SOURCE[0]}")/common-jcttech.sh"

# Parse arguments
JSON_MODE=false
PROJECT_NUMBER=""
CREATE_NAME=""
ADD_STATUS_OPTIONS=false
CREATE_FIELDS=false
DEPLOY_WORKFLOWS=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        --json)
            JSON_MODE=true
            shift
            ;;
        --project)
            PROJECT_NUMBER="$2"
            shift 2
            ;;
        --create)
            CREATE_NAME="$2"
            shift 2
            ;;
        --add-status-options)
            ADD_STATUS_OPTIONS=true
            shift
            ;;
        --create-fields)
            CREATE_FIELDS=true
            shift
            ;;
        --deploy-workflows)
            DEPLOY_WORKFLOWS=true
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

# Extract owner from repo (could be user or org)
OWNER=$(echo "$REPO" | cut -d'/' -f1)
REPO_NAME=$(echo "$REPO" | cut -d'/' -f2)

REPO_ROOT=$(get_repo_root)
CONFIG_DIR="$REPO_ROOT/.specify"
CONFIG_FILE="$CONFIG_DIR/config.yml"
FIELDS_FILE="$CONFIG_DIR/project-fields.yml"

mkdir -p "$CONFIG_DIR"

# Determine owner type (user or organization)
get_owner_type() {
    local owner="$1"
    # Try to get org info - if it fails, it's a user
    if gh api "orgs/$owner" &>/dev/null; then
        echo "organization"
    else
        echo "user"
    fi
}

# Get project node ID
get_project_node_id() {
    local owner="$1"
    local project_num="$2"
    local owner_type=$(get_owner_type "$owner")

    if [[ "$owner_type" == "organization" ]]; then
        gh api graphql -f query='
            query($org: String!, $num: Int!) {
                organization(login: $org) {
                    projectV2(number: $num) {
                        id
                    }
                }
            }
        ' -f org="$owner" -F num="$project_num" --jq '.data.organization.projectV2.id' 2>/dev/null
    else
        gh api graphql -f query='
            query($user: String!, $num: Int!) {
                user(login: $user) {
                    projectV2(number: $num) {
                        id
                    }
                }
            }
        ' -f user="$owner" -F num="$project_num" --jq '.data.user.projectV2.id' 2>/dev/null
    fi
}

# Get field ID by name
get_field_id() {
    local project_id="$1"
    local field_name="$2"

    gh api graphql -f query='
        query($projectId: ID!) {
            node(id: $projectId) {
                ... on ProjectV2 {
                    fields(first: 20) {
                        nodes {
                            ... on ProjectV2Field {
                                id
                                name
                            }
                            ... on ProjectV2SingleSelectField {
                                id
                                name
                            }
                        }
                    }
                }
            }
        }
    ' -f projectId="$project_id" --jq ".data.node.fields.nodes[] | select(.name == \"$field_name\") | .id" 2>/dev/null
}

# Get Status field with options
get_status_field() {
    local project_id="$1"

    gh api graphql -f query='
        query($projectId: ID!) {
            node(id: $projectId) {
                ... on ProjectV2 {
                    fields(first: 20) {
                        nodes {
                            ... on ProjectV2SingleSelectField {
                                id
                                name
                                options {
                                    id
                                    name
                                }
                            }
                        }
                    }
                }
            }
        }
    ' -f projectId="$project_id" --jq '.data.node.fields.nodes[] | select(.name == "Status")' 2>/dev/null
}

# Create a single-select field
create_single_select_field() {
    local project_id="$1"
    local field_name="$2"
    shift 2
    local options=("$@")

    # Build options JSON
    local options_json="["
    local first=true
    for opt in "${options[@]}"; do
        if ! $first; then
            options_json+=","
        fi
        options_json+="{\"name\":\"$opt\"}"
        first=false
    done
    options_json+="]"

    gh api graphql -f query='
        mutation($projectId: ID!, $name: String!) {
            createProjectV2Field(input: {
                projectId: $projectId
                dataType: SINGLE_SELECT
                name: $name
            }) {
                projectV2Field {
                    ... on ProjectV2SingleSelectField {
                        id
                        name
                    }
                }
            }
        }
    ' -f projectId="$project_id" -f name="$field_name" 2>/dev/null
}

# Add option to single-select field
add_field_option() {
    local project_id="$1"
    local field_id="$2"
    local option_name="$3"
    local color="${4:-GRAY}"

    gh api graphql -f query='
        mutation($projectId: ID!, $fieldId: ID!, $name: String!, $color: ProjectV2SingleSelectFieldOptionColor!) {
            updateProjectV2Field(input: {
                projectId: $projectId
                fieldId: $fieldId
                singleSelectOptions: [{name: $name, color: $color}]
            }) {
                projectV2Field {
                    ... on ProjectV2SingleSelectField {
                        id
                    }
                }
            }
        }
    ' -f projectId="$project_id" -f fieldId="$field_id" -f name="$option_name" -f color="$color" 2>/dev/null
}

# Get all fields with their options for caching
get_all_fields() {
    local project_id="$1"

    gh api graphql -f query='
        query($projectId: ID!) {
            node(id: $projectId) {
                ... on ProjectV2 {
                    fields(first: 30) {
                        nodes {
                            ... on ProjectV2SingleSelectField {
                                id
                                name
                                options {
                                    id
                                    name
                                }
                            }
                        }
                    }
                }
            }
        }
    ' -f projectId="$project_id" 2>/dev/null
}

# Save configuration files
save_config() {
    local project_num="$1"
    local owner="$2"
    local owner_type="$3"

    cat > "$CONFIG_FILE" << EOF
# Spec-kit configuration
# Generated by /jcttech.setup-project

github:
  project: "$project_num"
  owner: "$owner"
  owner_type: "$owner_type"
EOF
    echo "Saved: $CONFIG_FILE"
}

# Save field IDs cache
save_fields_cache() {
    local project_id="$1"
    local fields_json="$2"

    cat > "$FIELDS_FILE" << EOF
# Auto-generated by /jcttech.setup-project
# Do not edit manually - re-run setup to refresh

project_id: "$project_id"
fields:
EOF

    # Parse fields and write to YAML
    echo "$fields_json" | jq -r '
        .data.node.fields.nodes[] |
        select(.options != null) |
        "  \(.name | ascii_downcase | gsub(" "; "_")):\n    id: \"\(.id)\"\n    options:" +
        ([.options[] | "      \(.name | ascii_downcase | gsub(" "; "_")): \"\(.id)\""] | join("\n"))
    ' >> "$FIELDS_FILE"

    echo "Saved: $FIELDS_FILE"
}

# Main execution
OWNER_TYPE=$(get_owner_type "$OWNER")

# Create or get project
if [[ -n "$CREATE_NAME" ]]; then
    echo "Creating project: $CREATE_NAME"
    PROJECT_NUMBER=$(gh project create --owner "$OWNER" --title "$CREATE_NAME" --format json | jq -r '.number')
    echo "Created project #$PROJECT_NUMBER"
elif [[ -z "$PROJECT_NUMBER" ]]; then
    # Check existing config
    if [[ -f "$CONFIG_FILE" ]]; then
        PROJECT_NUMBER=$(grep "project:" "$CONFIG_FILE" | sed 's/.*project: *//' | tr -d '"')
        if [[ -n "$PROJECT_NUMBER" ]]; then
            echo "Using configured project #$PROJECT_NUMBER"
        fi
    fi

    if [[ -z "$PROJECT_NUMBER" ]]; then
        echo "ERROR: No project specified. Use --project NUMBER or --create NAME" >&2
        exit 1
    fi
fi

# Get project node ID
PROJECT_ID=$(get_project_node_id "$OWNER" "$PROJECT_NUMBER")
if [[ -z "$PROJECT_ID" || "$PROJECT_ID" == "null" ]]; then
    echo "ERROR: Could not find project #$PROJECT_NUMBER for $OWNER" >&2
    exit 1
fi

echo "Project ID: $PROJECT_ID"

# Link repository to project
echo "Linking repository $REPO to project..."
gh project link "$PROJECT_NUMBER" --owner "$OWNER" --repo "$REPO" 2>/dev/null || true

# Get and cache all fields
echo "Fetching project fields..."
FIELDS_JSON=$(get_all_fields "$PROJECT_ID")

# Save configuration
save_config "$PROJECT_NUMBER" "$OWNER" "$OWNER_TYPE"
save_fields_cache "$PROJECT_ID" "$FIELDS_JSON"

# Deploy GitHub Actions workflows if requested
WORKFLOWS_DEPLOYED=()
if $DEPLOY_WORKFLOWS; then
    echo ""
    echo "Deploying GitHub Actions workflows..."

    WORKFLOW_SOURCE="$REPO_ROOT/.specify/workflows"
    WORKFLOW_DEST="$REPO_ROOT/.github/workflows"

    if [[ -d "$WORKFLOW_SOURCE" ]]; then
        mkdir -p "$WORKFLOW_DEST"
        for wf in "$WORKFLOW_SOURCE"/*.yml; do
            [[ -f "$wf" ]] || continue
            local_name=$(basename "$wf")
            if [[ -f "$WORKFLOW_DEST/$local_name" ]]; then
                echo "  Skipping $local_name (already exists)"
            else
                cp "$wf" "$WORKFLOW_DEST/$local_name"
                echo "  Deployed: $local_name"
                WORKFLOWS_DEPLOYED+=("$local_name")
            fi
        done
    else
        echo "  No workflow templates found at $WORKFLOW_SOURCE"
    fi
fi

# Output result
if $JSON_MODE; then
    # Build workflows array for JSON output
    WORKFLOWS_JSON="[]"
    if [ ${#WORKFLOWS_DEPLOYED[@]} -gt 0 ]; then
        WORKFLOWS_JSON=$(printf '%s\n' "${WORKFLOWS_DEPLOYED[@]}" | jq -R . | jq -s .)
    fi

    cat << EOF
{
  "project_number": "$PROJECT_NUMBER",
  "project_id": "$PROJECT_ID",
  "owner": "$OWNER",
  "owner_type": "$OWNER_TYPE",
  "config_file": "$CONFIG_FILE",
  "fields_file": "$FIELDS_FILE",
  "workflows_deployed": $WORKFLOWS_JSON
}
EOF
else
    echo ""
    echo "Project setup complete!"
    echo "  Project: #$PROJECT_NUMBER"
    echo "  Owner: $OWNER ($OWNER_TYPE)"
    echo "  Config: $CONFIG_FILE"
    echo "  Fields: $FIELDS_FILE"
    if [ ${#WORKFLOWS_DEPLOYED[@]} -gt 0 ]; then
        echo "  Workflows deployed: ${WORKFLOWS_DEPLOYED[*]}"
    fi
    echo ""
    echo "Note: Custom fields (Type, Area, Effort, Priority) should be created"
    echo "manually in the GitHub Project settings, or they will use labels instead."
fi
