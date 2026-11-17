# Hub público 2026: torneos, podio y rivales

## Decisión propuesta

El reporte público seguirá teniendo a **SAPA como portada y punto de entrada**.
Desde allí se incorporarán dos superficies distintas:

1. **Torneos 2026**, para consultar hechos históricos y la situación publicada
   de cada competencia.
2. **Pronósticos**, para explorar escenarios estadísticos de la competencia que
   todavía tenga fixture pendiente.

No se mezclarán resultados confirmados con simulaciones en la misma tabla. El
torneo responde «qué pasó / cómo está»; el pronóstico responde «qué puede pasar
si se juegan los partidos pendientes según el modelo».

## Estado verificado al 17/11/2026

Hechos comprobados contra la base y las planillas; sirven para dimensionar el
trabajo y evitar promesas que los datos no sostienen.

| Competencia | Stage | Estado real | Cobertura |
|---|---|---|---|
| Permanencia 2026 | `9` | 14 fechas jugadas; F14 Pilar–U.N.La.M. pendiente; F15 el 22/11 | 110 planillas confirmadas + 1 partido suspendido (San Martín 2–0 Ituzaingó) |
| Apertura 2026 · Zona A | `8` | Finalizado | 116 planillas confirmadas + 4 resultados informados sin planilla |
| Apertura 2026 · Zona B | `11` | Finalizado | 119 planillas confirmadas + 1 suspendido (Escobar 0–3 Goethe) |

- **Identidad de club validada:** `Club` + `CompetitionTeam` une Lanús (`club_id 92`) entre
  Zona B y Permanencia, y SAPA (`club_id 109`) entre Zona A y Permanencia. No hace
  falta comparar textos.
- **Identidad de jugador:** `Player` se materializa por inscripción/stage, así que
  la continuidad de plantel entre competencias sólo puede estimarse por nombre
  normalizado dentro del mismo club. Es una aproximación, no un registro de pases.
- **Permanencia tiene una sola fecha pendiente real** (más un partido postergado de
  F14). El pronóstico de podio se juega en esa fecha; no es un ejercicio de varias
  jornadas.
- **La regla de puntos es 3/2/1** (perder suma 1) y el suspendido es 3/0. Sin esa
  aclaración la tabla parece incorrecta: Lanús tiene 37 puntos con 11 victorias.
  La explicación debe estar visible en Torneos y en Pronósticos.
- **El desempate es olímpico:** a igualdad de puntos manda primero el resultado
  entre los equipos igualados (mini-tabla de puntos, diferencia y goles a favor).
  Si la mini-tabla separa sólo a algunos, se repite con los que siguen igualados;
  recién después se usa la diferencia general. Esto no es un detalle: con la
  regla anterior la tabla de Permanencia ubicaba a Ituzaingó 15.º y a Defensores
  de Moreno 16.º; con el desempate olímpico quedan invertidos porque Moreno ganó
  el partido entre ambos. También cambia el pronóstico de la F15.
- **Cobertura ≠ oficialidad:** Apertura Zona A está «finalizado» como competencia,
  pero su cobertura de planillas es parcial (4 resultados informados). La tarjeta
  debe decir ambas cosas, no sólo «finalizado».

## Recorrido principal

```text
Inicio · SAPA en 2026
├── Partidos analizados
├── Torneos 2026
│   ├── Permanencia 2026 · en curso
│   ├── Apertura 2026 · Zona A · finalizado
│   └── Apertura 2026 · Zona B · finalizado
└── Pronósticos
    └── Permanencia 2026 · podio y fecha final
```

### Inicio: SAPA primero

La portada no pasa a ser un índice genérico. Debe conservar los partidos
analizados de SAPA y sumar un bloque compacto **«SAPA en 2026»**:

- posición y puntos actuales en Permanencia;
- próximo rival o último resultado, según corresponda;
- acceso a **Torneos 2026**;
- acceso a **Pronóstico de cierre** si hay fixture pendiente.

No se mostrará una probabilidad como titular sin contexto: se rotulará como
estimación e indicará la fecha de actualización. La metodología y las decisiones
internas del modelo quedan en esta documentación y en el código, no en la UI.

## Torneos 2026

### Catálogo

La pantalla `Torneos` mostrará tres tarjetas, ordenadas por relevancia actual:

| Tarjeta | Estado | Resumen visible | Acción |
|---|---|---|---|
| Permanencia 2026 | En curso | Fecha cubierta, posición SAPA, próximo partido | Ver torneo |
| Apertura 2026 · Zona A | Finalizado | Tabla final y cobertura | Ver torneo |
| Apertura 2026 · Zona B | Finalizado | Tabla final y cobertura | Ver torneo |

La tarjeta no debe afirmar que los datos son la tabla oficial de FEMEBAL. Debe
indicar la cobertura de planillas/resultados incluidos y su actualización.

### Pantalla de un torneo

Cada torneo utilizará una misma estructura, aun cuando sea histórico:

```text
Resumen SAPA → Posiciones → Fixture y resultados → Goleadores → Disciplina → Marcas
```

- **Resumen SAPA:** posición, puntos, PJ, G/E/P, GF, GC, diferencia, efectividad
  de puntos, promedios por partido y racha actual.
- **Posiciones:** tabla completa derivada de resultados cargados, con CP y una
  nota visible de la regla 3/2/1 + suspendido 3/0.
- **Fixture y resultados:** una fecha por vez; resultado, local/visitante y
  estado de cobertura. Es más útil que una lista plana de 120 partidos.
- **Goleadores y disciplina:** datos de planillas confirmadas, con la
  advertencia de cobertura existente y el tamaño de muestra de cada jugador.
- **Marcas:** rachas y extremos de la competencia (ver definiciones abajo).

Los Apertura se publicarán como torneos históricos: tendrán tabla, fixture y
estadísticas, pero **nunca una proyección retrospectiva**. Permanencia podrá
tener un enlace hacia Pronósticos mientras conserve fechas pendientes.

### Definiciones de las métricas

Las planillas oficiales dan goles y sanciones, **no tiros**. Por eso el hub de
torneos no puede mostrar «eficacia de tiro»; esa métrica pertenece al reporte de
video. Las definiciones públicas serán:

| Métrica | Fórmula / criterio |
|---|---|
| Puntos | Regla vigente del torneo (3/2/1; suspendido 3/0). |
| Efectividad de puntos | `puntos / (partidos jugados × 3)`. No es porcentaje de victorias. |
| Porcentaje de victorias | `ganados / jugados`. |
| Goles a favor / en contra por partido | `GF / PJ`, `GC / PJ`; se muestran ambos para no ocultar el ritmo de juego. |
| Local / visitante | Misma efectividad y promedios, separados por condición. |
| Racha | Secuencia de fechas consecutivas; se informa largo y tramo (`Fechas 9–14`). |
| Forma | Últimos 5 partidos como `G/E/P` y puntos obtenidos. |
| Top 5 / últimos 5 | Grupos disjuntos según la tabla del mismo dataset; en ligas chicas el grupo se reduce para no solaparse. |
| Mayor victoria / derrota | Sólo partidos jugados; los resultados por suspendido no se presentan como goleadas. |
| Continuidad de plantel | Nombres normalizados del mismo club entre dos competencias. La aclaración metodológica es interna y no se muestra en el reporte. |

**Marcas de competencia** (calculadas del mismo dataset, sin narrativa táctica):

- mayor racha sin perder, mayor racha de victorias y de derrotas;
- mayor promedio de goles a favor y menor promedio en contra;
- mejor efectividad como local y como visitante;
- mejor presente en los últimos 5;
- clubes que no cedieron puntos contra los últimos cinco de la tabla.

Cada marca incluye club, valor, unidad y detalle (tramo de fechas o partidos).
No se publica una marca si el grupo de comparación está vacío.

## Pronósticos: podio y última fecha

### Pregunta que debe responder

No alcanza con «quién puede salir campeón». En la última fecha la pantalla debe
mostrar, para cada equipo con posibilidad matemática o simulada de podio:

| Equipo | Campeón / 1.º | 2.º | 3.º | Podio | Situación |
|---|---:|---:|---:|---:|---|
| SAPA | 4% | 20% | 40% | 64% | vs. Lanús · visitante |

**Podio** es la suma de terminar 1.º, 2.º o 3.º dentro de las mismas
simulaciones. No se calculará sumando porcentajes redondeados en el navegador.

La tabla se ordenará por probabilidad de podio, luego por campeonato. SAPA irá
siempre destacado, aunque esté fuera del corte visual. Para evitar una tabla
llena de ceros:

- mostrar primero los clubes con posibilidad matemática de podio;
- si hay demasiados, usar una vista inicial de los que tengan probabilidad de
  podio mayor que cero y un control **«Ver todos los equipos»**;
- usar `<0,1%` para una frecuencia positiva muy pequeña, no `0%`.

### Navegación de Pronósticos

```text
Pronósticos · Permanencia 2026
├── Panorama de podio             ← pantalla inicial
├── Fecha final y partidos        ← probabilidades G/E/P por fixture
└── Caminos de los aspirantes     ← campañas de la competencia actual
```

La pantalla inicial tendrá tres elementos, en este orden:

1. **Panel SAPA:** probabilidad de 1.º, 2.º, 3.º y podio; rival, condición
   local/visitante y probabilidades de ganar/empatar/perder su próximo partido.
2. **Tabla de podio:** comparación de todos los aspirantes.
3. **Fecha decisiva:** todos los cruces pendientes, con sus probabilidades.

No se deben presentar «escenarios obligatorios» del tipo «SAPA necesita ganar
y que X pierda» salvo que se enumeren exhaustivamente a partir de las reglas de
desempate. La sección de escenarios de la fecha final muestra el nivel de
exigencia: condiciones verificadas, derivadas de los datos y del desempate
olímpico. La primera versión puede limitarse a probabilidades; la vista de
escenarios agrega las condiciones exactas que el sistema pueda demostrar.

### Campaña de los aspirantes

Debajo de la tabla de podio, cada aspirante tendrá una fila expandible con su
campaña **en Permanencia**:

```text
F1 · L · vs Club A · 31–27 · G     F2 · V · vs Club B · 25–25 · E
```

Diseño accesible y legible:

- verde + texto `G` para ganado;
- amarillo + texto `E` para empatado;
- rojo + texto `P` para perdido;
- `L` o `V`, rival y marcador siempre visibles;
- el color es un refuerzo, nunca la única forma de entender el resultado;
- en móvil, cada fecha será una tarjeta vertical o una tira con desplazamiento
  horizontal, no una tabla comprimida ilegible.

Esta campaña es un hecho observado y debe separarse visualmente de las
probabilidades futuras.

## Ficha rival: Lanús durante todo 2026

Como el cierre enfrenta a SAPA con Lanús, la pantalla de pronósticos debe
ofrecer una tarjeta contextual **«Conocer a Lanús»**. No será un perfil táctico:
las planillas permiten describir resultados y estadísticas, no causas de juego.

### Contenido de la ficha

1. **Lanús en Permanencia**
   - posición actual, campaña G/E/P, GF/GC, diferencia, efectividad de puntos y
     promedios por partido;
   - tira de todas las fechas con rival, local/visitante, resultado y marcador;
   - local y visitante por separado;
   - rendimiento contra el top 5, la zona media y los últimos 5;
   - rachas (sin perder, victorias, derrotas) y forma de los últimos 5;
   - mayor victoria y mayor derrota;
   - próximo partido contra SAPA y sus probabilidades por resultado.
2. **Lanús en Apertura 2026 · Zona B**
   - posición final y campaña de esa competencia;
   - la misma tira de 15 fechas, independiente de Permanencia;
   - goleadores y disciplina con cobertura 119/120 planillas.
3. **Goleadores y jugadores clave del año**
   - tabla por competencia y, si se muestra un total anual, rotulado como suma de
     competencias distintas;
   - goles, partidos, goles por partido y sanciones;
   - **siempre visible el tamaño de muestra**: un jugador con 29 goles en 5
     partidos no se presenta como equivalente a uno con 61 en 14;
   - no se infiere jerarquía táctica ni “jugador más importante”: se describen
     goles y participación observados.
4. **Continuidad de plantel**
   - cuántos jugadores de Permanencia ya figuraban en Apertura Zona B, calculado
     por nombre normalizado dentro del club;
   - el método de nombres normalizados es una decisión interna: no se muestra la
     aclaración en la UI pública. No se usa como insumo del pronóstico.
5. **Resumen anual descriptivo**
   - dos bloques comparables: Apertura y Permanencia;
   - totales anuales sólo como suma rotulada de competencias distintas, nunca
     como una tabla de posiciones ni como una tasa que oculte cobertura.

El enlace desde Pronósticos debe decir **«Ver temporada 2026 de Lanús»**. La
misma ficha será reutilizable para cualquier rival de SAPA, pero la primera
versión puede abrir Lanús directamente por su relevancia en la última fecha.

### Hallazgos que la ficha debe poder explicar

Estos números son un ejemplo de lo que los datos permiten afirmar hoy; el
exportador debe recalcularlos, no fijarlos en el código.

- Lanús llega primero con 37 puntos, pero **cedió puntos contra el top 5**
  (5 de 9) y sólo perdió dos partidos: 19–32 con Palermo y 27–30 con Polvorines.
- Contra los últimos cinco de la tabla cedió **un solo punto**: 30–30 como local
  con Ituzaingó. **No fue una derrota**; conviene corregir esa lectura si aparece
  en la previa.
- SAPA y Palermo no cedieron puntos contra los últimos cinco; Lanús sí (1 punto).
  Es una marca comparativa, no una causa del resultado.
- SAPA llega con la racha sin perder más larga (6 fechas, F9–F14) y Palermo con
  el mejor presente (15/15 en los últimos 5). Lanús combina 5 victorias seguidas
  al inicio con un cierre de 12/15.
- En Apertura Zona B Lanús terminó 13.º con 23 puntos; en Permanencia lidera con
  37. El contraste es descriptivo: no prueba por sí solo una mejora táctica.

### Identidad del club

El cruce entre Apertura Zona B y Permanencia debe hacerse con una identidad
interna de club/equipo validada por las inscripciones, no con una comparación
libre de textos. La etiqueta pública puede ser `C.A. Lanús C` o la denominación
oficial de cada etapa, pero la ficha debe dejar visible si el nombre cambia.

## Contrato público de datos

Se reemplazará el único archivo de torneo por un catálogo y artefactos
individuales, siempre estáticos y con allowlist:

```text
reports/public/tournaments.json
reports/public/tournament_permanencia-2026.json
reports/public/tournament_apertura-zona-a-2026.json
reports/public/tournament_apertura-zona-b-2026.json
reports/public/forecast_permanencia-2026.json
```

`tournaments.json` sólo contendrá los metadatos necesarios para las tarjetas:
clave pública, nombre, temporada, estado, cobertura, archivo y si tiene
pronóstico. Ningún artefacto expondrá IDs, URLs operativas, payloads, notas,
datos de backend ni credenciales.

Cada artefacto de torneo incluirá además:

```json
{
  "schema_version": "tournament-v3",
  "updated_at": "2026-11-17",
  "coverage": {
    "matches_total": 120,
    "matches_counted": 111,
    "planillas_confirmed": 110,
    "reported_only": 0,
    "suspended": 1,
    "pending": 9,
    "label": "…"
  }
}
```

Decisiones de compatibilidad:

- `reports/public/tournament.json` se mantiene como respaldo hasta que la nueva
  navegación esté publicada. Reemplazarlo antes rompe los enlaces y el
  decodificador actual.
- Si un artefacto individual falla al decodificar, el catálogo debe seguir
  visible y mostrar esa tarjeta como no disponible; nunca una pantalla en blanco.
- La ficha anual de Lanús se deriva en el navegador desde los dos artefactos de
  torneo ya allowlistados. No se crea un tercer artefacto con datos duplicados.

### Cambios necesarios al pronóstico

El motor actual ya simula los marcadores pendientes y cuenta campeones. Debe
pasar a ordenar la tabla final completa en **cada** simulación aplicando puntos,
el desempate olímpico y, sólo después, la diferencia de gol general.

Implementado en `backend/app/services/competition_ranking.py` y reutilizado por
la tabla y el pronóstico:

- los puntos se leen de `backend/config/points_rules.json` (3/2/1 y suspendido
  3/0), sin una regla paralela en la simulación;
- los equipos igualados en puntos se ordenan primero por la mini-tabla de sus
  enfrentamientos (puntos, diferencia y goles a favor), y recién después por la
  diferencia general;
- los fixtures `suspended` o `cancelled` no se proyectan;
- cada simulación ordena la tabla completa y, si persiste una igualdad exacta
  después de todos los criterios, reparte la probabilidad de puesto entre los
  equipos igualados;
- el podio se calcula sumando las posiciones 1–3 del mismo conteo, nunca desde
  porcentajes redondeados;
- se agrega `expected_position` y `points_rule` para que la UI explique el modelo
  sin duplicar reglas.

La proyección pública de cada equipo debe incluir, como mínimo:

```json
{
  "club": "S.A.P.A.",
  "champion_probability": 0.04,
  "finish_probabilities": { "first": 0.04, "second": 0.20, "third": 0.40 },
  "podium_probability": 0.64,
  "expected_position": 3.08,
  "campaign": []
}
```

El exportador debe producir la campaña de cada club a partir del fixture de su
propio torneo. La ficha anual de Lanús será una proyección compuesta que
referencia sólo campañas públicas permitidas de Apertura Zona B y Permanencia,
derivada en el navegador desde esos dos artefactos; no se duplica un tercer JSON
que pueda quedar desactualizado.

### Escenarios de la fecha final

Con una sola fecha pendiente, la aritmética de puntos y el desempate olímpico
permiten afirmaciones exactas y verificables. Con la tabla al 17/11/2026 (Lanús
37, Palermo 36, SAPA 35, Vicente López 34):

- **Lanús campeón** si gana; o si empata y Palermo no gana.
- **Palermo campeón** si gana y Lanús no gana.
- **SAPA campeón** si gana y Palermo no gana. No necesita una diferencia
  determinada: a igualdad de puntos con Lanús, ganó el enfrentamiento directo.

El podio es más delicado y no se debe resumir en una frase: con un empate de SAPA,
Vicente López puede pasarlo por el duelo directo, pero si además Palermo pierde
se abre una igualdad de tres que SAPA gana por la mini-tabla. La vista debe
generar esas condiciones desde los enfrentamientos y la tabla, y no escribirlas a
mano. Un ejemplo verificado de la lógica: con SAPA derrotado, sólo entra al podio
si Vicente López pierde; un empate de Vicente le alcanza para quedar arriba.

Estas condiciones deben derivarse de los datos en cada exportación, no
escribirse a mano, y mostrarse como **condiciones calculadas** con la regla y los
desempates a la vista. No reemplazan la tabla de probabilidades: la complementan.
Si cambia un resultado o la diferencia de gol, la exportación debe recalcularlas
o dejar de mostrarlas.

### Evidencia y límites del modelo

Se probó el modelo actual contra las tres competencias completas y se comparó
con una línea base de frecuencia (local/empate/visitante):

| Competencia | Log-loss del modelo | Log-loss de la línea base |
|---|---:|---:|
| Apertura Zona A | 0.85–0.86 | 1.09 |
| Apertura Zona B | 0.66–0.70 | 0.91–0.97 |
| Permanencia | 0.74–0.76 | 0.87–0.98 |

Conclusiones que cambian el plan:

- El modelo aporta información real frente a la frecuencia simple; no hace falta
  reemplazarlo por un modelo más complejo.
- **Usar los resultados del Apertura como prior no mejora la predicción de
  Permanencia** (diferencia de log-loss ≈ −0.001 ± 0.007, dentro del ruido). La
  rotación de plantel y el cambio de competencia diluyen esa señal. El Apertura
  sirve como contexto histórico y para la ficha anual, no como insumo del
  pronóstico.
- El optimizador actual ya está convergido: una implementación con pasos
  newtonianos reproduce los mismos valores. No hay ganancia pendiente ahí.
- La corrección más importante no era estadística sino **reglamentaria**: el
  desempate es olímpico. Al aplicarlo, la probabilidad de SAPA de salir campeón
  pasa de 0,04% a ~4% y Palermo deja de tener podio seguro (98,4%), porque perdió
  con Vicente López el enfrentamiento directo.
- Por lo tanto, la mejora del pronóstico está en la **presentación, el contrato
  y la regla** (podio, puestos, desempate, escenarios), no en agregar señales
  nuevas.

## Plan de entrega

> Estado al 17/11/2026: el slice público está implementado y validado localmente
> (artefactos + decodificadores + vistas + tests). No se commiteó, publicó ni
> desplegó. La publicación sigue siendo una decisión explícita.

### Fase 1 — Modelo y contratos

- [x] Generalizar el exportador, hoy fijo a Permanencia/stage 9, para exportar
  un stage público configurado (`PUBLIC_TOURNAMENT_STAGE_ID` y
  `export_public_competitions.py`), derivando temporada, cantidad de fechas y
  estado de cobertura del stage.
- [x] Crear `tournaments.json` y los tres artefactos de torneo 2026.
- [x] Añadir fixture/resultados al contrato público de torneo (`rounds` con
  cobertura por partido).
- [x] Extender el decodificador allowlist y sus pruebas de campos prohibidos
  (`reports/src/publicCompetitions.ts` + tests).
- [x] Definir la identidad validada que une Lanús en Apertura Zona B y
  Permanencia (`Club` + `CompetitionTeam`, `club_id`).

**Criterio de aceptación:** el navegador puede abrir los tres torneos sólo con
JSON estático y rechaza todo campo fuera de allowlist.

### Fase 2 — Simulación de podio

- [x] Ordenar la clasificación final de cada simulación, no sólo elegir campeón.
- [x] Contar probabilidades de 1.º, 2.º, 3.º y podio.
- [x] Reutilizar las reglas reales de puntos y desempate; no mantener una regla
  paralela en la simulación.
- [x] Agregar pruebas deterministas de sumas, desempates y repetibilidad con
  semilla fija.
- [ ] Exportar un `forecast_permanencia-2026.json` independiente.
- [x] Definir y probar el reparto de probabilidad cuando dos equipos empatan
  exactamente en puntos, diferencia y goles a favor.

**Criterio de aceptación:** para cada equipo, las probabilidades de puesto son
consistentes con el número de simulaciones y el pronóstico se reproduce sin
cambios de datos.

### Fase 2b — Marcas y ficha anual (servicio de insights)

- [x] Calcular efectividad de puntos, promedios, local/visitante, rachas, forma,
  top 5 / últimos 5, mayor victoria y derrota.
- [x] Calcular marcas de competencia (rachas, ataque, defensa, local, visitante,
  presente, puntos ideales contra los últimos cinco).
- [x] Calcular comparación anual por bloques y continuidad de plantel aproximada.
- [x] Conectar el servicio al exportador y al contrato público (`insights` dentro
  de cada artefacto de torneo).
- [x] Probar los nuevos campos con el decodificador allowlist.

**Criterio de aceptación:** las marcas se derivan del mismo dataset que la tabla
y ninguna afirmación pública requiere una regla o un dato que no esté en el JSON.

### Fase 3 — Navegación y vistas

- [x] Mantener Inicio SAPA y sumar accesos a Torneos y Pronósticos.
- [x] Crear catálogo de torneos, detalle de torneo y vista de pronósticos.
- [x] Mover la proyección que hoy vive dentro del torneo a la nueva superficie
  (`forecast_permanencia-2026.json` + `Forecast.tsx`).
- [x] Implementar la tabla de podio y las campañas expandibles G/E/P.
- [x] Construir la ficha anual de Lanús, reutilizable para otros rivales
  (`SeasonProfile.tsx`), con todos los partidos del año.
- [ ] Verificar navegación por teclado, etiquetas accesibles, móvil y contraste
  de verde/amarillo/rojo. (Parcial: etiquetas `aria-label`, texto además del
  color, responsive y foco básico; falta una auditoría formal.)

**Criterio de aceptación:** una persona puede ir de Inicio a Permanencia,
entender los hechos actuales, abrir Pronósticos y volver a la temporada anual
de Lanús sin perder el contexto.

### Fase 4 — Validación y publicación manual

- [ ] Pruebas del exportador por cada stage y pruebas de privacidad.
- [x] Pruebas del motor de pronóstico: podio, última fecha y desempates.
- [x] Pruebas del decodificador y build de `reports`.
- [x] Inspeccionar catálogo, los tres JSON de torneo, el JSON de pronóstico y
  cualquier PDF enlazado antes de publicar. (Artefactos locales inspeccionados y
  decodificados con los datos reales; la publicación sigue pendiente.)

La actualización seguirá siendo explícita tras nuevas planillas: cargar y
confirmar la fuente, exportar los artefactos estáticos, validar y recién
entonces publicar si se solicita.

## Archivos de partida

| Responsabilidad | Archivo actual |
|---|---|
| Navegación pública | `reports/src/App.tsx` |
| Catálogo de torneos | `reports/src/Competitions.tsx` |
| Detalle de torneo | `reports/src/CompetitionDetail.tsx` |
| Pronóstico y podio | `reports/src/Forecast.tsx` |
| Ficha anual del rival | `reports/src/SeasonProfile.tsx` + `reports/src/seasonData.ts` |
| Tiras G/E/P | `reports/src/resultStrip.tsx` |
| Límite de privacidad del hub | `reports/src/publicCompetitions.ts` |
| Motor de simulación | `backend/app/services/tournament_forecast_service.py` |
| Desempate olímpico compartido | `backend/app/services/competition_ranking.py` |
| Marcas y ficha anual (backend) | `backend/app/services/tournament_insights_service.py` |
| Regla de puntos compartida | `backend/app/services/standings_service.py` + `backend/config/points_rules.json` |
| Exportador del catálogo | `backend/scripts/export_public_competitions.py` |
| Exportador legacy de Permanencia | `backend/scripts/export_public_tournament.py` |
| Estado de datos 2026 | `docs/operations/permanencia-2026-status.md` |

## Límites que se mantienen

- Los resultados y campañas sólo reflejan datos observados/cargados.
- Las planillas dan goles y sanciones, no tiros ni posesiones: el hub de torneos
  no publica eficacia de tiro ni conclusiones sobre el juego.
- Una probabilidad no es pronóstico seguro, cuota de apuesta ni diagnóstico
  táctico.
- El historial de Apertura sirve como contexto de competencia; el backtest
  muestra que no mejora la predicción de Permanencia y no se usa como prior.
- La continuidad de plantel es una coincidencia de nombres normalizados, no un
  registro de pases ni una afirmación sobre lesiones o disponibilidad. Es una
  decisión interna y no se explicita en la UI pública.
- La UI pública no muestra la metodología interna, el conteo de simulaciones ni
  las decisiones de implementación; eso queda en esta documentación y en el
  código.
- El historial de Apertura no demuestra por sí mismo cómo jugará Lanús el
  próximo partido.
- La web pública no consulta la API privada ni la base de datos en tiempo real.
