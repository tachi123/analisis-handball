# Video Source Management Specification

### Requirement: Validate sources
The system MUST accept canonical `youtube.com`, `youtu.be`, and `youtube-nocookie.com` URLs, persist original URL/provider/video ID, reject malformed URLs before save, and MUST NOT proxy, download, or cache audiovisual content.

#### Scenario: Valid source
- GIVEN an authenticated analyst enters a supported URL
- WHEN the source is saved
- THEN a provider-neutral source identity is persisted

#### Scenario: Invalid source
- GIVEN a malformed or unsupported URL
- WHEN the analyst submits it
- THEN saving is blocked with an actionable validation error

### Requirement: Report availability and recover
The system MUST expose loading, ready, autoplay-blocked, unavailable/private/removed, embedding-disabled, restricted, player/network-error, and unknown states. Non-ready states MUST preserve data and offer retry, replacement, provider opening, and no-playback evidence. A no-playback observation MUST use the same `no_visible`/`ambiguous` evidence-state policy as the unified analysis record.

#### Scenario: Runtime failure
- GIVEN a saved source fails after player readiness
- WHEN the failure is reported
- THEN its state and recovery actions are visible without deleting the session

### Requirement: Preserve source rights in public report publication
The system MUST retain source and rights/publication status with evidence. SAPA reports are intentionally public; a report MAY include an evidence reference only when its source status permits public publication. It MUST NOT publish raw video links or audiovisual content unless that specific media link is approved for public publication.

#### Scenario: Unapproved source
- GIVEN selected evidence is associated with a source not approved for public publication
- WHEN the analyst prepares a package
- THEN the evidence link is withheld and the package remains reviewable with its source restriction visible

### Requirement: Use the existing authentication prerequisite
The MVP MUST be usable by one analyst with the existing app authentication, MUST disclose provider privacy/terms, and MUST NOT introduce user management, clubs, collaboration, multi-user permissions, tenant isolation, or a new authorization model.

#### Scenario: Existing authenticated session
- GIVEN the analyst is authenticated by the existing app
- WHEN they create or replace the MVP video source
- THEN the source workflow is available without requiring user-management setup

#### Scenario: Unauthenticated prerequisite
- GIVEN no existing authenticated session is available
- WHEN the analyst opens the review workflow
- THEN the app applies its existing authentication behavior and does not create a new account or permission flow
