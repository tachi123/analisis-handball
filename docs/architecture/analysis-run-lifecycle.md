# Immutable analysis runs

An analysis run keeps independent analyst work separate until a deliberate promotion selects one canonical version for a match.

## Quick path

1. Confirm the official sheet.
2. Create or resume a draft with the intended mode.
3. Finish evidence-backed capture and period markers.
4. Promote the intended draft to `active`.
5. Export only from the active run.

## States

| State | Purpose | Can change events? | Used by reports? |
|---|---|---:|---:|
| `draft` | Work in progress | Yes, creator/admin | No |
| `active` | Canonical selected analysis | No | Yes |
| `superseded` | Prior historical analysis | No | Historical reads only |

Promotion is a state transition. It preserves events, revisions, evidence, session, and source; it does not copy or rewrite them.

## Modes

| Mode | Capture source | Clock/evidence contract |
|---|---|---|
| `video` | YouTube | Calibrated video evidence and seekable anchors |
| `manual` | Local video outside the browser | Analyst-entered local-video timestamp; no iframe claim |
| `live` | Live observation | Observed clock with explicit unavailable-video evidence |

Mode is immutable after draft creation. Create another draft instead of repurposing a run.

## Access and API contract

- Draft creation requires a confirmed official sheet for non-admin users.
- Manual-origin matches enforce their owner rules.
- Only a draft creator or admin/superadmin can write or promote that draft.
- All draft writes must carry `run_id`; legacy fallback paths must preserve the same authorization check.
- Review a draft with `/match/:matchId/review?run=:runId` even before canonical analysis is enabled.

## Completion checklist

- [ ] Periods 1 and 2 have observed `kickoff` and `period_end`.
- [ ] The intended video/manual/live evidence is attached.
- [ ] Warnings and official reconciliation were reviewed.
- [ ] The draft is explicitly promoted before metrics/export.

## References

- `backend/app/services/analysis_run_service.py`
- `backend/app/services/canonical_analysis_service.py`
- `frontend/src/pages/ManualMatchPreparationPage.tsx`
- `frontend/src/pages/MatchReview.tsx`
