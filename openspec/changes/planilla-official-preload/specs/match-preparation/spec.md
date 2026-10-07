# Delta for Match Preparation

## ADDED Requirements

### Requirement: Select pre-loaded official fixtures
The system MUST list non-bye pre-loaded fixtures with their fixture key and linked confirmed official snapshot, and MUST expose a `youtube_link` field whose initial value is empty. Selection MUST use the fixture key and MUST reject fixtures lacking confirmed official evidence.

#### Scenario: Select a pre-loaded fixture
- GIVEN a fixture with a confirmed linked snapshot and no video
- WHEN the fixture-selection API is requested
- THEN its row includes the fixture key, snapshot reference, and empty `youtube_link`
