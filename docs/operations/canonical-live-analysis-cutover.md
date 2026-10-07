# Canonical Live Analysis Cutover

Canonical analysis is disabled by default for every match. Starting analysis through `PUT /api/v1/matches/{match_id}/canonical-cutover` requires a confirmed official sheet. For a manual match, only its creator or an admin/superadmin may enable it. Existing fixture-linked and other non-manual matches retain the general policy: any authenticated analyst may enable them. Disabling remains an admin or superadmin rollback: canonical writes and canonical derived reads are blocked, while the original `events`, `analysis_events`, and `goalkeeper_shots` remain available only through existing read-only/audit paths. No rollback mutates canonical rows, legacy rows, or immutable PDF snapshots.

## Approval gate

An admin or superadmin MUST approve the current event taxonomy/codebook before a backfill or cutover. Run `GET /api/v1/matches/{match_id}/canonical-legacy-dry-run` first, review every source-table mapping as unreviewed, and do not count any dry-run candidate in canonical metrics or reports.

Before enabling a production match, record an approval over a minimum of **three representative completed matches**: one live capture, one full video review, and one match containing an explicit unknown or unresolved observation. Each sample MUST show the same canonical semantics in live/video where applicable, reconcile score, lineup/goalkeeper, and discipline against the immutable PDF/fixture data, and disclose every discrepancy. An undisclosed discrepancy, unresolved taxonomy decision, or failed validation gate blocks approval.

## Operational sequence

1. Freeze the approved taxonomy version and run the legacy dry-run; preserve its review record.
2. Run unit/integration, isolated migration, live/video parity, PDF sample, frontend build, and report-lint gates.
3. Enable only the approved match. Monitor reconciliation and evidence coverage.
4. On a problem, disable that match immediately and use the read-only legacy fallback while investigating.
