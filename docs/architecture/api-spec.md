# SAPA Stats — API Specification (REST /api/v1)

## Autenticación

Todas las rutas protegidas por JWT excepto `/auth/login`.

```
Authorization: Bearer <access_token>
```

**JWT Payload:**
```json
{
  "sub": 1,                    // user_id
  "club_id": 1,                // club al que pertenece (null para superadmin global)
  "role": "admin",             // superadmin | admin | analyst
  "exp": 1712345678
}
```

**Filtro automático por club:** Todos los endpoints GET de listas filtran por `club_id` del JWT automáticamente. Superadmin puede pasar `?club_id=X` para ver datos de cualquier club. POST/PATCH/DELETE validan que el recurso pertenezca al club del usuario.

---

## 1. Auth (`/api/v1/auth`)

| Método | Ruta | Auth | Descripción |
|--------|------|------|-------------|
| POST | `/auth/login` | No | Login email+password → devuelve `{ access_token, token_type, user, club }` |
| GET | `/auth/me` | Sí | Devuelve usuario del token actual + su club |
| PUT | `/auth/change-password` | Sí | Cambia contraseña (requiere actual + nueva) |
| GET | `/auth/users` | Sí (admin+) | Lista usuarios |
| POST | `/auth/users` | Sí (admin+) | Crea un usuario; un admin solo puede crear analistas |

---

## 2. Tournaments (`/api/v1/tournaments`)

| Método | Ruta | Roles |
|--------|------|-------|
| GET | `/tournaments/` | cualquiera (filtrado por club_id JWT) |
| POST | `/tournaments/` | superadmin, admin |
| PATCH | `/tournaments/{id}` | cualquiera (valida club_id) |
| DELETE | `/tournaments/{id}` | superadmin, admin |

---

## 3. Teams (`/api/v1/teams`)

| Método | Ruta | Roles |
|--------|------|-------|
| GET | `/teams/` | cualquiera (filtrado por club_id) |
| POST | `/teams/` | superadmin, admin |
| PATCH | `/teams/{id}` | cualquiera (valida club_id) |
| DELETE | `/teams/{id}` | superadmin, admin |

---

## 4. Players (`/api/v1/players`)

| Método | Ruta | Query params | Roles |
|--------|------|-------------|-------|
| GET | `/players/` | `?team_id=` (opcional) | cualquiera (filtrado club_id) |
| POST | `/players/` | — | superadmin, admin (club_id automático del JWT) |
| PATCH | `/players/{id}` | — | cualquiera (valida club_id) |
| DELETE | `/players/{id}` | — | superadmin, admin |

---

## 5. Matches (`/api/v1/matches`)

| Método | Ruta | Roles |
|--------|------|-------|
| GET | `/matches/` | cualquiera (filtrado club_id, eager loaded tournament, teams) |
| GET | `/matches/{id}` | cualquiera (valida club_id, eager loaded tournament, teams, squad, player) |
| POST | `/matches/` | cualquier usuario autenticado; queda como creador del manual |
| PATCH | `/matches/{id}` | cualquiera (valida club_id) |
| DELETE | `/matches/{id}` | superadmin, admin |

Los partidos creados por `POST /matches/` son `manual`: requieren equipos distintos, pueden omitir fecha, hora y el torneo legado (`tournament_id`). Un analista puede crear y modificar únicamente sus propios manuales; admin y superadmin pueden administrar todos. La clasificación por torneo legado no crea ni modifica `TournamentStage`, fixture, ronda o inscripción.

### Planilla oficial de partido manual

| Método | Ruta | Descripción |
|--------|------|-------------|
| POST | `/pdf/matches/{match_id}/preview` | Parsea un PDF sin escribir, compara equipos, fecha y marcador con el partido manual. |
| POST | `/pdf/matches/{match_id}/confirm` | Persiste snapshot, jugadores oficiales y `MatchSquad` tras reconocer discrepancias. |

Ambas rutas son de la persona creadora del partido manual o de un admin. La confirmación no crea `Match`, `ScheduledMatch`, `FixtureImport`, `StageRoster`, registros ni rondas. La fuente PDF y los hechos de `OfficialSnapshot` son inmutables; el análisis canónico queda disponible sólo tras una planilla confirmada.

---

## 6. Squad (`/api/v1/matches/{id}/squad`)

| Método | Ruta | Roles |
|--------|------|-------|
| GET | `/matches/{id}/squad` | cualquiera |
| PUT | `/matches/{id}/squad` | superadmin, admin (upsert: crea si no existe, actualiza si existe) |
| DELETE | `/matches/{id}/squad/{player_id}` | superadmin, admin |

---

## 6.1 MatchSquad Fields

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `jersey_number` | Integer | Número de camiseta para este partido |
| `is_goalkeeper` | Boolean | |
| `official_goals` | Integer | Goles según planilla oficial (del PDF) |
| `official_yellow` | Integer | Tarjetas amarillas oficiales |
| `official_2min` | Integer | Exclusiones de 2 min oficiales |
| `official_red` | Integer | Tarjetas rojas oficiales |
| `official_blue` | Integer | Tarjetas azules oficiales |

---

## 7. Events (`/api/v1/matches/{id}/events`)

| Método | Ruta | Roles | Notas |
|--------|------|-------|-------|
| GET | `/matches/{id}/events` | cualquiera | Ordenados por `game_timestamp` ASC |
| POST | `/matches/{id}/events` | cualquiera | Crea evento (club_id se hereda del match) |
| DELETE | `/matches/{id}/events/{event_id}` | cualquiera | |
| DELETE | `/matches/{id}/events/last` | cualquiera | Elimina último evento (por ID) y lo devuelve |

**Event Taxonomy** — ver `docs/handball/taxonomy.md`

---

## 8. Clips (`/api/v1/matches/{id}/clips`)

| Método | Ruta | Roles |
|--------|------|-------|
| GET | `/matches/{id}/clips` | cualquiera |
| POST | `/matches/{id}/clips` | cualquiera |
| PATCH | `/matches/{id}/clips/{clip_id}` | cualquiera |
| DELETE | `/matches/{id}/clips/{clip_id}` | cualquiera |

---

## 9. PDF confirmation (`/api/v1/pdf`)

| Método | Ruta | Roles | Descripción |
|--------|------|-------|-------------|
| POST | `/pdf/parse` | cualquiera | Parsea planilla PDF Femebal y devuelve JSON sin persistir |
| POST | `/pdf/confirm` | superadmin, admin | Persiste una planilla PDF con los valores confirmados por el analista. |
| POST | `/pdf/import` | superadmin, admin | No importa datos: responde `409` e indica usar `/pdf/confirm`. |

**Flujo `/pdf/confirm`:**
1. Recibe el archivo PDF y `confirmation_json` (multipart form-data).
2. Valida la confirmación del analista y persiste el snapshot oficial.
3. Devuelve `{ match_id, snapshot_id }` con `201 Created`.

---

## 10. Stage Performance (`/api/v1/stages/{stage_id}`)

| Método | Ruta | Roles |
|--------|------|-------|
| GET | `/stages/{stage_id}/standings` | cualquiera (standings confirmados-only) |
| GET | `/stages/{stage_id}/scorers` | cualquiera (goleadores confirmados-only) |
| GET | `/stages/{stage_id}/player-averages` | cualquiera (promedios confirmados-only) |

---

## 11. Canonical Analysis (per-match contracts)

Canonical analysis is intentionally addressed by match, not by a session-scoped facade. The analysis-session endpoint resolves the authenticated analyst's session for that match; its `PUT` is a complete checkpoint, not a partial `PATCH`.

| Método | Ruta | Roles | Descripción |
|--------|------|-------|-------------|
| GET | `/matches/{match_id}/analysis-session` | cualquiera | Obtiene la sesión del analista autenticado para el partido |
| PUT | `/matches/{match_id}/analysis-session` | cualquiera | Crea/reemplaza el checkpoint completo: source, angle, posición, filtros, borrador, cola, anclas y segmentos |
| GET | `/matches/{match_id}/canonical-events` | cualquiera | Lista eventos canónicos, cada uno con su última revisión |
| POST | `/matches/{match_id}/canonical-events` | cualquiera | Crea un evento canónico observado; valida responsabilidad contra roster/planilla del partido |
| PATCH | `/canonical-events/{event_id}` | cualquiera | Reemplaza el evento observado; la respuesta devuelve solo la revisión actual |
| DELETE | `/canonical-events/{event_id}` | cualquiera | Desactiva un evento con motivo |
| GET | `/matches/{match_id}/canonical-state` | cualquiera | Estado analítico derivado |
| GET | `/matches/{match_id}/canonical-metrics` | cualquiera | Métricas derivadas y cobertura de elegibilidad |
| GET | `/matches/{match_id}/canonical-reconciliation` | cualquiera | Comparación analítica contra snapshot oficial |
| GET | `/matches/{match_id}/warnings-summary` | cualquiera | Totales oficiales/canónicos por jugador y partido, estado y eventos de evidencia vinculados |
| GET | `/matches/{match_id}/canonical-player-projection` | cualquiera | Proyección canónica opcional de un jugador; requiere `player_id` y admite filtros de equipo, período y rango de reloj |
| GET | `/matches/{match_id}/canonical-legacy-dry-run` | cualquiera | Vista de legacy no mutante para revisión de cutover |
| PUT | `/matches/{match_id}/canonical-cutover` | manual: creador o admin/superadmin para habilitar; fixture/existente: cualquier usuario autenticado para habilitar con planilla confirmada; admin/superadmin para deshabilitar | Inicia el cutover desde la preparación o realiza rollback con motivo |

### Límites actuales del contrato

- No existen endpoints `/canonical-analysis/sessions/*`, listas de sesiones, sesión activa, eventos por sesión, anclas por sesión, exportación ni sincronización offline.
- Una respuesta de evento expone únicamente la última revisión. El backend aún no persiste confidence, visibility, corrected payload, `revision_of` ni un historial/diff cronológico para la UI.
- Un jugador incluido en `match_squad`, planilla oficial o roster de fixture puede ser responsable aunque se desconozcan alineación, sustituciones o arquero activo; esos contextos no bloquean la captura.
- `warnings-summary` compara los totales canónicos elegibles contra la planilla oficial inmutable. Los timestamps oficiales y las sustituciones de arquero son `not_comparable`: el PDF oficial aporta totales, no ese detalle temporal.
- No existe un endpoint de exportación PDF. StatisticsPage construye el PDF en el cliente a partir de estas lecturas canónicas; puede incluir una proyección de arquero opcional.

## Future public reports

Public Google Sheets/GitHub Pages reports are not current API behavior. Any future public projection requires its own approved contract and must remain separate from the authenticated `/match/{id}/timeline` UI.

---

## Error Responses

```json
// 400 Bad Request
{ "detail": "Validation error description" }

// 401 Unauthorized
{ "detail": "Invalid or expired token" }

// 403 Forbidden
{ "detail": "Insufficient permissions or club mismatch" }

// 404 Not Found
{ "detail": "Resource not found" }

// 409 Conflict
{ "detail": "Resource conflict (e.g., duplicate slug, version mismatch)" }

// 422 Unprocessable Entity
{ "detail": [ { "loc": ["body", "field"], "msg": "error", "type": "value_error" } ] }

// 500 Internal Server Error
{ "detail": "Internal server error" }
```

---

## Pagination

List endpoints accept:
- `?limit=50&offset=0` (default limit 50, max 100)
- `?club_id=X` (superadmin only)

Response envelope:
```json
{
  "items": [...],
  "total": 123,
  "limit": 50,
  "offset": 0
}
```

---

## Versioning

- URL version: `/api/v1/`
- Breaking changes → nueva versión URL
- Deprecation header: `Deprecation: true` + `Link: <new-url>; rel="successor-version"`
