# Permanencia 2026 (3ª Masculino) — Estado y Plan de trabajo

> Documento de handoff. Resume qué está hecho, cómo funciona el modelo de datos,
> y qué falta, para continuar el trabajo en otra sesión con poco contexto.

## Objetivo

Hub privado autenticado del torneo **FEMEBAL Permanencia 2026** (stage `9`,
nombre `Torneo Permanencia 2026 3ªM`): fixture, planillas oficiales,
reconciliación de jugadores/clubes, estadísticas por jugador y por club, y tabla
de posiciones. Preservar los análisis de video existentes de SAPA.

---

## Estado actual (HECHO)

### Fixture
- **120 partidos / 15 fechas** importados en el stage 9 (clave de fixture:
  `femebal:00067XXX`). Fuente: tracker FEMEBAL.
- 22 fixtures reutilizados (los que ya tenían planilla) + 98 creados.
- 3 partidos de análisis SAPA **linkeados sin pérdida**: Match 100 → fixture
  fecha 6, Match 99 → fecha 9, Match 101 → fecha 10.

### Planillas oficiales (confirmadas)
- **96 planillas cargadas** = **95 confirmadas** (`is_confirmed=True`) + **1 suspendida**.
- Cobertura **8/8 en todas las fechas 1 a 12**.
- Fecha 13: **0 confirmadas** todavía (no se bajaron los PDF).

### Resultados sin planilla (reported)
- **Fecha 13 completa con resultado** (8/8), como `reported` (no confirmados):
  - 7 vienen del tracker FEMEBAL.
  - 1 manual/provisorio: **Pilar 0–1 Palermo** (`femebal:00067276`), pendiente de confirmar con planilla.
- Fechas **14 y 15**: sin resultado (futuras).

### Jugadores y clubes
- **334 jugadores** distintos, vinculados a club por **nombre normalizado + club**
  (el dorsal puede variar; nunca se fusiona entre clubes).
- **2.683 filas** de jugador confirmadas (apariciones con goles/sanciones).
- 0 filas pendientes de vinculación.

### Estadísticas (solo confirmadas por planilla)
| Métrica | Total |
|---|---|
| Goles | 4.950 |
| Amarillas | 55 |
| Exclusiones 2' | 511 |
| Rojas | 65 |
| Azules | 3 |

### Partidos especiales
- **San Martín (Ce.M.E.F) 2–0 Ituzaingó** (`femebal:00067197`, fecha 3):
  suspendido y otorgado. La planilla muestra 16–12 (parcial de suspensión), el
  resultado oficial es 2–0. El snapshot quedó `is_confirmed=False` y sus 25
  jugadores / 28 goles **no cuentan** en estadísticas.
- **Pilar 0–1 Palermo** (`femebal:00067276`, fecha 13): provisional `reported`,
  a confirmar.

---

## Modelo de datos y reglas no negociables

### Entidades clave (backend/app/models.py)
- `ScheduledMatch`: el fixture (fecha, equipos, `source_home_score`,
  `source_away_score`, `result_status`, `status`, `fixture_key` único).
- `Match`: el partido "jugado" con resultado (`home_score`, `away_score`,
  `scheduled_match_id` **único**, `origin`, equipos legacy `Team`).
- `OfficialSnapshot`: evidencia de la planilla (`is_confirmed`, score, hash,
  `source_*`). Se vincula al `Match`.
- `OfficialSnapshotPlayer`: fila de jugador por planilla (`player_id`, `side`,
  goles/sanciones).
- `Player`: jugador; `StageRoster`/`MatchSquad`: pertenencia a club/partido.
- `FixtureImportEntry`: vincula `entry_key` (femebal) ↔ `ScheduledMatch`.

### Estados y semántica
- `result_status`: `unreported` → `reported` (tracker/sin planilla) →
  `approved`/`confirmed` (planilla).
- `status` (`MatchStatus`): `scheduled`, `played`, `postponed`, `cancelled`,
  `suspended` (se agregó `suspended`).
- Regla clave: **la planilla manda** sobre el tracker. Fecha y score de la
  planilla son la verdad oficial; el tracker es `reported`.
- **Estadísticas se agregan SOLO de snapshots `is_confirmed=True`** (así el
  partido suspendido queda excluido).

### Reglas duras
1. Nunca fusionar jugadores entre clubes distintos.
2. Dorsal es evidencia secundaria, no clave de identidad (puede variar).
3. Resultados `reported` NO se muestran como confirmados.
4. `Match.scheduled_match_id` es único → al llegar la planilla se **actualiza el
   mismo Match**, no se crea otro.
5. Uvicorn sin `--reload`: reiniciar el contenedor tras cambios Python.
6. `resources/` está montado **read-only** dentro del contenedor; los scripts de
   escritura de artefactos se corren en el **host** (Windows) con Python local.
7. No commit/push/deploy sin pedido explícito.

---

## Scripts y flujo de trabajo

Todos en `backend/scripts/`. Patrón común: `--dry-run` / `--execute`, idempotentes,
y entradas en JSON revisables (nada hardcodeado).

| Script | Función |
|---|---|
| `discover_planillas.py` | Regenera `manifest.json` desde los PDF (se corre en el host). |
| `load_femebal_reconciled_planillas.py` | Carga planillas reconciliadas por URL de PDF del tracker (dry-run/execute). |
| `load_reported_results.py` | Materializa resultados `reported` (del tracker en DB) en `Match`, sin planilla. |
| `set_reported_results.py` | Aplica resultados provisorios desde un JSON revisado (ej. Palermo 0–1). |
| `reconcile_official_planilla_players.py` | Vincula filas de jugador a `Player` por nombre normalizado + club. |
| `correct_suspended_matches.py` | Corrige partidos suspendidos (resultado otorgado, baja snapshot). |

### Artefactos JSON clave (resources/planillas/_discovery/)
- `femebal-permanencia-2026-fixture.json` — fixture 120 partidos con `result` y URL de PDF del tracker.
- `femebal-permanencia-2026-planilla-reconciliation.json` — 96 links PDF↔fixture (0 sin matchear).
- `femebal-permanencia-2026-suspended-matches.json` — correcciones de suspendidos.
- `femebal-permanencia-2026-reported-results.json` — resultados provisorios manuales.
- `_all-2026-audit/manifest.json` — corpus de planillas parseadas (210 records).

### Servicio de reconciliación
- `backend/app/services/femebal_planilla_reconciliation_service.py`:
  matchea PDFs locales contra el fixture por **nombre de archivo del PDF en la URL
  del tracker** (identidad única). Si el score del tracker difiere, marca
  `tracker_score_disagrees` en vez de rechazar.
- `backend/app/services/official_planilla_loader_service.py`:
  `_link_entry` reutiliza/actualiza el `Match` existente (para resultados
  `reported` previos) en vez de duplicar.

---

## PENDIENTE (qué falta)

### 1. Tabla de posiciones (standings)
- Derivar de los resultados (fechas 1–13). Usar score de planilla (confirmado)
  y/o `reported` con distinción visible.
- Puntos: victoria 2, empate 1, derrota 0 (confirmar criterio con usuario).
- Desempates: definir (diferencia de gol, goles a favor, etc.).

### 2. Estadísticas agregadas por jugador y por club
- Por jugador: partidos, goles, sanciones, promedios.
- Por club: GF/GC, diferencial, totales, puntos.
- Excluir el partido suspendido (snapshot `is_confirmed=False`).

### 3. UI (hub)
- `frontend/src/pages/PermanenciaHubPage.tsx` ya muestra fixture cronológico con
  badges (planilla/video/análisis). Falta: pestaña/panel de **standings** y de
  **estadísticas** (jugador y club).
- Mostrar estado `suspended` (hoy `fixture_read` no expone `status`).
- Mostrar distinción `reported` vs `approved` en resultados.

### 4. Fuzzy merge de jugadores (revisable, NO automático)
- Se detectaron muy pocos "parecidos" dentro de un club, todos personas distintas
  (hermanos / distinto nombre de pila): no hay merges seguros pendientes.
- Si se quiere, generar un artefacto de candidatos por similitud para revisar a mano.

### 5. Fechas 14 y 15
- Descargar planillas y cargar con el mismo flujo (`discover` → reconciliar →
  `load_femebal_reconciled_planillas`).

### 6. Confirmar Palermo 0–1
- Cuando esté la planilla, se confirma y reemplaza el provisional.

### 7. Inconsistencia SAPA (3 fixtures)
- `femebal:00067226` (f6), `00067244` (f9), `00067259` (f10) tienen **snapshot
  confirmado** pero `result_status` sigue en `reported` con score del tracker.
  Reconciliar: pasar `result_status` a `approved` y `source_*` al score de la
  planilla confirmada (verificar qué score es el correcto).

---

## Validación

```powershell
# Backend (contenedor)
docker exec "analisis-handball-backend-1" pytest -q tests/test_canonical_analysis_service.py tests/test_analysis_events.py tests/test_analysis_run_service.py tests/test_migrations.py

# Tests de este trabajo (rápidos)
docker exec "analisis-handball-backend-1" pytest -q tests/test_official_planilla_loader_service.py tests/test_femebal_planilla_reconciliation_service.py

# Frontend
npm --prefix reports test
npm --prefix reports run build
```

- Nota: `tests/test_official_planilla_preload_cli.py` falla dentro del contenedor
  por resolución de path (`ROOT=parents[2]` → `/`), es preexistente y NO es
  regresión de este trabajo.

---

## Estado de git

Nada commiteado. Cambios sin commitear incluyen (ver `git status`):
- `backend/app/schemas.py` (agregado `suspended`).
- `backend/app/services/fixture_seeder.py`, `official_planilla_loader_service.py`,
  `pdf_service.py` (+ nuevos `femebal_planilla_reconciliation_service.py`).
- Nuevos scripts `backend/scripts/`: `load_femebal_reconciled_planillas.py`,
  `load_reported_results.py`, `set_reported_results.py`,
  `reconcile_official_planilla_players.py`, `correct_suspended_matches.py`.
- Frontend: `PermanenciaHubPage.tsx` y ajustes.
- Artefactos `resources/planillas/_discovery/` y corpus `_all-2026-audit/`,
  `_permanencia-2026-audit/`, PDFs de `2026_Torneo_Permanencia_.../`.
