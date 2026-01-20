# Project Constitution

## Core Principles

Define the non-negotiable principles that guide all development on this project:

1. **[Principle 1]**: [Description of this guiding principle]
2. **[Principle 2]**: [Description of this guiding principle]
3. **[Principle 3]**: [Description of this guiding principle]

## Documentation Rules

### Architecture Updates

Documentation must stay current with the codebase:

- **On Plan**: When `/jcttech.plan` creates Stories, update `architecture.md` with:
  - New components or services
  - New integrations or dependencies
  - Changes to data flow

- **On Implement**: When `/jcttech.implement` completes, verify:
  - Architecture matches actual implementation
  - Update if implementation differs from plan
  - Record any decisions made during development

### Decision Records

All significant technical decisions must be recorded:

- Use `/jcttech.decision` to add ADRs to `decisions.md`
- Link decisions to related Epic/Spec/Story issues
- Mark architectural impact for diagram updates
- Include context, options considered, and consequences

### Diagram Updates

Update `architecture.excalidraw` when:

- New services or components are added
- Integration patterns change
- Major refactoring occurs
- Data flow is modified

Use `/jcttech.architecture` to review and regenerate documentation.

## Quality Standards

### Code Quality

- [Define code style requirements]
- [Define linting/formatting rules]
- [Define code review requirements]

### Testing Requirements

- [Define unit test coverage expectations]
- [Define integration test requirements]
- [Define E2E test requirements]

### Documentation Requirements

- [Define code documentation standards]
- [Define API documentation requirements]
- [Define README update rules]

## GitHub Configuration

### Project Board

All issues should be added to a GitHub Project for tracking:

```yaml
# Configure in .specify/config.yml
github:
  project: "PROJECT_NUMBER"
  owner: "OWNER_NAME"
  owner_type: "user|organization"
```

Use `/jcttech.setup-project` to automatically configure your GitHub Project with:
- **Status columns**: Inbox, Triaged, Planned, In Progress, In Review, Done
- **Custom fields**: Type, Area, Effort, Priority

When creating issues, the `/jcttech.*` commands will automatically add them to this project.

### Issue Types

Ensure these custom Issue Types are configured in your repository settings:
- Epic
- Spec
- Story
- Bug
- Task
- Idea

### Backlog Workflow

Ideas (backlog items) flow through the project board differently from planned work:

```
/jcttech.idea ──► Idea (Inbox)
                      │
/jcttech.triage ──────┤──► Set effort/priority (Triaged)
                      │
                      └──► Promote to Spec ──► Normal Epic→Spec→Story flow
```

**Key concepts:**
- **Ideas** can be created without a parent (exception to hierarchy rules)
- **Inbox** contains new, uncategorized backlog items
- **Triaged** contains items with effort/priority set, awaiting planning
- **Promote** converts an Idea to a proper Spec under an Epic

Use `/jcttech.triage` to periodically review and prioritize backlog items.

### Backlog Labels

The following labels are used for backlog management:

**Status:**
- `backlog` - Identifies item as unplanned/future work

**Area:**
- `area:architecture` - System design, patterns
- `area:tech-debt` - Code cleanup, maintenance
- `area:enhancement` - New features, improvements
- `area:performance` - Speed, efficiency
- `area:security` - Auth, permissions
- `area:ux` - User experience, UI
- `area:other` - Miscellaneous

**Effort:**
- `effort:xs` - Less than 2 hours
- `effort:s` - 2-4 hours
- `effort:m` - 1-2 days
- `effort:l` - 3-5 days
- `effort:xl` - 1-2 weeks

**Priority:**
- `priority:critical` - Must do immediately
- `priority:high` - Important, schedule soon
- `priority:medium` - Normal priority
- `priority:low` - Nice to have

## Issue Workflow

### Hierarchy Rules

All issues must follow the hierarchy:

```
Epic (strategic initiative)
  └── Spec (technical specification)
        └── Story (implementable unit)
              └── Tasks (checkboxes in Story)
              └── Bugs (can also attach to Spec/Epic)

Idea (backlog item - no parent required)
  └── Can be promoted to Spec via /jcttech.triage
```

### Naming Conventions

- **Epic**: `[Epic] Initiative Name`
- **Spec**: `[Spec] Feature Name`
- **Story**: `[Story] User-Facing Action`
- **Bug**: `[Bug] Brief Description`
- **Idea**: `[Idea] Brief Description`

### Issue Types

All issues use GitHub's native Type field:

- **Epic**: Top-level initiatives
- **Spec**: Technical specifications
- **Story**: Implementable work units
- **Bug**: Defects and regressions
- **Idea**: Backlog items (unplanned work)

Additional labels (priority, status, area) can be applied as needed.

## Version Control

### Branch Strategy

- [Define branch naming conventions]
- [Define merge strategy (squash, rebase, etc.)]
- [Define release process]

### Commit Messages

- [Define commit message format]
- [Define when commits should reference issues]

---

_This constitution was created using `/jcttech.specify` workflow._
_Last updated: [Date]_
