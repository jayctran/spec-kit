# GitHub Setup Guide

This guide documents the manual GitHub configuration required for spec-driven development workflows.

## Issue Types

Configure these custom issue types in **Repository Settings > Features > Issues > Issue Types**:

| Type | Description |
|------|-------------|
| Epic | Top-level initiative containing multiple Specs |
| Spec | Technical specification defining a feature or change |
| Story | Implementable work unit (1-3 days), Tasks are checkboxes within Stories |
| Bug | Defect or regression |
| Idea | Backlog item (unplanned/future work) |

## GitHub Project Fields

Create these custom fields in **Project Settings > Custom Fields**:

### Status (Single-select)

The workflow status field tracks issue progression:

| Option | Description |
|--------|-------------|
| Inbox | New items, uncategorized |
| Triaged | Reviewed, effort/priority set |
| Planned | Scheduled for implementation |
| In Progress | Currently being worked on |
| In Review | PR submitted, awaiting review |
| Done | Completed |

### Area (Single-select)

Domain classification for issues:

| Option | Description |
|--------|-------------|
| architecture | Architectural changes or decisions |
| tech-debt | Technical debt reduction |
| enhancement | Feature improvements |
| performance | Performance optimizations |
| security | Security-related work |
| ux | User experience improvements |
| other | Uncategorized |

### Effort (Single-select)

Size estimate using t-shirt sizing:

| Option | Typical Duration |
|--------|------------------|
| XS | Few hours |
| S | 1 day |
| M | 2-3 days |
| L | 1 week |
| XL | 1+ weeks (consider splitting) |

### Priority (Single-select)

Importance ranking:

| Option | Description |
|--------|-------------|
| Critical | Must be done immediately |
| High | Important, should be done soon |
| Medium | Normal priority |
| Low | Nice to have, do when time permits |

## Related Backlog Items Format

When creating Specs that address backlog Ideas, include a "Related Backlog Items" section in the Spec body:

```markdown
## Related Backlog Items

| Issue | Title | Effort | Priority |
|-------|-------|--------|----------|
| #71 | Add SSO support | L | High |
| #75 | Improve auth flow | M | Medium |
```

The `idea-state-sync.yml` workflow parses this table to automatically update Idea statuses:

1. **Spec created/edited**: Ideas listed move to "planned" status
2. **Story started** (status:in-progress label): Ideas move to "in_progress" status
3. **All Stories closed**: Ideas move to "done" status and are auto-closed

## Automated Workflows

The following GitHub Actions workflows are deployed via `/jcttech.setup-project`:

### cascade-close.yml

Automatically closes parent issues when all children are complete:

- When a Story PR is merged, checks if all Stories under the parent Spec are closed
- If so, closes the Spec with a comment
- Then checks if all Specs under the parent Epic are closed
- If so, closes the Epic with a comment

### idea-state-sync.yml

Syncs Idea status based on Spec/Story lifecycle:

- **Spec created/edited**: Updates referenced Ideas to "planned"
- **Story labeled status:in-progress**: Updates Ideas to "in_progress"
- **Story closed (all complete)**: Updates Ideas to "done" and closes them

## Status Labels

While GitHub Projects uses custom fields, the workflows also use labels for status tracking:

| Label | Purpose |
|-------|---------|
| status:inbox | New, uncategorized |
| status:triaged | Reviewed, ready for planning |
| status:planned | Scheduled for work |
| status:in-progress | Currently being worked on |
| status:in-review | PR open |
| status:done | Completed |

## Quick Setup Checklist

1. [ ] Create Issue Types (Epic, Spec, Story, Bug, Idea)
2. [ ] Create GitHub Project for the repository
3. [ ] Add Status field with all options
4. [ ] Add Area field with options
5. [ ] Add Effort field (XS, S, M, L, XL)
6. [ ] Add Priority field (Critical, High, Medium, Low)
7. [ ] Run `/jcttech.setup-project` to deploy workflows and cache field IDs
8. [ ] Create status labels if using label-based tracking

## Permissions

The deployed workflows require these permissions:

```yaml
permissions:
  issues: write      # To update issue labels and close issues
  contents: read     # To checkout config files
  repository-projects: write  # To update project field values
```

These are configured in the workflow files and use `GITHUB_TOKEN` automatically provided by GitHub Actions.
