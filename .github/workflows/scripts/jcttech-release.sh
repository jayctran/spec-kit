#!/usr/bin/env bash
set -euo pipefail

# jcttech-release.sh
# JCT Tech fork wrapper for create-release-packages.sh
# This script runs the upstream release packaging and adds fork-specific files.
#
# Usage: .github/workflows/scripts/jcttech-release.sh <version>
#   Version argument should include leading 'v' (e.g., jcttech-v0.0.90)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 <version-with-v-prefix>" >&2
  echo "Example: $0 jcttech-v0.0.90" >&2
  exit 1
fi

JCTTECH_VERSION="$1"

# Extract the base version (remove 'jcttech-' prefix if present)
if [[ $JCTTECH_VERSION =~ ^jcttech-(v[0-9]+\.[0-9]+\.[0-9]+)$ ]]; then
  BASE_VERSION="${BASH_REMATCH[1]}"
elif [[ $JCTTECH_VERSION =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
  BASE_VERSION="$JCTTECH_VERSION"
  JCTTECH_VERSION="jcttech-$BASE_VERSION"
else
  echo "Version must look like jcttech-v0.0.0 or v0.0.0" >&2
  exit 1
fi

echo "Building JCT Tech fork release packages for $JCTTECH_VERSION (base: $BASE_VERSION)"

# Run the upstream release packaging script
echo "Running upstream release packaging..."
"$SCRIPT_DIR/create-release-packages.sh" "$BASE_VERSION"

# Directory where packages were created
GENRELEASES_DIR=".genreleases"

# Add JCT Tech fork-specific files to each package
echo "Adding JCT Tech fork-specific files..."

add_jcttech_files() {
  local package_dir=$1
  local agent=$2
  local script_type=$3

  echo "  Enhancing $agent ($script_type) package..."

  # Add .specify/config.yml with fork configuration
  local spec_dir="$package_dir/.specify"
  mkdir -p "$spec_dir"

  cat > "$spec_dir/config.yml" << EOF
# JCT Tech Fork Configuration
# This file configures organization template integration and issue tracking

org_templates:
  # Repository containing GitHub issue templates
  source: "jcttech/.github"
  template_path: ".github/ISSUE_TEMPLATE"
  include_pr_template: true
  enabled: true

github_mcp:
  # Enable template-aware issue creation
  use_org_templates: true

claude_settings:
  # Enable Claude Code plugin integrations
  enable_claude_mem: true
  enable_github_mcp: true

# Issue tracking configuration
issue_tracking:
  enabled: true
  auto_sync: true
  cache_issues: true
  cache_closed_days: 7

# Draft management
drafts:
  auto_validate: true
  require_parent: true

# Documentation paths and auto-update behavior
docs:
  path: ".docs"
  constitution: ".docs/constitution.md"
  architecture_md: ".docs/architecture.md"
  architecture_diagram: ".docs/architecture.excalidraw"
  decisions: ".docs/decisions.md"
  auto_update_on_plan: true
  auto_update_on_implement: true

fork:
  # Upstream tag this fork is based on
  upstream_tag: "$BASE_VERSION"
  # This fork's version tag
  fork_tag: "$JCTTECH_VERSION"
EOF

  echo "    Created .specify/config.yml"

  # Copy JCT Tech specific command templates if they exist
  if [[ -d templates/jcttech/commands ]]; then
    # Determine the agent's command directory
    local cmd_dir=""
    case $agent in
      claude) cmd_dir="$package_dir/.claude/commands" ;;
      gemini) cmd_dir="$package_dir/.gemini/commands" ;;
      copilot) cmd_dir="$package_dir/.github/agents" ;;
      cursor-agent) cmd_dir="$package_dir/.cursor/commands" ;;
      qwen) cmd_dir="$package_dir/.qwen/commands" ;;
      opencode) cmd_dir="$package_dir/.opencode/command" ;;
      windsurf) cmd_dir="$package_dir/.windsurf/workflows" ;;
      codex) cmd_dir="$package_dir/.codex/prompts" ;;
      kilocode) cmd_dir="$package_dir/.kilocode/workflows" ;;
      auggie) cmd_dir="$package_dir/.augment/commands" ;;
      roo) cmd_dir="$package_dir/.roo/rules" ;;
      codebuddy) cmd_dir="$package_dir/.codebuddy/workflows" ;;
      amp) cmd_dir="$package_dir/.agents" ;;
      shai) cmd_dir="$package_dir/.shai/commands" ;;
      q) cmd_dir="$package_dir/.amazonq/prompts" ;;
      bob) cmd_dir="$package_dir/.bob/commands" ;;
      qoder) cmd_dir="$package_dir/.qoder/prompts" ;;
    esac

    if [[ -n "$cmd_dir" ]]; then
      mkdir -p "$cmd_dir"

      # Process jcttech command templates similar to upstream
      for template in templates/jcttech/commands/*.md; do
        [[ -f "$template" ]] || continue

        local name=$(basename "$template" .md)
        local description script_command body

        # Normalize line endings
        file_content=$(tr -d '\r' < "$template")

        # Extract description from YAML frontmatter
        description=$(printf '%s\n' "$file_content" | awk '/^description:/ {sub(/^description:[[:space:]]*/, ""); print; exit}')

        # Extract script command
        script_command=$(printf '%s\n' "$file_content" | awk -v sv="$script_type" '/^[[:space:]]*'"$script_type"':[[:space:]]*/ {sub(/^[[:space:]]*'"$script_type"':[[:space:]]*/, ""); print; exit}')

        # Replace placeholders in body
        body=$(printf '%s\n' "$file_content" | sed "s|{SCRIPT}|${script_command}|g")

        # Rewrite paths
        body=$(printf '%s\n' "$body" | sed -E \
          -e 's@(/?)memory/@.specify/memory/@g' \
          -e 's@(/?)scripts/@.specify/scripts/@g' \
          -e 's@(/?)templates/@.specify/templates/@g')

        # Remove scripts sections from frontmatter
        body=$(printf '%s\n' "$body" | awk '
          /^---$/ { print; if (++dash_count == 1) in_frontmatter=1; else in_frontmatter=0; next }
          in_frontmatter && /^scripts:$/ { skip_scripts=1; next }
          in_frontmatter && /^[a-zA-Z].*:/ && skip_scripts { skip_scripts=0 }
          in_frontmatter && skip_scripts && /^[[:space:]]/ { next }
          { print }
        ')

        # Determine output format and argument placeholder based on agent
        local arg_format="\$ARGUMENTS"
        local ext="md"

        case $agent in
          gemini|qwen)
            arg_format="{{args}}"
            ext="toml"
            # Escape backslashes for TOML
            body=$(printf '%s\n' "$body" | sed 's/\\/\\\\/g')
            ;;
          copilot)
            ext="agent.md"
            ;;
        esac

        # Replace argument placeholder
        body=$(printf '%s\n' "$body" | sed "s/{ARGS}/$arg_format/g")

        # Write output file with jcttech prefix (namespace separation from upstream speckit.*)
        case $ext in
          toml)
            { echo "description = \"$description\""; echo; echo "prompt = \"\"\""; echo "$body"; echo "\"\"\""; } > "$cmd_dir/jcttech.$name.$ext"
            ;;
          md|agent.md)
            echo "$body" > "$cmd_dir/jcttech.$name.$ext"
            ;;
        esac

        echo "    Added jcttech.$name.$ext"
      done
    fi
  fi

  # Copy JCT Tech specific shell scripts
  if [[ -d scripts/bash/jcttech && "$script_type" == "sh" ]]; then
    local jcttech_scripts_dir="$package_dir/.specify/scripts/bash/jcttech"
    mkdir -p "$jcttech_scripts_dir"
    cp scripts/bash/jcttech/*.sh "$jcttech_scripts_dir/" 2>/dev/null || true
    echo "    Copied jcttech shell scripts"
  fi

  # Copy JCT Tech doc templates
  if [[ -d templates/jcttech/docs ]]; then
    local docs_templates_dir="$package_dir/.specify/templates/docs"
    mkdir -p "$docs_templates_dir"
    cp templates/jcttech/docs/*.md "$docs_templates_dir/" 2>/dev/null || true
    echo "    Copied doc templates"
  fi

  # Copy JCT Tech workflows to .specify/workflows/ for deployment via project-setup
  if [[ -d templates/jcttech/workflows ]]; then
    local workflows_dir="$package_dir/.specify/workflows"
    mkdir -p "$workflows_dir"
    for wf in templates/jcttech/workflows/*.yml; do
      [[ -f "$wf" ]] || continue
      cp "$wf" "$workflows_dir/"
      echo "    Copied workflow: $(basename "$wf")"
    done
  fi
}

# Find all generated packages and enhance them
for package_dir in "$GENRELEASES_DIR"/sdd-*-package-*; do
  [[ -d "$package_dir" ]] || continue

  # Extract agent and script type from directory name
  # Format: sdd-{agent}-package-{script}
  dir_name=$(basename "$package_dir")
  if [[ $dir_name =~ ^sdd-(.+)-package-(sh|ps)$ ]]; then
    agent="${BASH_REMATCH[1]}"
    script_type="${BASH_REMATCH[2]}"
    add_jcttech_files "$package_dir" "$agent" "$script_type"
  fi
done

# Rename the zip files to use jcttech version
echo "Renaming release packages to JCT Tech version..."
for zip_file in "$GENRELEASES_DIR"/*.zip; do
  [[ -f "$zip_file" ]] || continue

  # Replace base version with jcttech version in filename
  new_name=$(basename "$zip_file" | sed "s/$BASE_VERSION/$JCTTECH_VERSION/g")
  if [[ "$new_name" != "$(basename "$zip_file")" ]]; then
    mv "$zip_file" "$GENRELEASES_DIR/$new_name"
    echo "  Renamed to $new_name"
  fi
done

echo ""
echo "JCT Tech fork release packages built successfully!"
echo "Packages available in: $GENRELEASES_DIR/"
ls -la "$GENRELEASES_DIR"/*.zip 2>/dev/null | head -20 || echo "No zip files found"
