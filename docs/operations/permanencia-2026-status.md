# Permanencia 2026 (3ª Masculino) — Estado y plan

> Documento de arranque para una sesión nueva. Lee esto primero; después abrí
> solo el doc modular que necesites (referencias abajo).

## Estado en una línea

Torneo FEMEBAL Permanencia 2026 (stage `9`) completo hasta la fecha 14 (7/8):
fixture, 111 planillas oficiales (110 confirmadas + 1 suspendida), 343 jugadores
reconciliados, tabla de posiciones con regla de puntos `3/2/1` (+ suspendido
`3/0`) y desempate olímpico, estadísticas por jugador/club, y reporte público
centrado en SAPA. La fecha 15 se juega el 2026-11-22. El hub público 2026 ya
tiene catálogo, detalle de torneo, pronóstico de podio y ficha anual de Lanús
exportados y validados localmente; falta publicar.

## Hecho

| Área | Estado |
|---|---|
| Fixture (120 partidos / 15 fechas) | Importado, stage 9, `femebal:00067XXX`. |
| Planillas oficiales | 111 = 110 confirmadas + 1 suspendida. Fechas 1–13 completas (8/8). |
| Fecha 14 | 7/8 confirmadas. Falta Municipalidad de Pilar–U.N.La.M. |
| Fecha 15 | Programada para 2026-11-22; **no jugada**. |
| Jugadores/clubes | 343 jugadores, 3111 filas confirmadas, 0 pendientes. Vincular por nombre normalizado + club; el dorsal puede variar. |
| Posiciones | Derivadas on-the-fly, con columna CP. Regla en `backend/config/points_rules.json` y desempate olímpico en `backend/app/services/competition_ranking.py`. |
| Estadísticas | Por jugador y por club, solo planillas `is_confirmed=True`. |
| Reporte público | `reports/public/tournament.json` (`tournament-v2`) + vista `Torneo`: SAPA, tabla, goleadores por club y proyección de partidos/campeonato. |
| Pronóstico de podio | `build_forecast` reconstruye la tabla en cada simulación, usa la regla de puntos del config y devuelve 1.º/2.º/3.º, podio y puesto esperado. Exportado en `forecast_permanencia-2026.json`. |
| Marcas e insights | `tournament_insights_service`: efectividad, promedios, local/visitante, rachas, forma, top 5 / últimos 5, mayor victoria/derrota, marcas de competencia, comparación anual y continuidad de plantel aproximada. Exportado en cada artefacto de torneo. |
| Hub público 2026 | `tournaments.json` + `tournament_<key>.json` + `forecast_permanencia-2026.json`; vistas `Competitions`, `CompetitionDetail`, `Forecast` y `SeasonProfile` con tiras G/E/P y todos los partidos del año de Lanús. |

## Apertura 2026 (contexto histórico)

| Zona | Stage | Fixture | Planillas | Jugadores |
|---|---|---|---|---|
| Apertura Zona A | `8` | 120 partidos / 15 fechas | 116 confirmadas + 4 resultados informados | 350 jugadores / 3397 filas |
| Apertura Zona B | `11` | 120 partidos / 15 fechas | 119 confirmadas + 1 suspendido | 351 jugadores / 3384 filas |

- Zona A: los 4 partidos sin planilla son Moreno 20–30 Villa Calzada (fecha 1),
  Comunicaciones 22–18 Moreno (fecha 2), Moreno 28–26 U.N.La.M. (fecha 3) y
  Moreno 18–22 San Telmo (fecha 4). Quedan `result_status=reported`.
- Zona B: Escobar–Goethe se suspendió; resultado final 0–3, Goethe suma 3 puntos,
  Escobar 0 y CP 1.
- La fecha nominal del fixture manda en `ScheduledMatch.scheduled_date`; la fecha
  real de juego queda en `Match.date` y `OfficialSnapshot.confirmed_date`.
- Artefactos: `resources/planillas/_discovery/femebal-apertura-zona-{a,b}-2026-*.json`.
- Apertura no se publica en el reporte público; se usa como contexto histórico
  de Permanencia.

## Pendiente (corto)

1. **Fecha 14**: cargar Municipalidad de Pilar–U.N.La.M. cuando exista planilla o
   resultado oficial.
2. **Fecha 15** (2026-11-22): bajar PDF, `discover_planillas` →
   `load_femebal_reconciled_planillas` → `reconcile_official_planilla_players`.
3. **Reexportar el hub tras cada nueva planilla**:
   `export_public_competitions.py` → copiar catálogo, tres torneos, pronóstico y
   `tournament.json` a `reports/public` → `npm --prefix reports test` → build.
4. **Publicar** (commit/push/deploy) sólo cuando el usuario lo pida. Los
   artefactos locales ya están regenerados y validados.
5. **Commit/push** (lo hace el usuario; nada commiteado aún).

## Reglas duras (atajos)

- La **planilla manda** sobre el score oficial; el tracker es `reported`.
- La **fecha nominal del fixture** manda en `ScheduledMatch.scheduled_date`; la fecha real de juego queda en `Match.date` y `OfficialSnapshot.confirmed_date`.
- **Desempate olímpico**: a igualdad de puntos manda primero el resultado entre los equipos igualados (mini-tabla); la diferencia general es el fallback. No ordenar por diferencia de gol directamente. Implementado en `backend/app/services/competition_ranking.py` y compartido por tabla, pronóstico e insights.
- **La UI pública muestra datos y probabilidades, no la metodología interna**: no se publican simulaciones, textos de metodología ni las decisiones de normalización de nombres. Esas decisiones quedan en la documentación y el código.
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
| Desempate olímpico compartido | `backend/app/services/competition_ranking.py` |
| Estadísticas jugador/club | `backend/app/services/statistics_service.py` |
| Marcas, rachas y ficha anual | `backend/app/services/tournament_insights_service.py` |
| Modelo de probabilidades del torneo | `backend/app/services/tournament_forecast_service.py` |
| Exportar el hub público 2026 (catálogo + torneos + pronóstico) | `backend/scripts/export_public_competitions.py` |
| Exportar el reporte legacy de Permanencia | `backend/scripts/export_public_tournament.py` |

## Validación

```powershell
# Backend (contenedor)
docker exec "analisis-handball-backend-1" pytest -q tests/test_canonical_analysis_service.py tests/test_analysis_events.py tests/test_analysis_run_service.py tests/test_migrations.py
docker exec "analisis-handball-backend-1" pytest -q tests/test_competition_ranking.py tests/test_standings_service.py tests/test_statistics_service.py tests/test_tournament_forecast_service.py tests/test_tournament_insights_service.py tests/test_femebal_planilla_reconciliation_service.py tests/test_official_planilla_loader_service.py

# Reporte público
npm --prefix reports test
npm --prefix reports run build
```

Nota: `tests/test_official_planilla_preload_cli.py` falla en el contenedor por
resolución de path (preexistente, no es regresión).

## Exportar el hub público

```powershell
docker exec -e PUBLIC_COMPETITIONS_OUTPUT=/tmp/public-hub -e PYTHONIOENCODING=utf-8 "analisis-handball-backend-1" python /app/scripts/export_public_competitions.py
docker cp "analisis-handball-backend-1:/tmp/public-hub/." "reports/public"
npm --prefix reports test
npm --prefix reports run build
```

El export escribe `tournaments.json`, los tres `tournament_<key>.json`,
`forecast_permanencia-2026.json` y el `tournament.json` legacy. No publica: la
copia a `reports/public` es local y el deploy sigue siendo explícito.

La navegación Inicio → Torneos → Permanencia → Pronóstico → Temporada de Lanús se
validó con Chrome headless (CDP), sin excepciones de runtime.

## Referencias modulares

- Arquitectura general: `docs/architecture/system-overview.md`
- Modelo de datos: `docs/architecture/data-model.md`
- Reporte público (fase 1): `docs/architecture/public-report-phase-1.md`
- Proyección pública de torneo: `docs/architecture/public-tournament-forecast.md`
- Flujo de export: `docs/operations/match-report-workflow.md`
- Referencia de scripts: `docs/operations/scripts-reference.md`
