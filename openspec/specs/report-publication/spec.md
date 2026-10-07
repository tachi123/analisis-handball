# Report Publication Specification

## Purpose

Define safe, repeatable publication of intentionally public SAPA reports from local analytical records.

## Requirements

### Requirement: Publish only a curated public projection

The system MUST publish a curated projection, excluding credentials, raw events, private notes, unapproved links, and database details. Google MUST remain credential-gated. A local file publisher MAY be selected only by explicit local-development configuration, MUST be rejected elsewhere, and MUST expose its exact projection through an anonymous local reader.

#### Scenario: Public report projection

- GIVEN the local analyst approves a report package for publication
- WHEN publication is requested
- THEN only fields allowed by the public report schema are sent to the public Sheet

#### Scenario: Restricted evidence

- GIVEN a package contains a private note or media link not approved for public publication
- WHEN the public projection is generated
- THEN the restricted field is omitted while the local package remains unchanged

### Requirement: Record the published report schema

The system MUST record the schema version, package report version, and publication time with each publication result. It MUST NOT require globally monotonic versions or immutable replacement lineage for local testing.

#### Scenario: Schema version recorded

- GIVEN a report uses the current public report schema
- WHEN it is published
- THEN the recorded result identifies the schema version, report version, and publication time

### Requirement: Publish idempotently

The system MUST make repeated publication of the same package idempotent for one local operator: the provider projection MUST converge to that package and its publication record MUST NOT duplicate. A later Publish or Re-publish request for another approved, recovery-ready package MUST directly replace the current public projection. The system MUST NOT reject a request because another package was published earlier.

#### Scenario: Retry publication

- GIVEN the current report version is retried
- WHEN its package/version publishes again
- THEN one projection and record remain

#### Scenario: Re-publish replaces current projection

- GIVEN one package is already public
- WHEN the local operator publishes another approved, recovery-ready package
- THEN the second package replaces the current public projection

### Requirement: Create recovery artifacts before publication

The analyst owns recovery. Before publication, the system MUST require a PostgreSQL dump and imported-PDF export for the source match. It MUST record entered locations as operator-attested, MUST NOT claim verification. The runbook MUST define backup cadence.

#### Scenario: Missing pre-publication export

- GIVEN the required PostgreSQL dump or imported-PDF export has not been completed
- WHEN the analyst attempts publication
- THEN publication is blocked with the missing recovery artifact identified

#### Scenario: Attested recovery

- GIVEN both locations are operator-attested for the package
- WHEN the analyst publishes it
- THEN publication may proceed and records attestations with the result

### Requirement: Expose authenticated publication control and status

The system MUST require an authenticated user for recovery, status, publish, and retry. It MUST persist `not ready`, `ready`, `publishing`, `published` (version/time), or failure. The UI MUST NOT claim success before `published` and MUST expose the public link.

#### Scenario: Authenticated publish workflow

- GIVEN a logged-in user and current package
- WHEN the user records artifacts and publishes
- THEN refreshed status has the public link

#### Scenario: Unauthenticated request

- GIVEN no valid authentication
- WHEN recovery, status, publish, or retry is requested
- THEN the system rejects it without state change

### Requirement: Require migration-ready local setup

The local workflow MUST require its Alembic migration before publication. Setup MUST require explicit `SUPERADMIN_EMAIL` and `SUPERADMIN_PASSWORD` and MUST NOT recommend the default fallback.

#### Scenario: Migration preflight

- GIVEN the migration is unapplied
- WHEN preflight runs
- THEN it requires `alembic upgrade head` before publishing

### Requirement: Publish only server-derived traceable conclusions

Reports MUST use server-derived canonical metrics and identify scope, eligibility, uncertainty, official-versus-observed reconciliation, and revision evidence for each conclusion. They MUST distinguish fact from inference and MUST NOT publish unsupported assertions without disclosure.

#### Scenario: Fixture-linked reconciliation

- GIVEN a report includes observed goals or sanctions
- WHEN generated
- THEN it links canonical revisions and fixture/PDF values
