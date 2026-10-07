# Delta for Review Statistics

## ADDED Requirements

### Requirement: Use confirmed snapshot facts for official reconciliation
The system MUST treat confirmed official snapshot score and player discipline facts as immutable reconciliation inputs. It MUST NOT use unconfirmed snapshots as official values or overwrite confirmed facts through analytical review.

#### Scenario: Exclude an unconfirmed snapshot
- GIVEN a fixture has only an unconfirmed official snapshot
- WHEN official reconciliation is requested
- THEN no official snapshot value is reported as confirmed
