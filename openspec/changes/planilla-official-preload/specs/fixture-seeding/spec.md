# Delta for Fixture Seeding

## ADDED Requirements

### Requirement: Derive approved-stage fixture payloads
The system MUST derive versioned, deterministic JSON from a manifest and reviewed team mapping. It MUST create distinct stage identities, infer each round from its match date under the declared calendar rule, preserve source scores, and report unresolved team labels without guessing.

#### Scenario: Derive mapped fixtures
- GIVEN a manifest, complete mapping, and declared date-to-round rule
- WHEN derivation is run twice with identical inputs
- THEN both JSON outputs are byte-equivalent and contain distinct stages and inferred rounds

#### Scenario: Report an unresolved label
- GIVEN a manifest label absent from the mapping
- WHEN derivation is run
- THEN the label is reported as unresolved and no fixture team is inferred for it
