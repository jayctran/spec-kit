---
description: Create a new Epic issue in GitHub (top-level initiative)
tools: ['github/github-mcp-server/issue_write']
scripts:
  sh: scripts/bash/jcttech/sync-issues.sh --json
  ps: scripts/powershell/check-prerequisites.ps1 -Json -PathsOnly
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Overview

This command creates a new Epic issue in GitHub. Epics are top-level initiatives that contain Specs, which contain Stories.

## Outline

1. **Parse user input** to extract:
   - Epic title/name
   - Optional overview/description
   - Optional objectives

2. **Check for existing Epics** by running sync:
   ```bash
   {SCRIPT}
   ```
   Show the user any existing epics they might want to use instead.

3. **Verify Git remote** is a GitHub URL:
   ```bash
   git config --get remote.origin.url
   ```

   > [!CAUTION]
   > ONLY PROCEED IF THE REMOTE IS A GITHUB URL

4. **Load Epic template** from `.specify/org-templates/epic.yml` if available.

5. **Generate Epic issue body**:

   ```markdown
   ## Overview

   [User-provided description or placeholder]

   ## Objectives & Goals

   - [Objective 1]
   - [Objective 2]

   ## Success Criteria

   - [ ] [Criterion 1]
   - [ ] [Criterion 2]

   ## Scope

   ### In Scope
   - [Item 1]

   ### Out of Scope
   - [Item 1]

   ## Specifications

   _Specs will be linked here as they are created._
   ```

6. **Create the Epic issue** using GitHub MCP:
   - Title: `[Epic] {title}`
   - Labels: `type:epic`
   - Body: Generated from step 5

7. **Update local index** by running sync again.

8. **Report success**:
   - Epic issue number and URL
   - Instructions to create Specs: "Use `/jcttech.specify` to create specs under this epic"

## Example

User input: "User Authentication System"

Creates:
- Title: `[Epic] User Authentication System`
- Labels: `type:epic`
- Issue body with structured sections
