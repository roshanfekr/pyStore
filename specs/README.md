# Software Design and Development (SDD)

## 1. Purpose

This directory contains the specifications, architectural decisions, technical contracts, and implementation plans for the project.

The purpose of this documentation is to ensure that development is:
- Requirements-driven.
- Consistent with approved project decisions.
- Incremental and verifiable.
- Maintainable and extensible.
- Suitable for AI-assisted development without uncontrolled changes.

**The specifications define the intended behavior of the system. The existing source code defines the current implementation.** When they disagree, the discrepancy must be investigated rather than resolved by silently changing either one.

## 2. Project Context

This project is an extensible, plugin-based e-commerce platform implemented primarily with Python and Django.

The project may include a separate frontend application, a REST API, product management, product combinations, pricing, inventory, shopping cart, checkout, orders, payment integration, and administrative functionality.

The authoritative requirements and approved technology decisions are defined in `PROJECT_SCOPE.md` and the relevant approved specifications.

Do not infer or introduce additional requirements merely because they are common in other e-commerce platforms.

## 3. Documentation Structure

The following structure defines the intended organization of project documentation.

```text
specs/
├── README.md
├── PROJECT_SCOPE.md
├── REQUIREMENTS.md
├── ARCHITECTURE.md
├── DATA_MODEL.md
├── API_SPEC.md
├── UI_UX_SPEC.md
├── PLUGIN_SYSTEM.md
├── SECURITY.md
├── TEST_STRATEGY.md
├── DEPLOYMENT.md
├── IMPLEMENTATION_PLAN.md
├── decisions/
│   └── ADR-001-example.md
└── features/
    ├── catalog/
    │   ├── requirements.md
    │   ├── data-model.md
    │   ├── api-spec.md
    │   └── ui-spec.md
    ├── cart/
    │   ├── requirements.md
    │   ├── api-spec.md
    │   └── ui-spec.md
    ├── checkout/
    ├── orders/
    ├── payments/
    └── customers/
```

This is the target structure, not a declaration that every file already exists.

Create a document only when it is needed for the current approved phase. Do not generate all documents with speculative or placeholder requirements.

## 4. Document Responsibilities

### 4.1. PROJECT_SCOPE.md

Defines the approved project scope, objectives, boundaries, major capabilities, and high-level constraints.

This document is the authoritative baseline for project scope.

Do not modify its approved content without explicit user authorization.

### 4.2. REQUIREMENTS.md

Defines functional and non-functional requirements, including:
- Unique requirement identifiers.
- Requirement descriptions.
- Acceptance criteria.
- Priorities where applicable.
- Dependencies and constraints.

Detailed feature requirements may be maintained in the corresponding `features/` directory.

### 4.3. ARCHITECTURE.md

Defines system architecture, application boundaries, major components, dependencies, and communication patterns.

It must be consistent with the approved project scope and architecture decisions.

### 4.4. DATA_MODEL.md

Defines entities, relationships, constraints, data ownership, and important business invariants.

Feature-specific data structures may be documented in the corresponding feature directory.

### 4.5. API_SPEC.md

Defines API contracts, endpoints, HTTP methods, request and response schemas, authentication requirements, error handling, and versioning rules where applicable.

Feature-specific API contracts may be documented in `features/<feature>/api-spec.md`.

### 4.6. UI_UX_SPEC.md

Defines global UI conventions, design principles, navigation, accessibility, responsive behavior, and reusable interface patterns.

Feature-specific screen layouts and interactions belong in the relevant feature's `ui-spec.md`.

### 4.7. PLUGIN_SYSTEM.md

Defines plugin boundaries, extension points, registration and discovery mechanisms, lifecycle, configuration, dependencies, and compatibility rules.

Do not introduce a plugin mechanism without documenting its intended contract and obtaining the required approval.

### 4.8. SECURITY.md

Defines security requirements, authentication and authorization rules, validation, secrets management, data protection, and security testing expectations.

### 4.9. TEST_STRATEGY.md

Defines the testing approach, test levels, quality gates, regression requirements, and acceptance verification.

### 4.10. DEPLOYMENT.md

Defines supported environments, configuration, deployment prerequisites, migrations, operational requirements, and rollback considerations.

### 4.11. IMPLEMENTATION_PLAN.md

Defines approved development phases, dependencies, deliverables, completion criteria, and current phase status.

### 4.12. decisions/

Contains Architecture Decision Records (ADRs).

Each ADR should explain:
- The context and problem.
- The decision.
- The alternatives considered.
- The rationale.
- The consequences and trade-offs.
- The decision status.

Use sequential identifiers such as `ADR-001`, `ADR-002`, and so on.

Do not use an ADR to silently override an approved project requirement.

### 4.13. features/

Contains detailed specifications for individual features.

Create feature documents as needed. A feature specification should define its behavior, constraints, relevant data, interfaces, user interactions, and acceptance criteria as appropriate.

## 5. Authority and Conflict Resolution

When working on the project, follow these rules:

1. Preserve explicitly approved project decisions.
2. Use `PROJECT_SCOPE.md` as the baseline for approved project scope.
3. Follow approved architecture decisions and applicable feature specifications.
4. Treat unapproved proposals and drafts as proposals, not implementation requirements.
5. Treat the source code as evidence of current behavior, not automatic proof that the behavior is intended.
6. If documents conflict, identify the conflicting statements and request clarification when the conflict affects the implementation.
7. Never silently resolve a significant architectural, business, security, or compatibility conflict.
8. Record approved changes in the relevant specification and, when appropriate, an ADR.

If the required document does not exist, do not invent its approved contents. Determine whether the current task can proceed safely; otherwise, request approval to create the missing specification.

## 6. AI Agent Operating Rules

Any AI coding agent working on this project must follow these rules.

### 6.1. Before Making Changes

Before modifying source code, configuration, database models, API contracts, or dependencies:

1. Read this document.
2. Read `PROJECT_SCOPE.md`.
3. Read the applicable sections of `IMPLEMENTATION_PLAN.md`, if available.
4. Read the relevant architecture, feature, API, data-model, UI, and security specifications.
5. Inspect the existing implementation and identify affected components.
6. Check for uncommitted user changes and avoid overwriting them.
7. Identify missing requirements, contradictions, and implementation risks.

Do not read or modify unrelated components unless required by the approved task.

### 6.2. Scope Control

The agent must:
- Implement only the explicitly approved task.
- Avoid unrelated refactoring and feature additions.
- Preserve existing behavior unless a change is approved.
- Avoid unnecessary dependencies.
- Follow the existing project conventions unless they conflict with an approved requirement.
- Never replace an existing architecture merely because another architecture appears preferable.

If the requested implementation requires changes outside the approved scope, explain why and request approval before proceeding.

### 6.3. Clarification and Approval

Ask the user for clarification before implementation when:
- A business rule is ambiguous.
- Two authoritative specifications conflict.
- An architectural decision has not been approved.
- A change would alter an external contract or break compatibility.
- A security-sensitive behavior is not sufficiently specified.
- The implementation requires a significant change in scope.

Do not ask unnecessary questions when the approved specifications already provide the answer.

### 6.4. Implementation and Verification

For each approved implementation task:

1. Identify the relevant requirements and acceptance criteria.
2. Plan the smallest appropriate set of changes.
3. Implement the approved behavior.
4. Add or update tests as required.
5. Run relevant tests and validation checks.
6. Report any tests that could not be run and explain why.
7. Update affected documentation when the approved implementation changes documented behavior.
8. Summarize modified files, decisions, test results, and known limitations.

Never claim that a test passed unless it was actually executed and passed.

Never claim that a feature is complete if its acceptance criteria remain unmet.

### 6.5. Documentation Updates

Keep documentation consistent with approved implementation changes.

When updating a specification:
- Preserve unrelated approved content.
- Identify material changes.
- Update affected references when necessary.
- Do not turn an implementation assumption into an approved requirement.
- Do not rewrite `PROJECT_SCOPE.md` without explicit authorization.

If a proposed documentation update requires approval, present the proposed change before applying it.

## 7. Phase-Gate Workflow

Development follows explicit approval gates.

### Phase 1: Scope

Establish and approve the project scope.

**Completion condition:** The scope document is explicitly approved by the user.

### Phase 2: Requirements

Define functional and non-functional requirements based on the approved scope.

**Completion condition:** The relevant requirements are reviewed and approved.

### Phase 3: Architecture

Define system boundaries, component responsibilities, technology decisions, and integration patterns.

**Completion condition:** The architecture and significant decisions are approved.

### Phase 4: Detailed Design

Specify the required data models, APIs, UI behavior, plugin contracts, security rules, and feature-level details.

**Completion condition:** The specifications required for the next implementation task are approved.

### Phase 5: Implementation

Implement only the approved features and tasks.

**Completion condition:** The task's acceptance criteria and required verification checks are satisfied.

### Phase 6: Review and Maintenance

Review test results, documentation consistency, regressions, and remaining issues.

**Completion condition:** The user accepts the deliverable or explicitly authorizes the next phase.

These phases are logical gates, not a requirement to finish every possible feature document before any implementation begins.

The user may approve a limited feature or implementation slice independently, provided its dependencies and required specifications are sufficiently defined.

**An AI agent must not advance to the next approval-gated phase without explicit user approval.**

## 8. Requirements and Traceability

Use stable identifiers for requirements and important acceptance criteria.

Examples:

- `FR-CART-001`: A customer can view cart items.
- `FR-CART-002`: A customer can update item quantities.
- `FR-CART-003`: The system validates the selected product combination and availability.
- `NFR-SEC-001`: The system validates security-sensitive operations on the server.

These are illustrative identifier examples, not approved requirements.

Where practical, connect requirements to:
- Feature specifications.
- Architecture or API decisions.
- Implementation tasks.
- Automated tests.
- Acceptance results.

Do not create traceability references that do not exist.

## 9. Change Management

When a new request affects an approved specification:

1. Identify the affected documents and requirements.
2. Explain the impact on scope, architecture, data, APIs, UI, security, and tests as applicable.
3. Separate the requested change from unrelated improvements.
4. Present the proposed specification changes when approval is required.
5. Obtain the necessary approval.
6. Update the approved specifications.
7. Implement the change within the approved boundaries.
8. Verify the implementation and update relevant tests.

For a correction that does not change approved behavior, make the smallest appropriate change and preserve unrelated content.

## 10. Definition of Done

A task is considered complete only when its applicable completion conditions are satisfied:

- The implementation matches the approved requirements.
- Relevant acceptance criteria are met.
- Appropriate tests and validation checks have been executed.
- Existing behavior and unrelated changes have been protected.
- Security and data-integrity requirements are respected.
- Relevant documentation is consistent with the approved implementation.
- Remaining limitations and unverified behavior are disclosed.
- The final report identifies the changes and verification results.

User acceptance remains separate from technical completion whenever the workflow requires an explicit approval gate.

## 11. Initial Project Onboarding

Before starting new development using this documentation structure:

1. Inspect the repository structure.
2. Locate and read the approved `PROJECT_SCOPE.md`.
3. Identify the current frontend, backend, database, and plugin architecture from available evidence.
4. Review the existing implementation and identify completed, partial, and missing features.
5. Compare the implementation against the approved scope.
6. Report discrepancies and unresolved architectural decisions.
7. Propose a prioritized documentation plan.
8. Request approval before making significant architectural or scope changes.

Do not regenerate an existing project from scratch merely because its documentation is incomplete.

## 12. Current Documentation Status

The existence of this README does not imply that every planned specification has been created, reviewed, or approved.

Track the status of individual documents and phases in `IMPLEMENTATION_PLAN.md` when that file is established.

Use explicit status labels where appropriate:

- `Draft`
- `In Review`
- `Approved`
- `Implemented`
- `Superseded`

Only mark a document `Approved` when the user has explicitly approved it.

**Current status (2026-10-20):** The project is at the scope/requirements
approval gate. `PROJECT_SCOPE.md` and `REQUIREMENTS.md` are in final review,
pending explicit user approval. A first draft of `ARCHITECTURE.md` (v0.1,
Draft — proposed for review, not approved) has been created for the
architecture phase; no other specification documents exist yet. Architecture
approval must not be assumed from the draft's existence, and detailed design
and implementation must not begin until the scope/requirements approval is
given and the next phase is authorized.

---

**End of document.**