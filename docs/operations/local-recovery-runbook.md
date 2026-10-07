# Local Recovery Runbook

Use this manual runbook to preserve and recover the local SAPA Stats database and imported PDFs. It creates no automatic backups. The analyst owns the cadence, storage location, and verification record.

## Quick Path

1. Start the safe local stack from the repository root: `./start.ps1` or `start.cmd`.
2. Confirm the operational SPA at `http://localhost:5173` and reports at `http://localhost:5174` open after the backend health check succeeds.
3. Create a PostgreSQL archive outside this repository.
4. Copy imported PDFs from `backend/data/pdfs` into the same recovery folder.
5. Verify the archive by restoring it into the disposable `sapa_stats_recovery_check` database.
6. Before every public report publication, repeat steps 3-5 and record the artifact folder and verification time.

Do not reset, delete, recreate, or target a restore at the live `sapa_stats` database. The named preload volume is authoritative imported competition data.

## Safe Local Start And Stop

`start.ps1` layers `docker-compose.local.yml` over the base Compose file with `--env-file backend/.env.local` and uses the approved Compose target: project `analisis-handball`, volume `analisis-handball_postgres_data`, and database `sapa_stats`. It runs `docker compose --env-file backend/.env.local -f docker-compose.yml -f docker-compose.local.yml up -d`, so Compose waits for `migrate` to complete `alembic upgrade head` before the backend starts. The expected migration head is `73b208e83d81`.

Before it starts anything, the launcher requires Docker, npm, and `backend/.env.local`. Copy `backend/.env.local.example` to `backend/.env.local` and use explicit non-default local superadmin credentials. The overlay makes the effective database URL target Compose service `db`; it does not read or overwrite a pre-existing `backend/.env` or its `DATABASE_URL`. It accepts only development file-publisher settings and gives the reports Vite process the local reports API URL. It never prints passwords or credentials.

The launcher opens separate PowerShell windows for the operational SPA and reports Vite server. Close those windows when finished. To stop Compose services while preserving the database volume, run:

```powershell
docker compose stop
```

Use `docker compose ps` and `docker compose logs migrate backend` to diagnose a failed migration or unhealthy backend. Do not use destructive cleanup commands for ordinary local stops.

### Historical Preload Compatibility

The retained preload records Alembic revision `73b208e83d81`. That historical revision repeated the `competition_teams.external_code` DDL already applied by `600464b8cb43`. Source now retains `73b208e83d81` as a no-op compatibility marker, so `alembic upgrade head` resolves the preload safely without reapplying the column or unique index. If migration still fails, preserve the volume and use the isolated backup verification below before investigating further.

## What To Preserve

| Item | Local source | Why it matters |
|---|---|---|
| PostgreSQL data | Compose volume `postgres_data` in service `db` | Authoritative matches, roster, events, users, and future analytical records |
| Imported PDFs | `backend/data/pdfs` on the host | `PDFService` writes `data/pdfs` in the backend container; Compose maps `./backend` to `/app` |
| Recovery artifacts | A folder outside the repository | Prevents backup files and imported source documents from being staged or published accidentally |
| Reference PDFs | `resources/planillas` | Supplied parser inputs, not the runtime imported-PDF store |

The current `.gitignore` does not ignore `backend/data` or recovery archives. Keep both outside Git staging; use a directory beside the repository, not a path inside it.

## Create A Manual Backup

Run these commands from the repository root in PowerShell. They intentionally create recovery artifacts, so do not run them merely to test this document.

```powershell
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$recoveryRoot = Join-Path (Resolve-Path "..") "sapa-stats-recovery"
$backup = Join-Path $recoveryRoot $stamp
New-Item -ItemType Directory -Force -Path $backup, (Join-Path $backup "imported-pdfs")

docker compose up -d db
docker compose exec -T db pg_isready -U postgres -d sapa_stats
docker compose exec -T db pg_dump -U postgres -d sapa_stats --format=custom --file=/tmp/sapa_stats.dump
docker compose cp db:/tmp/sapa_stats.dump "$backup\sapa_stats.dump"
Get-FileHash "$backup\sapa_stats.dump" -Algorithm SHA256 |
    Format-List | Out-File "$backup\sapa_stats.dump.sha256.txt"
```

Copy the imported files after the dump. An empty `backend/data/pdfs` is valid when no PDF has been imported yet.

```powershell
$importedPdfPath = Join-Path $PWD "backend\data\pdfs"
if (Test-Path $importedPdfPath) {
    Get-ChildItem $importedPdfPath -Force |
        Copy-Item -Destination "$backup\imported-pdfs" -Recurse -Force
}
Get-ChildItem "$backup\imported-pdfs" -File -Recurse |
    Select-Object FullName, Length, LastWriteTime |
    Format-Table -AutoSize | Out-File "$backup\imported-pdfs-manifest.txt"
```

Record the backup folder, dump hash, PDF manifest, and analyst in the report-publication record when that workflow exists. Until then, record them in the publication checklist or analyst log. A dump alone does not preserve imported PDF bytes.

## Verify In An Isolated Clone

This check restores the archive into a separate PostgreSQL container. It never targets the live Compose database or mounts `analisis-handball_postgres_data`. Choose a unique `$verificationName` for every run and retain the container for inspection; this runbook intentionally provides no deletion commands.

```powershell
$verificationName = "sapa-stats-recovery-check-$(Get-Date -Format 'yyyyMMddHHmmss')"
docker run -d --name $verificationName -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=sapa_stats postgres:15
docker cp "$backup\sapa_stats.dump" "${verificationName}:/tmp/sapa_stats.dump"
docker exec $verificationName sh -c "until pg_isready -U postgres -d sapa_stats; do sleep 1; done"
docker exec $verificationName pg_restore -U postgres -d sapa_stats --no-owner /tmp/sapa_stats.dump
docker exec $verificationName psql -U postgres -d sapa_stats -c "SELECT version_num FROM alembic_version;"
docker exec $verificationName psql -U postgres -d sapa_stats -c "SELECT COUNT(*) AS matches FROM matches; SELECT COUNT(*) AS preload_batches FROM official_batch_runs; SELECT COUNT(*) AS snapshots FROM official_snapshots; SELECT COUNT(*) AS competition_teams FROM competition_teams; SELECT COUNT(*) AS external_codes FROM competition_teams WHERE external_code IS NOT NULL; SELECT indexname FROM pg_indexes WHERE schemaname = 'public' AND tablename = 'competition_teams' AND indexname = 'ix_competition_teams_external_code';"
```

Success means `pg_restore` exits successfully and the counts/index match the recorded live invariants. Inspect the PDF manifest and confirm it includes the imported source files expected for the match. If verification fails, keep the artifacts and do not publish or modify the live database.

## Live Restore Boundary

This runbook does not provide live-database replacement commands. A live restore requires a separately approved maintenance procedure, a newly verified archive, and an explicit change record. Do not adapt the isolated-clone commands to the authoritative preload.

## Cadence And Pre-Publication Checklist

Create and verify a manual backup after each meaningful imported-PDF or match-data batch, at least weekly while actively analyzing matches, and immediately before every report publication. Keep the recovery folder on storage you can access if the development machine fails.

- [ ] PostgreSQL dump was created outside the repository.
- [ ] Imported PDFs were copied and their manifest was reviewed.
- [ ] The dump hash was recorded.
- [ ] The dump restored successfully into an isolated PostgreSQL container.
- [ ] The clone's counts and external-code index matched the recorded live invariants.
- [ ] The backup folder and verification time were recorded before publication.

## Limits

- This runbook does not schedule, upload, encrypt, replicate, or monitor backups.
- `docker compose` preserves `postgres_data` across ordinary restarts, but it is not a backup.
- A PostgreSQL dump does not include imported PDFs; both artifacts are required for complete recovery.
- This process recovers local data only. If future public reporting is introduced, it will not recover its Google Sheet, GitHub Pages deployment, credentials, or external video content.
- Do not restore an unverified archive over `sapa_stats`.

## Official Planilla Preload (Local Only)

Use this flow to turn a reviewed, local FEMEBAL corpus into confirmed fixture evidence. It is deliberately separated from the PostgreSQL recovery flow above: the commands below create and target an explicit **SQLite file outside the repository**. They do not use `backend/.env`, the Compose PostgreSQL database, or any deployment database.

### 0. 2026 3ªM bootstrap approval chain

For the 136 canonical 2026 3ªM PDFs, first run the bootstrap **dry-run** with the reviewed discovery, bootstrap mapping (the ID-bearing bootstrap mapping), reconciliation, report, and a human-approved `bootstrap-approval.json`. Then execute it against the same local SQLite file and retain its report/audit IDs. Do not invent or edit an approval: a maintainer must review the two stage IDs, every target ID, exact labels, and all hashes.

```powershell
# Dry-run, then execute only after human approval; both commands require the same raw evidence.
python backend/scripts/bootstrap_official_3m_competition.py --database-url $env:DATABASE_URL --manifest resources/planillas/_discovery/bootstrap-manifest.json --discovery resources/planillas/_discovery/manifest.json --mapping "$run\bootstrap-mapping.json" --reconciliation "$run\reconciliation.json" --bootstrap-report "$run\bootstrap-report.json" --approval "$run\bootstrap-approval.json" --dry-run
python backend/scripts/bootstrap_official_3m_competition.py --database-url $env:DATABASE_URL --manifest resources/planillas/_discovery/bootstrap-manifest.json --discovery resources/planillas/_discovery/manifest.json --mapping "$run\bootstrap-mapping.json" --reconciliation "$run\reconciliation.json" --bootstrap-report "$run\bootstrap-report.json" --approval "$run\bootstrap-approval.json" --report "$run\bootstrap-executed-report.json" --execute
```

Derivation requires those completed bootstrap audits plus the still-approved pre-derivation approval. It emits `bootstrap_approval_sha256`; the maintainer then creates a **new completed approval** containing that value as `pre_derivation_approval_sha256`, the exact derived-file SHA-256, `status: "completed"`, and completion metadata. The loader requires that completed approval and the same raw bootstrap evidence. Dry-run first, inspect its JSON, then repeat without `--dry-run`. To roll back only an unused bootstrap, use `--rollback-audit-id <id> --execute` with the approved evidence; it refuses fixture or roster activity and never touches 4ª data.

**Do not substitute a production, staging, Railway, or shared database URL for the SQLite URL in this runbook.** The loader accepts any explicit URL, so the operator is responsible for the target. A production load requires a separately approved deployment procedure, a verified backup, and an explicit production change record; this runbook intentionally provides no production-load command.

### 1. Create review artifacts

Run the following from the repository root. The corpus remains read-only; all generated review artifacts go to a dated folder outside the repository.

```powershell
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$run = Join-Path (Resolve-Path "..") "planilla-official-preload\$stamp"
$sourceRoot = Join-Path $PWD "resources\planillas"
New-Item -ItemType Directory -Force -Path $run | Out-Null

python backend/scripts/discover_planillas.py $sourceRoot "$run\discovery"
python backend/scripts/group_planilla_players.py "$run\discovery\manifest.json" "$run\identities"
```

If an analyst has reviewed player-identity overrides, rerun the second command with the override file. Overrides affect only identity-review artifacts; they do not guess or resolve fixture teams.

```powershell
python backend/scripts/group_planilla_players.py "$run\discovery\manifest.json" "$run\identities" --overrides "C:\approved\identity-overrides.json"
```

Review `identities\identity-summary.json`, `identities\conflicts.md`, and the discovery report before continuing. Keep the reviewed mapping and approval artifacts with the batch record.

### 2. Review team labels and derive fixtures

First create suggestions and a preview. A preview is review material only: never approve or load it.

```powershell
python backend/scripts/derive_planilla_fixtures.py `
  --manifest "$run\discovery\manifest.json" `
  --identities "$run\identities\identity-summary.json" `
  --rules "resources\planillas\_discovery\round-rules.json" `
  --suggested-mapping "$run\team-mapping.suggested.json" `
  --output "$run\derived-fixtures.preview.json" `
  --unresolved-output "$run\derivation-report.preview.json"
```

Copy the suggestion file to the reviewed mapping path, then edit and review it. Mapping keys must be exact source labels and each value must be `{ "club": "...", "variant": "..." }` (or `null` for no variant). Do not normalize, infer, or bulk-fill labels.

```powershell
Copy-Item "$run\team-mapping.suggested.json" "$run\team-mapping.reviewed.json"
# Edit and review $run\team-mapping.reviewed.json before the next command.

python backend/scripts/derive_planilla_fixtures.py `
  --manifest "$run\discovery\manifest.json" `
  --identities "$run\identities\identity-summary.json" `
  --mapping "$run\team-mapping.reviewed.json" `
  --rules "resources\planillas\_discovery\round-rules.json" `
  --output "$run\derived-fixtures.json" `
  --unresolved-output "$run\derivation-report.json"
```

The current discovery corpus has **72 unresolved sheets**. They are excluded from `derived-fixtures.json`, not guessed. Review `derivation-report.json`; resolve only evidence supported by a reviewed mapping and rerun derivation. A sheet with a missing or invalid label stays out of the batch.

### 3. Create a hash-bound approval

Approve only the final reviewed mapping and final derived file. This command writes the manifest and mapping hashes recorded by derivation and the SHA-256 of the exact derived-file bytes. Replace `operator-name` with the approving analyst's recorded name.

```powershell
python -c "import hashlib,json,sys,datetime; d=json.load(open(sys.argv[1], encoding='utf-8')); a={'schema_version':1,'manifest_sha256':d['manifest_sha256'],'mapping_sha256':d['mapping_sha256'],'derived_sha256':hashlib.sha256(open(sys.argv[1],'rb').read()).hexdigest(),'approved_by':sys.argv[3],'approved_at':datetime.datetime.now(datetime.timezone.utc).isoformat().replace('+00:00','Z')}; json.dump(a,open(sys.argv[2],'w',encoding='utf-8'),ensure_ascii=False,sort_keys=True,separators=(',',':')); open(sys.argv[2],'a',encoding='utf-8').write('\n')" "$run\derived-fixtures.json" "$run\approval.json" "operator-name"
Get-Content -Raw "$run\approval.json"
```

Changing the manifest, reviewed mapping, or derived JSON after this point invalidates the approval. Re-derive, review, and create a new approval instead of editing hashes.

### 4. Prove the batch with local SQLite

Create a fresh SQLite database in the batch folder and migrate **that file only**. The explicit environment variable is scoped to this PowerShell session; clear it after the proof.

Automated tests MUST use temporary SQLite databases and copied fixture PDFs only. They MUST NOT invoke this runbook against the Compose PostgreSQL database, a developer runtime database, or any production/shared database.

```powershell
$localDb = Join-Path $run "official-planilla-local.sqlite"
$env:DATABASE_URL = "sqlite:///" + $localDb.Replace("\", "/")
Push-Location backend
python -m alembic upgrade head
Pop-Location

python backend/scripts/load_planilla_official.py `
  --database-url $env:DATABASE_URL `
  --manifest "$run\discovery\manifest.json" `
  --mapping "$run\team-mapping.reviewed.json" `
  --derived "$run\derived-fixtures.json" `
  --approval "$run\approval.json" `
  --source-root $sourceRoot `
  --dry-run | Tee-Object "$run\load-dry-run.json"
```

`--dry-run` validates and rolls back the candidate batch. It may report would-be created/reused/skipped rows, but it must not leave fixture, match, snapshot, or completed-batch records in the SQLite file. Stop if the command exits non-zero or reports `rejected` or unexpected `skipped` reasons.

### 5. Perform and inspect the verified local load

After the dry-run report is accepted, run the same command without `--dry-run`, still using the explicit local SQLite URL:

```powershell
python backend/scripts/load_planilla_official.py `
  --database-url $env:DATABASE_URL `
  --manifest "$run\discovery\manifest.json" `
  --mapping "$run\team-mapping.reviewed.json" `
  --derived "$run\derived-fixtures.json" `
  --approval "$run\approval.json" `
  --source-root $sourceRoot | Tee-Object "$run\load-local.json"

python -c "import sqlite3,sys; db=sqlite3.connect(sys.argv[1]); print(*db.execute('SELECT id, status, created_at, rejection_reason, report FROM official_batch_runs ORDER BY id DESC'), sep='\n')" $localDb
python -c "import json,sys; r=json.load(open(sys.argv[1],encoding='utf-8')); print('unresolved:', r['counts']['unresolved']); print(*((f\"{x['source_path']}: {', '.join(x['reasons'])}\") for x in r['unresolved']), sep='\n')" "$run\derivation-report.json"
```

Keep `load-dry-run.json`, `load-local.json`, the `official_batch_runs` output, and `derivation-report.json` as the batch audit. The audit row records created, reused, and skipped fixture keys; a rejected approval has a rejection reason. Do not treat skipped or unresolved sheets as loaded evidence.

When the local proof is complete, close that PowerShell session before returning to the Compose workflow. This prevents the explicit SQLite target from being reused accidentally.

### 6. Attach video and begin canonical analysis

Start the normal local stack only after the local proof has been accepted. In the application, select a confirmed preloaded fixture; its selection row exposes the fixture key, linked official snapshot, and `youtube_link`. Attach the YouTube URL to that selected fixture through the existing match workflow. The preload does not ingest video and an unconfirmed fixture cannot be selected.

Then follow [Canonical Live Analysis Cutover](canonical-live-analysis-cutover.md): preserve its approval gate, dry-run, and match-specific enablement. A confirmed sheet and an attached YouTube link are prerequisites for analysis context, not authorization to enable canonical analysis.
