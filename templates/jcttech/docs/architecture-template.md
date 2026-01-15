# Architecture Overview

## System Components

Document your system's major components:

### Core Services

- **[ServiceName]**: [Brief description of responsibility]
- **[ServiceName]**: [Brief description of responsibility]

### Controllers/Handlers

- **[ControllerName]**: [Endpoints or events handled]

### Data Access

- **[RepositoryName]**: [Data entities managed]

## Data Flow

Describe how data flows through your system:

```
[Client] → [API Gateway] → [Service Layer] → [Database]
                                          → [Cache]
                                          → [External APIs]
```

## External Integrations

| Service | Purpose | Connection Method |
|---------|---------|------------------|
| [Service] | [Purpose] | REST API / SDK / etc |

## Technology Stack

- **Language**: [e.g., TypeScript, Python]
- **Framework**: [e.g., Express, FastAPI]
- **Database**: [e.g., PostgreSQL, MongoDB]
- **Cache**: [e.g., Redis]
- **Infrastructure**: [e.g., AWS, GCP, Docker]

## Key Design Decisions

Link to relevant ADRs:

- [ADR-001: Decision Title](decisions.md#adr-001-decision-title)
- [ADR-002: Decision Title](decisions.md#adr-002-decision-title)

## Diagrams

See `architecture.excalidraw` for visual representations:

- System overview diagram
- Data flow diagram
- Component interaction diagram

## Security Considerations

- [Authentication method]
- [Authorization approach]
- [Data encryption]

## Scalability

- [Horizontal scaling approach]
- [Caching strategy]
- [Database scaling plan]

---

_Last updated: [Date]_
_Generated/updated by `/jcttech.architecture`_
