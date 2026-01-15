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

## Issue Workflow

### Hierarchy Rules

All issues must follow the hierarchy:

```
Epic (strategic initiative)
  └── Spec (technical specification)
        └── Story (implementable unit)
              └── Tasks (checkboxes in Story)
              └── Bugs (can also attach to Spec/Epic)
```

### Naming Conventions

- **Epic**: `[Epic] Initiative Name`
- **Spec**: `[Spec] Feature Name`
- **Story**: `[Story] User-Facing Action`
- **Bug**: `[Bug] Brief Description`

### Labels

Required labels for all issues:

- `type:epic`, `type:spec`, `type:story`, or `type:bug`
- Additional labels as appropriate (priority, area, etc.)

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
