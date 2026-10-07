# Delta for Video Review Workspace

## ADDED Requirements

### Requirement: Capture and preserve optional canonical shot zones

The workspace MUST allow an analyst to omit or select one IHF numeric zone 1–9 only while creating or revising a canonical `shot`. It MUST preserve the selected zone through draft restoration, revision, evidence updates, and video-anchor recalibration unless the analyst explicitly changes it. It MUST NOT expose or submit a shot zone for non-shot commands, and it MUST NOT submit legacy zone values.

#### Scenario: Capture a zoned shot

- GIVEN an analyst records a shot with zone 4
- WHEN the canonical command is saved and later revised
- THEN zone 4 remains in the revision unless explicitly changed

#### Scenario: Unzoned or non-shot command

- GIVEN a historic unzoned shot or a non-shot command
- WHEN the workspace renders or saves it
- THEN the unzoned shot remains valid and the non-shot has no zone control or payload
