# Tasks: Match Review Workspace

## Review Workload Forecast

| Field | Value |
|---|---|
| Estimated changed lines | 1,150–1,450; each slice ≤400 |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | Docs → player → timeline → anchors/evidence → workspace |
| Delivery strategy | ask-always |
| Chain strategy | pending |

Decision needed before apply: Yes
Chained PRs recommended: Yes
Chain strategy: pending
400-line budget risk: High

### Suggested Work Units

| Unit | Goal | Likely files / verification / rollback |
|---|---|---|
| 1 | Correct contract documentation | Docs/specs; review; revert docs (~140) |
| 2 | Player synchronization | Hook/tests; Vitest; delete unit (~260) |
| 3 | Evidence-aware timeline | Component/tests; Vitest; delete unit (~300) |
| 4 | Anchor checkpoint and revision | Editor/modal/client/tests; Vitest; revert unit (~360) |
| 5 | Workspace wiring | Page/route/tests; quality checks; remove unit (~390) |

## Phase 1: Contract correction (Unit 1)

- [x] 1.1 Correct `docs/architecture/match-review-spec.md` and both delta specs to the per-match session/event endpoints; remove facade/export/offline claims. Test: contract review.
- [x] 1.2 State supported evidence provenance (`video_source_id`, `video_anchor_seconds`, reason/latest revision) and explicitly defer persisted confidence/visibility/corrected payload/revision diffs. Test: docs cite no unavailable contract.

## Phase 2: Player and timeline (Units 2–3)

- [x] 2.1 Create `frontend/src/hooks/useYouTubeSync.ts` using `youtubeEmbedUrl`, `playerMessage`, and `playerAvailability`; expose observed time, seek/play/pause, unavailable state. Test messages, errors, clamping.
- [x] 2.2 Create `frontend/src/components/EventTimeline.tsx` with evidence badges, text `clock_unverified` status, keyboard selection, and click-to-seek `max(0, anchor - 2)` only when video evidence exists. Test no-seek explanation, closest-time highlight, and live-region update. Timeline filters are not a usable MVP behavior: session filter persistence remains supported, but no filter controls or filter requirement are claimed.

## Phase 3: Anchors and incident review (Unit 4)

- [x] 3.1 Create `AnchorsEditor.tsx`: add/edit/delete and set video seconds from current position; require the analyst to enter/select the regulation match-start value. Derive only valid consecutive same-period playable segments; a single anchor remains unverified. Test mapping and badge outcomes.
- [x] 3.2 On explicit anchor save, checkpoint ordered anchors and valid segments through `saveAnalysisSession`; retain untouched replacement-`PUT` fields. No automatic segment persistence. Test payload/error retention.
- [x] 3.3 Create `EvidenceModal.tsx` for supported four-state event create/revise payloads: current video evidence when playable, otherwise `no_visible`/`ambiguous` without anchor. Add supported PATCH client/types and preserve drafts on 403/409/422. Test POST/PATCH payloads and invalidation.
- [x] 3.4 Do not create server-history diffs or persistence UI for confidence, visibility, corrected payload, or `revision_of`; present only latest supported reason/evidence with a deferred-history explanation. Test the limitation message.

## Phase 4: Workspace integration (Unit 5)

- [x] 4.1 Create `MatchReview.tsx` and protected `/match/:matchId/review` route in `App.tsx`; query match/session/events in parallel and compose player, timeline, anchors, and modal.
- [x] 4.2 Wire highlight, period-to-anchor seek, explicit checkpoints, unavailable retry/replacement, and guarded `dispatchReviewShortcut`. Test loading, unavailable review, editable guard, and alerts.
- [x] 4.3 Run `npm --prefix frontend test -- --run`, `npm --prefix frontend run lint`, and `npm --prefix frontend run build`; record each slice's result before requesting the next chain decision.

## Phase 5: Verifier corrections (size-exception follow-up)

- [x] 5.1 Correct shortcut mappings (`[`/`]` seek, `n`/`p` navigate, Shift+`n` notes) and document unsupported canonical undo/redo.
- [x] 5.2 Surface `clock_unverified` in the evidence modal and auto-scroll the highlighted timeline row.
- [x] 5.3 Checkpoint runtime player availability failures and recalibrate video-provenance events with audited per-event PATCH revisions after anchor saves.
- [x] 5.4 Add MatchReview scenario runtime coverage for timeline seek, period seek, tagging provenance, shortcuts, no-playback evidence, anchor recalibration, and runtime-failure checkpoints.

## Phase 6: Failed re-verification corrective batch (size-exception follow-up)

- [x] 6.1 Preserve the complete latest canonical evidence collection in each anchor-recalibration PATCH and add frontend plus per-match backend regression coverage for repeated revisions.
- [x] 6.2 Correct action shortcuts (`a`, Shift+`n`, `?`), make workspace control targets practically 44px, and narrow the active accessibility requirement to labelled radio activation areas.

## Phase 7: Final verification remediation (size-exception follow-up)

- [x] 7.1 Reconcile the new-incident tagging specification, design, and architecture documentation to the implemented canonical POST flow; retain PATCH only for existing-event revisions.
- [x] 7.2 Guarantee and regression-test 44×44 workspace targets, including modal close and timeline revise actions.
- [x] 7.3 Add runtime coverage for every applicable active scenario, or narrow unsupported claims with exact per-match-contract rationale while retaining repeated-recalibration provenance coverage.

## Phase 8: Final verifier blocker remediation (size-exception follow-up)

- [x] 8.1 Narrow `removed` from the active no-playback scenario because it is not a backend `AvailabilityState`; retain every provider state the existing contract accepts.
- [x] 8.2 Add a non-mocked `useYouTubeSync` runtime message test proving YouTube `infoDelivery.currentTime` drives timeline highlighting, and a reload-outage test covering restored source, position, anchors, draft, queue, and no-playback tagging.
- [x] 8.3 Preserve runtime-failure checkpoint fields, document/test Escape closes, and prove retained revision drafts on relevant mutation errors.

## Phase 9: Remaining acceptance remediation (size-exception follow-up)

- [x] 9.1 Render persisted `session.draft` and `session.queue` beside playback with useful empty states; add desktop/outage runtime coverage.
- [x] 9.2 Add a runtime `App`/`ProtectedRoute` test for `/match/:matchId/review`; extend outage and runtime-failure checkpoints to preserve/assert `angle` and `filters` and exercise an actual 403 revision rejection.
- [x] 9.3 Reconcile the base `video-review-workspace` specification with the dedicated review route, supported player limitations, and resumed persisted-state behavior; run frontend quality commands and targeted backend tests.

## Phase 10: Strict acceptance closure (size-exception follow-up)

- [x] 10.1 Add non-mocked player-hook runtime coverage proving paused seek emits no playback command, keeps the paused observed state, and updates time only after provider delivery.
- [x] 10.2 Add targeted per-match API runtime coverage proving a `match_squad` player is accepted without lineup, substitution, or active-goalkeeper context; retain the supported base requirement.
- [x] 10.3 Reconcile API, README, QA, expert-review, and roadmap documentation to actual per-match canonical contracts, implemented MatchReview scope, and known backend limits.

## Phase 11: Final documentation correction (size-exception follow-up)

- [x] 11.1 Correct the expert-review comparison table: canonical events are revised through per-event `PATCH`, the API returns only latest revision/evidence, and `revision_of` is not persisted. Test: documentation contract review plus frontend quality and targeted canonical-route checks.
