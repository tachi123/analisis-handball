# Permanencia 2026 (3ª Masculino) — Estado y plan

> Documento de arranque para una sesión nueva. Lee esto primero; después abrí
> solo el doc modular que necesites (referencias abajo).

## Estado en una línea

Torneo FEMEBAL Permanencia 2026 (stage `9`) completo hasta la fecha 13: fixture,
96 planillas oficiales, 334 jugadores reconciliados, tabla de posiciones con
regla de puntos `3/2/1` (+ suspendido `3/0`), estadísticas por jugador/club, y
reporte público del torneo centrado en SAPA.

## Hecho

| Área | Estado |
|---|---|
| Fixture (120 partidos / 15 fechas) | Importado, stage 9, `femebal:00067XXX`. |
| Planillas oficiales | 96 = 95 confirmadas + 1 suspendida. Fechas 1–12 completas (8/8). |
| Fecha 13 | 8/8 con resultado `reported` (7 del tracker + Palermo 0–1 provisorio). |
| Fechas 14–15 | **No jugadas** (sin planilla). |
| Jugadores/clubes | 334 jugadores, 0 pendientes. Vincular por nombre normalizado + club; el dorsal puede variar. |
| Posiciones | Derivadas on-the-fly, con columna CP. Regla en `backend/config/points_rules.json`. |
| Estadísticas | Por jugador y por club, solo planillas `is_confirmed=True`. |
| Reporte público | `reports/public/tournament.json` + vista `Torneo` (fondo claro, SAPA resaltado). |

## Pendiente (corto)

1. **Confirmar Palermo 0–1** (`femebal:00067276`) cuando salga la planilla: se
   reemplaza el provisorio con `set_reported_results` → `load_femebal_reconciled_planillas`.
2. **Fechas 14–15** cuando se jueguen: bajar PDF, `discover_planillas` →
   `load_femebal_reconciled_planillas` → `reconcile_official_planilla_players`.
3. **Pulido visual del reporte público** (validar en navegador con `npm --prefix reports run dev`).
4. **Commit/push** (lo hace el usuario; nada commiteado aún).

## Reglas duras (atajos)

- La **planilla manda** sobre el tracker: fecha y score oficiales = planilla; el tracker es `reported`.
- Estadísticas solo de snapshots `is_confirmed=True` (el suspendido queda excluido).
- `Match.scheduled_match_id` es único → al llegar la planilla se **actualiza** el Match, no se duplica.
- Partido suspendido: ganador `3`, perdedor `0` y cuenta como `CP`, no derrota.
- Nunca fusionar jugadores entre clubes distintos.
- `resources/` es read-only dentro del contenedor; scripts de escritura se corren en el host.
- Uvicorn sin `--reload`: reiniciar `analisis-handball-backend-1` tras cambios Python.
- No commit/push/deploy sin pedido explícito.

## Modelo de datos (resumen)

- `ScheduledMatch` (fixture) → `Match` (resultado, `scheduled_match_id` único) →
  `OfficialSnapshot` (planilla, `is_confirmed`) → `OfficialSnapshotPlayer` (goles/sanciones).
- `result_status`: `unreported` → `reported` (sin planilla) → `approved` (planilla).
- `status`: `scheduled / played / postponed / cancelled / suspended`.

## Scripts y servicios (cuándo usarlos)

| Necesidad | Dónde |
|---|---|
| Reconciliar PDF ↔ fixture (por URL del tracker) | `backend/app/services/femebal_planilla_reconciliation_service.py` |
| Cargar planillas reconciliadas (dry-run/execute) | `backend/scripts/load_femebal_reconciled_planillas.py` |
| Materializar resultados sin planilla (tracker) | `backend/scripts/load_reported_results.py` |
| Aplicar un resultado provisorio manual | `backend/scripts/set_reported_results.py` |
| Vincular jugadores a club | `backend/scripts/reconcile_official_planilla_players.py` |
| Corregir un partido suspendido | `backend/scripts/correct_suspended_matches.py` |
| Regenerar manifest de PDF | `backend/scripts/discover_planillas.py` (host) |
| Posiciones (derivación) | `backend/app/services/standings_service.py` + `backend/config/points_rules.json` |
| Estadísticas jugador/club | `backend/app/services/statistics_service.py` |
| Exportar reporte público del torneo | `backend/scripts/export_public_tournament.py` |

## Validación

```powershell
# Backend (contenedor)
docker exec "analisis-handball-backend-1" pytest -q tests/test_canonical_analysis_service.py tests/test_analysis_events.py tests/test_analysis_run_service.py tests/test_migrations.py
docker exec "analisis-handball-backend-1" pytest -q tests/test_standings_service.py tests/test_statistics_service.py tests/test_femebal_planilla_reconciliation_service.py tests/test_official_planilla_loader_service.py

# Reporte público
npm --prefix reports test
npm --prefix reports run build
```

Nota: `tests/test_official_planilla_preload_cli.py` falla en el contenedor por
resolución de path (preexistente, no es regresión).

## Referencias modulares

- Arquitectura general: `docs/architecture/system-overview.md`
- Modelo de datos: `docs/architecture/data-model.md`
- Reporte público (fase 1): `docs/architecture/public-report-phase-1.md`
- Flujo de export: `docs/operations/match-report-workflow.md`
- Referencia de scripts: `docs/operations/scripts-reference.md`
