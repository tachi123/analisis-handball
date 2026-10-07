# Verification Report: Expand Warning Comparison Details

**Change**: `warnings-panel-expandable-detail`  
**Mode**: Standard (`strict_tdd: false`)  
**Preflight**: auto · OpenSpec · approved `size:exception`  
**Scope**: Final fresh-context, read-only verification.

## Result

**PASS WITH WARNINGS** — all six specified scenarios have passing runtime coverage, including a real Chromium test for native Enter/Space disclosure behavior. The lazy-query gate is correct by source inspection, but its before/after request timing is not asserted at runtime.

## Completeness

| Metric | Value |
|---|---:|
| Tasks total | 13 |
| Tasks complete | 13 |
| Tasks incomplete | 0 |

The completed work unit uses the maintainer-approved `size:exception`.

## Fresh Execution Evidence

| Check | Command | Result |
|---|---|---|
| Frontend tests | `npm --prefix frontend test -- --run` | ✅ 22 files, 92 tests passed |
| Browser keyboard test | `npm --prefix frontend run test:browser` | ✅ Chromium, 1 test passed |
| Lint | `npm --prefix frontend run lint` | ✅ passed with zero warnings |
| Production build/type-check | `npm --prefix frontend run build` | ✅ passed; Vite built 2,338 modules |
| Coverage | Not configured | ➖ unavailable |

## Spec Compliance Matrix

| Requirement | Scenario | Runtime evidence | Result |
|---|---|---|---|
| Disclosure | Expand/collapse linked comparison | `WarningsPanel.test.tsx` — pointer activation, inline target, official total, linked-event filtering, collapse and focus return | ✅ COMPLIANT |
| Disclosure | No linked events | `WarningsPanel.test.tsx` — explicit no-ID state and no disclosure button | ✅ COMPLIANT |
| Disclosure | Keyboard Enter/Space | `WarningsPanel.browser.test.tsx` — focused native button receives Enter then Space in Chromium, without a manual click | ✅ COMPLIANT |
| Disclosure | ARIA control/detail association | `WarningsPanel.test.tsx` — `aria-controls`, target ID, and `aria-expanded` transitions | ✅ COMPLIANT |
| Evidence | Ready video seek | `WarningsPanel.test.tsx` — waits for iframe readiness, then asserts `seekTo` message | ✅ COMPLIANT |
| Evidence | PDF or unavailable evidence | `WarningsPanel.test.tsx` — readable PDF fields/no action; unavailable video fallback/no seek | ✅ COMPLIANT |

**Compliance summary**: 6/6 scenarios compliant.

## Correctness — Static Inspection

| Concern | Status | Evidence |
|---|---|---|
| Inline native disclosure | ✅ | `WarningsPanel.tsx` renders keyed `type="button"`, `aria-expanded`, `aria-controls`, and a full-width detail row. |
| Lazy reads and linked-event filtering | ✅ | Both React Query reads are enabled only while a comparison is expanded; events filter by `canonical_event_ids`. |
| Per-event detail | ✅ | Warning presentation renders player, kind, period, regulation time, `clock_unverified`, video time, and evidence types. |
| Video seek lifecycle | ✅ | `selectEvidence` uses `seekTargetForEvent`; the effect seeks only after ready iframe availability. |
| PDF/unavailable evidence | ✅ | Non-video evidence has no seek action; unavailable-player fallback remains readable and clears the pending seek. |
| Live status and focus | ✅ | Polite live region announces state; collapse restores disclosure focus; switching clears selected/pending seek state. |
| Read-only/official boundary | ✅ | No mutation controls or official timestamps are rendered; only the immutable official total appears. |

## Design Coherence

| Decision | Followed? | Notes |
|---|---|---|
| Full-width inline detail row | ✅ | Detail `tr` immediately follows its owning comparison row. |
| Native button, no custom Enter/Space handler | ✅ | Chromium proves browser-native activation; no disclosure key shim exists. |
| Expand-on-demand reads | ✅ | React Query enablement is keyed to expansion. |
| Client-side ID scoping | ✅ | The warning timeline receives only filtered linked events. |
| Reuse seek lifecycle | ✅ | Reuses `ReportEventTimeline`, `seekTargetForEvent`, and `useYouTubeSync`. |

## Issues Found

### CRITICAL

None.

### WARNING

- Lazy fetching is source-correct but lacks a runtime assertion that canonical-event and session requests are absent before first expansion and occur after activation.

### SUGGESTION

- Add a comparison-switch focus assertion to directly cover the design's switch-focus behavior.

## Unrelated Workspace State

Per verification scope, the only unrelated item noted is the Alembic `external_code` migration pair:

- `backend/alembic/versions/600464b8cb43_add_external_code_to_competition_team.py`
- `backend/alembic/versions/73b208e83d81_add_external_code_column_to_competition_.py`

They are outside this frontend-only change and were not evaluated.
