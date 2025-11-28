# Master Plan

**Status**: [DRAFT | ACTIVE | COMPLETE]
**Version**: 1.0
**Last Updated**: YYYY-MM-DD

---

## Instructions for Use

This file contains the master plan for your project. It should be:
- **Living document** - Updated as requirements and architecture evolve
- **Version controlled** - Track major iterations (v1.0, v2.0, etc.)
- **Evidence-based** - All decisions backed by CoD^Σ reasoning
- **Comprehensive** - Cover architecture, components, workflows, and metrics

---

## Project Overview

**Project Name**: [Your Project Name]

**Problem Statement**:
[What problem does this project solve? Who are the users? What are their pain points?]

**Core Innovation**:
[What makes this project unique? What is the key technical or design innovation?]

**Success Criteria**:
1. [Measurable criterion 1]
2. [Measurable criterion 2]
3. [Measurable criterion 3]

---

## Architecture (CoD^Σ)

### System Model

```
System := Component₁ ⊕ Component₂ ⊕ ... ⊕ Componentₙ
Flow := Input ≫ Processing ≫ Output
Integration := System₁ ⇄ System₂
```

### Key Components

**Component 1**: [Component Name]
- **Purpose**: What it does
- **Dependencies**: What it depends on
- **Interfaces**: How it connects to other components
- **Evidence**: Existing implementations or references

**Component 2**: [Component Name]
- **Purpose**: What it does
- **Dependencies**: What it depends on
- **Interfaces**: How it connects to other components
- **Evidence**: Existing implementations or references

### Data Flow

```
User Input → Component₁ → Component₂ → ... → Output
         ↓
    Validation
         ↓
    Processing
         ↓
     Storage
```

---

## Components (Must-Have for v1.0)

### Core Infrastructure

1. ✓ **Component Name** - Status and brief description
   - **Purpose**: What problem it solves
   - **Key Features**: Main capabilities
   - **Dependencies**: Prerequisites
   - **Status**: [PLANNED | IN_PROGRESS | COMPLETE]

2. ✓ **Component Name** - Status and brief description
   - **Purpose**: What problem it solves
   - **Key Features**: Main capabilities
   - **Dependencies**: Prerequisites
   - **Status**: [PLANNED | IN_PROGRESS | COMPLETE]

### Business Logic

1. ✓ **Component Name** - Status and brief description
2. ✓ **Component Name** - Status and brief description

### User Interface

1. ✓ **Component Name** - Status and brief description
2. ✓ **Component Name** - Status and brief description

### Integration Points

1. ✓ **Component Name** - Status and brief description
2. ✓ **Component Name** - Status and brief description

---

## Optional Components (Phase 2)

### Nice-to-Have Features

1. **Component Name** - Brief description
2. **Component Name** - Brief description

### Future Enhancements

1. **Component Name** - Brief description
2. **Component Name** - Brief description

---

## Technology Stack

### Frontend
- **Framework**: [Technology and version]
- **State Management**: [Technology and rationale]
- **UI Components**: [Technology and rationale]
- **Styling**: [Technology and approach]

### Backend
- **Runtime**: [Technology and version]
- **Framework**: [Technology and rationale]
- **Database**: [Technology and rationale]
- **Authentication**: [Technology and approach]

### Infrastructure
- **Hosting**: [Platform and rationale]
- **CI/CD**: [Tools and workflow]
- **Monitoring**: [Tools and approach]
- **Testing**: [Frameworks and strategy]

---

## File Structure

```
project-root/
├── src/
│   ├── components/     # UI components
│   ├── services/       # Business logic
│   ├── utils/          # Utilities
│   └── types/          # Type definitions
├── tests/              # Test files
├── docs/               # Documentation
├── .claude/            # Claude Code toolkit
│   ├── agents/         # Subagents
│   ├── skills/         # Skills
│   ├── commands/       # Slash commands
│   └── templates/      # Templates
└── specs/              # Feature specifications
```

---

## Development Workflow

### SDD (Specification-Driven Development)

1. **Specify** (`/feature`) - Create technology-agnostic spec.md
2. **Clarify** (automatic) - Resolve ambiguities
3. **Plan** (automatic) - Generate implementation plan with tech stack
4. **Tasks** (automatic) - Break down into user stories
5. **Audit** (automatic) - Validate consistency and quality
6. **Implement** (`/implement`) - Execute with TDD and AC verification
7. **Verify** (automatic per story) - Progressive delivery with independent validation

### Quality Gates

- **Pre-Planning**: Quality checklist validation
- **Pre-Implementation**: `/audit` cross-artifact consistency check
- **Per-Story**: `/verify --story [id]` acceptance criteria validation
- **Pre-Commit**: Linting, type checking, tests
- **Pre-Deploy**: Integration tests, security scan

---

## Phases and Milestones

### Phase 1: Foundation (Weeks 1-2)
**Goal**: Core infrastructure and basic functionality

**Milestones**:
- [ ] M1.1: Development environment setup
- [ ] M1.2: Core data models defined
- [ ] M1.3: Basic authentication working
- [ ] M1.4: Database schema deployed

**Deliverables**:
- Working development environment
- Database with core tables
- Authentication flow (login/logout)
- Basic test coverage

### Phase 2: Core Features (Weeks 3-5)
**Goal**: Primary user-facing features

**Milestones**:
- [ ] M2.1: User story P1 complete
- [ ] M2.2: User story P2 complete
- [ ] M2.3: User story P3 complete
- [ ] M2.4: Integration complete

**Deliverables**:
- All P1-P3 user stories implemented
- Comprehensive test coverage
- API documentation
- User guide

### Phase 3: Enhancement (Weeks 6-7)
**Goal**: Polish and optional features

**Milestones**:
- [ ] M3.1: Performance optimization
- [ ] M3.2: UI/UX refinement
- [ ] M3.3: Additional features
- [ ] M3.4: Production deployment

**Deliverables**:
- Performance benchmarks met
- Production-ready deployment
- Monitoring and alerts configured
- Documentation complete

---

## Success Metrics

### Technical Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Token Efficiency | 80%+ savings vs baseline | project-intel.mjs usage |
| Test Coverage | > 90% | Jest/pytest coverage |
| Build Time | < 2 minutes | CI/CD pipeline |
| API Response Time | < 200ms p95 | APM monitoring |
| Error Rate | < 0.1% | Error tracking |

### Business Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| User Adoption | [Target number] | Analytics |
| User Satisfaction | > 4.5/5 | Surveys |
| Feature Completion | 100% P1 stories | Task tracking |
| Time to Market | [Target date] | Project timeline |

---

## Risk Management

### Technical Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| [Risk description] | [H/M/L] | [H/M/L] | [Mitigation strategy] |
| [Risk description] | [H/M/L] | [H/M/L] | [Mitigation strategy] |

### Business Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| [Risk description] | [H/M/L] | [H/M/L] | [Mitigation strategy] |
| [Risk description] | [H/M/L] | [H/M/L] | [Mitigation strategy] |

---

## Dependencies

### External Dependencies

- **Dependency 1**: [Name, version, purpose]
- **Dependency 2**: [Name, version, purpose]
- **Dependency 3**: [Name, version, purpose]

### Internal Dependencies

- **Component 1** depends on **Component 2** for [reason]
- **Component 3** depends on **Component 4** for [reason]

---

## Decision Log

### Major Architectural Decisions

**Decision**: [Decision made]
- **Date**: YYYY-MM-DD
- **Rationale**: Why this decision was made
- **Alternatives**: What other options were considered
- **Evidence**: Supporting data or references
- **Impact**: How this affects the system

**Decision**: [Decision made]
- **Date**: YYYY-MM-DD
- **Rationale**: Why this decision was made
- **Alternatives**: What other options were considered
- **Evidence**: Supporting data or references
- **Impact**: How this affects the system

---

## Version History

### Version 1.0 (YYYY-MM-DD)
- Initial plan created
- Core components defined
- Architecture established

### Version 1.1 (YYYY-MM-DD)
- [Changes made]
- [New components added]
- [Architecture updates]

---

## Related Documents

- **Todo List**: @todo.md (actionable tasks)
- **Workbook**: @workbook.md (current context, patterns)
- **Event Stream**: @event-stream.md (chronological log)
- **Constitution**: @.claude/shared-imports/constitution.md (principles)
- **Specifications**: @specs/ (feature specifications)
- **Architecture**: @docs/architecture/ (detailed architecture docs)

---

## Notes

Use this section for temporary notes, questions, or observations that don't fit elsewhere. Clean up periodically.

---

**Last Review**: YYYY-MM-DD
**Next Review**: YYYY-MM-DD
**Status**: [On Track | At Risk | Blocked]
