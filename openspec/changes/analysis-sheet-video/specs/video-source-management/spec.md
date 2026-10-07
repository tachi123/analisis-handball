# Delta for Video Source Management

## MODIFIED Requirements

### Requirement: Validate sources

The system MUST accept canonical `youtube.com`, `youtu.be`, and `youtube-nocookie.com` URLs, persist original URL/provider/video ID, and reject malformed URLs before save. First-time setup and replacement from review MUST use the existing authenticated per-match analysis-session source contract as the only URL-write path; the general match update contract MUST NOT persist a video source for this flow. The system MUST NOT proxy, download, or cache audiovisual content.

(Previously: Validated source persistence did not explicitly require the analysis-session contract as the sole URL-write path.)

#### Scenario: Valid source

- GIVEN an authenticated analyst enters a supported URL in review
- WHEN the source is saved through the per-match analysis-session contract
- THEN a provider-neutral source identity is persisted

#### Scenario: Invalid source

- GIVEN a malformed or unsupported URL
- WHEN the analyst submits it through review
- THEN saving is blocked with an actionable validation error

#### Scenario: Reject alternate URL write path

- GIVEN an authenticated analyst attempts to persist a review source through a general match update
- WHEN the request is processed
- THEN that contract does not save the video source
- AND the validated analysis-session contract remains the available source-write path
