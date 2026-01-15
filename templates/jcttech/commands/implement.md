---
description: Pull Story from GitHub, execute tasks, check off progress, update docs if needed
tools: ['github/github-mcp-server/issue_read', 'github/github-mcp-server/issue_write']
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

This command implements a Story by:
1. Pulling the Story issue from GitHub
2. Working through each task checkbox
3. Updating the issue as tasks complete
4. Optionally updating architecture/decisions docs

## Outline

1. **Select Story to implement**:
   - If user provides Story number (e.g., "#102"), use that
   - Otherwise, list open Stories from index:
     ```bash
     gh issue list --label type:story --state open --json number,title,assignees
     ```
   - Show Stories with their task counts

2. **Fetch Story details**:
   ```bash
   gh issue view {story_number} --json number,title,body,state,labels
   ```

3. **Parse tasks from Story body**:
   - Extract checkbox items: `- [ ] Task description`
   - Track which are already completed: `- [x] Done task`
   - Display task list to user

4. **Work through tasks sequentially**:

   For each unchecked task:
   a. Display the task description
   b. Implement the task (write code, tests, etc.)
   c. After completing, update the GitHub issue:
      ```bash
      gh issue edit {story_number} --body "{updated_body_with_checked_task}"
      ```
   d. Optionally commit progress

5. **Check for architecture changes**:

   After implementation, ask:
   - Did implementation introduce new components?
   - Did implementation change data flow?
   - Were there decisions made during implementation?

   If yes to any:
   - Prompt to update `.docs/architecture.md`
   - Prompt to record decision with `/jcttech.decision`

6. **When all tasks complete**:
   - Close the Story issue or change status label
   - Update index via sync
   - Report completion summary

## Task Workflow Example

```
Story #102: Implement JWT Token Service

Tasks:
[1/4] - [ ] Create JWTService class with sign/verify methods
[2/4] - [ ] Add token validation middleware
[3/4] - [ ] Implement refresh token flow
[4/4] - [ ] Write unit tests

Current task: Create JWTService class with sign/verify methods

Working on this task...
[Implementation happens]

Task complete! Updating GitHub issue...
✓ Task 1/4 checked off

Continue to next task? [Y/n]
```

## GitHub Issue Update

When checking off a task, the issue body is updated:

Before:
```markdown
## Tasks
- [ ] Create JWTService class
- [ ] Add token validation middleware
```

After:
```markdown
## Tasks
- [x] Create JWTService class
- [ ] Add token validation middleware
```

## Documentation Updates

At the end of implementation (or periodically), check if docs need updates:

1. **Architecture changes detected?**
   - New files in unexpected locations
   - New service classes
   - New API endpoints
   → Offer to update `.docs/architecture.md`

2. **Decisions made?**
   - Library choices
   - Design pattern choices
   - Trade-off decisions
   → Offer to run `/jcttech.decision`

3. **Implementation differs from plan?**
   - Compare actual implementation with Story description
   → Note differences in architecture.md

## Completion

When Story is complete:
```
Story #102 Complete!

Summary:
- 4/4 tasks completed
- Files created: 3
- Files modified: 2
- Tests added: 12

Documentation:
- architecture.md: Updated with AuthService component
- decisions.md: ADR-003 added (jose library choice)

Story #102 marked as closed.

Next Stories in Spec #101:
- #103 [Story] Create Login Endpoint (3 tasks)
- #104 [Story] Add Token Refresh Flow (3 tasks)
```
