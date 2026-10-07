## Exploration: sdd/match-review-incidents/explore

### Current State

The MatchReview screen at `http://127.0.0.1:5173/match/98/review` triggers React's development-mode error: "Rendered more hooks than during the previous render". The error is associated with `MatchReview.tsx:140` where `const currentVideoTime = player.currentTime` accesses the YouTube player's current time. The component uses 30+ React hooks (useState, useQuery, useMutation, useEffect, useMemo, useYouTubeSync) all called at the top level in a fixed order, so the violation must stem from indirect state destabilization rather than missing or conditionally-called hooks.

### Affected Areas

- `frontend/src/pages/MatchReview.tsx:63` — `useYouTubeSync(session?.source ?? null, session?.video_position_seconds ?? 0, sessionQuery.dataUpdatedAt)` passes `sessionQuery.dataUpdatedAt` as the `retryKey` parameter. This is a React Query internal timestamp that changes on every query refetch, causing the hook's internal `useEffect` (line 25-29) to reset availability to `'unknown'` and internally rebalance state.
- `MatchReview.tsx:64` — `useMemo(() => closestEventId(eventsQuery.data ?? [], player.currentTime), [eventsQuery.data, player.currentTime])` depends on `player.currentTime`, which fluctuates when the `retryKey` changes, forcing the memo to recompute on every render cascade.
- `MatchReview.tsx:140` — `const currentVideoTime = player.currentTime` feeds the notice display and is passed down to `VideoSection`, `MatchClock`, and `IncidentCapture` as `currentVideoTime` prop.
- Child components `VideoSection.tsx`, `MatchClock.tsx`, `IncidentCapture.tsx`, `EventTimeline.tsx`, `Sidebar.tsx` all receive `currentVideoTime` or `player`-derived props, so state fluctuations propagate through the entire render tree.

### Root Cause (Confirmed)

**Primary**: `useYouTubeSync` called with `sessionQuery.dataUpdatedAt` as `retryKey` (line 63). This timestamp changes when the `analysis-session` query refetches (e.g., after saveSession.mutate, after anchorSave, after query invalidation). The hook's internal effect (dep: `[source, retryKey]`) then calls `setAvailability('unknown')`, resetting the player's availability state. This causes `player.currentTime` to effectively restart or fluctuate, which propagates through:

1. `useMemo` dependency on line 64 → recomputation
2. `currentVideoTime` prop passed to 3 child components
3. Render conditions like `playerUnavailable = !session?.source || unavailable.has(player.availability)` → toggling visibility
4. `handleWizardSubmit` and `mark` mutation flows that check `hasValidClockStart` based on `player.availability`

The cascade of re-renders, combined with React Strict Mode's double-invocation in development, can cause the hook call counter to appear inconsistent between render passes, triggering "Rendered more hooks than during the previous render."

**Secondary (not confirmed but plausible)**:

- The `useEffect` cleanup bug on line 118: `window.removeEventListener('keydown', 'closeOnEscape')` should be `window.removeEventListener('keydown', closeOnEscape)` — a string literal instead of the function variable. This could cause keydown handler accumulation but is unlikely to be the direct hook order cause.
- Conditional rendering of `EvidenceModal` (`modal && selected`) and `IncidentWizard` (`wizardOpen`) — these components mount/unmount based on state, but the parent's hook order remains fixed; they could contribute to a perception of instability but not the root cause.

### Proposed Fix

**Safe approach**: Stabilize the `retryKey` for `useYouTubeSync` by replacing `sessionQuery.dataUpdatedAt` with a locally managed state key that only changes when the video source actually changes, not on every query refetch.

**Change in `MatchReview.tsx` line 63**:

Replace:
```javascript
const player = useYouTubeSync(session?.source ?? null, session?.video_position_seconds ?? 0, sessionQuery.dataUpdatedAt)
```

With:
```javascript
const [retryKey, setRetryKey] = useState(0)
useEffect(() => { setRetryKey(Date.now()) }, [session?.source]) // only changes when source changes
// ...
const player = useYouTubeSync(session?.source ?? null, session?.video_position_seconds ?? 0, retryKey)
```

**Rationale**: The `retryKey`'s purpose is to allow `useYouTubeSync` to detect when the source has changed and reset availability accordingly. By tying it to `session?.source` via a `useEffect` rather than `sessionQuery.dataUpdatedAt`, the key stays stable across query refetches that don't change the source (which is the common case — the session query refetches when backend data updates, but the YouTube source URL stays the same). When the source does change, the effect fires and the new `retryKey` triggers the hook's existing availability-reset logic.

**Alternative (simpler, lower risk)**: If the retry/reset functionality is not essential for the review screen, simply use a constant `0` or `Date.now()` memoized once:

```javascript
const player = useYouTubeSync(session?.source ?? null, session?.video_position_seconds ?? 0, 0)
```

This eliminates the changing key entirely. The hook's internal `previousRetryKey` ref will always see `0 !== 0` as false, so the availability-reset effect won't trigger on every refetch. The availability will persist based on iframe messages instead, which is sufficient for a review screen where the source is typically set once.

### Scope

- **File changed**: `frontend/src/pages/MatchReview.tsx` — one line modified (the `useYouTubeSync` call on line 63, plus adding the `useEffect` + `retryKey` state if choosing the first option).
- **No child component changes needed** — stabilizing the `retryKey` at the parent level resolves the cascade.
- **No API or backend changes** — purely a frontend hook dependency fix.

### Validations

1. **Unit test**: Verify that `useYouTubeSync` is called with a stable `retryKey` that does not change when `matchQuery`, `sessionQuery`, or `eventsQuery` refetch, only when `session?.source` changes.
2. **Render test**: Verify that the MatchReview component renders without the "Rendered more hooks" warning in React Strict Mode development environment.
3. **Player time stability**: Verify that `player.currentTime` no longer fluctuates on every query refetch when the source URL is unchanged.
4. **Availability state**: Verify that `player.availability` still resets appropriately when the YouTube source actually changes (the `useEffect` tying `retryKey` to `session?.source` ensures this).

### Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| `useYouTubeSync` availability reset stops working for actual source changes | Low | Medium | Choose the first fix option (tie `retryKey` to `session?.source` via `useEffect`), which preserves the reset logic for real source changes |
| `player.currentTime` stops updating from iframe messages | Low | Medium | The `useYouTubeSync` hook's internal message-listening `useEffect` (dep: `[]`) is unchanged; only the `retryKey` stability changes |
| Other components rely on `player` re-rendering on query refetch | Low | Low | The `useMemo` on line 64 previously recomputed on every refetch — stabilizing the key reduces unnecessary work, which should be an improvement |
| Edge case: source changes between renders and `retryKey` doesn't fire in time | Very Low | Low | The `useEffect([session?.source])` fires on source change, and the new `retryKey` triggers the hook's reset in the same render cycle |

### Next Recommended

Proceed with the **simpler alternative** first: change line 63 to use a constant `retryKey = 0`. This is the lowest-risk change (single line, no new `useEffect`, no new state variable) and directly addresses the root cause by eliminating the changing timestamp that cascades through the component tree. If testing confirms the hook order error disappears and player behavior remains correct, land that change. If the availability-reset behavior is needed for a specific workflow (e.g., source URL swaps during a review session), upgrade to the full `useEffect([session?.source])` + `retryKey` state pattern.

Before implementing, run the existing test suite (`pnpm test -- MatchReview`) to establish a baseline, then verify the fix eliminates the hook order warning in development mode.