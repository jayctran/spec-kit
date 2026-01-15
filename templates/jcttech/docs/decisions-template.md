# Architecture Decision Records

## Index

| ADR | Title | Status | Date | Related |
|-----|-------|--------|------|---------|

---

_No decisions recorded yet. Use `/jcttech.decision` to record architectural decisions._

---

## ADR Template

When recording a decision, use this format:

```markdown
## ADR-NNN: [Decision Title]

**Status**: proposed | accepted | deprecated | superseded
**Date**: YYYY-MM-DD
**Related Issues**: #issue1, #issue2

### Context

[Why is this decision needed? What problem does it solve?
What constraints exist?]

### Options Considered

1. **Option A** - [Brief description]
   - Pros: [Advantages]
   - Cons: [Disadvantages]

2. **Option B** - [Brief description]
   - Pros: [Advantages]
   - Cons: [Disadvantages]

### Decision

[What was decided and why? Be specific about the choice made
and the reasoning behind it.]

### Consequences

- [Positive consequence]
- [Negative consequence and how it will be mitigated]

### Architecture Impact

- **Material**: Yes/No
- **Diagram Update**: Required/Not Required
```

---

## Status Definitions

- **proposed**: Decision is under discussion, not yet finalized
- **accepted**: Decision has been made and is currently in effect
- **deprecated**: Decision is no longer recommended but may still exist in code
- **superseded**: Decision has been replaced by a newer ADR (link to it)

## When to Create an ADR

Create an ADR when making decisions about:

- Technology choices (libraries, frameworks, languages)
- Architectural patterns (microservices, monolith, etc.)
- Data storage approaches
- API design choices
- Security implementations
- Performance trade-offs
- Integration approaches

## Good ADR Practices

1. **Keep it concise**: ADRs should be readable in 5 minutes
2. **Focus on "why"**: The reasoning is more valuable than the what
3. **Link to issues**: Connect decisions to the work that drove them
4. **Update when superseded**: Don't delete old ADRs, mark them superseded
5. **Record even "obvious" decisions**: Future you will thank present you
