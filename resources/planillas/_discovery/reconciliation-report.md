# Planilla Label-Recovery Reconciliation

**Corpus:** manifest `073577361393f977603acda98a51599bd1b93e065fb71e9c8ce8615f796e27a4` (136 canonical PDFs; 2 duplicate aliases excluded)  
**Scope:** the 72 derived fixtures left unresolved by `team-mapping.json`. No DB, PDF, mapping, alias, approval, or Git state was changed.

## Decision protocol and validation

1. A source label must be an exact key in the approved mapping to be loadable automatically. There are 17 such keys and 64 fixtures already loadable.
2. Candidate identity evidence was evaluated in this order: normalized/exact label, approved alias, exact player-name overlap in the same recovered corpus, then date/round/opponent consistency. No fuzzy club-name expansion was accepted as an alias.
3. For each row below, home/away orientation and the `H–A` score were compared with the corresponding canonical manifest record's PDF-labelled `Equip o local` / `Equipo visitante` fields. All 72 agree; no orientation or score disagreement was found. The `PDF` value is the canonical SHA prefix and filename is the same prefix under the stage directory.
4. The local Postgres service was stopped during this review (`docker compose ps` showed no services), so no read-only lookup of internal `CompetitionTeam.id` was possible. Consequently this report deliberately does **not** invent IDs.

## Label decisions

| Recovered source label | Occurrences | Proposed target | Class | Deterministic evidence | Collision / disposition |
|---|---:|---|---|---|---|
| `A.A. Argentinos Juniors D` | 15 | approved label `Argentinos Juniors D` → `{club: Argentinos Juniors, variant: D}`; internal ID unavailable | **strong** | 19 exact recovered player identities overlap from 24 vs the approved-label roster (Jaccard 0.792); same `D` suffix; both labels occur only in the same Apertura/Permanencia progression and never as opponents. | The institutional prefix differs, so it is not normalized-exact under the current conservative mapper. Do not approve until the target `CompetitionTeam.id` is read and the roster evidence is accepted. |
| `C.A. Defensores de Moreno` | 14 | suggested `{club: Defensores de Moreno, variant: null}`; ID unavailable | **needs-human-review** | Source text and a home court named `Defensores de Moreno Victorica` are internally consistent; 23 recovered players form a separate roster. | `Defensores` is a collision-prone stem; it must not be conflated with Defensores de Banfield. No approved alias or roster-to-ID evidence. |
| `C.S. y C. Deportivo Laferrere` | 14 | suggested `{club: Deportivo Laferrere, variant: null}`; ID unavailable | **needs-human-review** | 17 recovered players form a separate roster and the full formal label is stable across dates. | Prefix stripping is only a suggestion, not an approved alias or ID match. |
| `C.S. y D. Defensores de Banfield` | 18 | suggested `{club: C.S. y D. Defensores de Banfield, variant: null}`; ID unavailable | **needs-human-review** | 20 recovered players form a stable separate roster; only one incidental player-name overlap with Villa Calzada (1/43 union) and none with Defensores de Moreno. | Explicitly distinct from both `C.A. Banfield B` and Defensores de Moreno; do not resolve from the shared `Banfield`/`Defensores` words. |
| `Municipalidad de Avellaneda` | 14 | suggested `{club: Municipalidad de Avellaneda, variant: null}`; ID unavailable | **needs-human-review** | 25-player recovered roster is separate; dates/opponents form one consistent Apertura schedule. | Municipal team names are not interchangeable; no approved mapping/ID evidence. |
| `Municipalidad de San Martín (Ce.M.E.F)` | 2 | suggested same club, null variant; ID unavailable | **needs-human-review** | 13-player recovered roster; two consecutive Permanencia dates (09/08, 16/08). | Parenthetical facility/name qualifier must be retained until reviewed. |
| `Municipalidad de Tres de Febrero B` | 3 | suggested `{club: Municipalidad de Tres de Febrero, variant: B}`; ID unavailable | **needs-human-review** | 18-player recovered roster; `B` suffix consistently present over all three Permanencia sheets. | **Suffix collision risk:** `B` is identity-bearing and cannot be dropped or borrowed from another Municipalidad team. |
| `Municipalidad de Vicente López C` | 2 | suggested `{club: Municipalidad de Vicente López, variant: C}`; ID unavailable | **needs-human-review** | 19-player recovered roster; `C` suffix consistently present in both Permanencia sheets. | **Suffix collision risk:** `C` is identity-bearing and cannot be dropped or borrowed from another Municipalidad team. |

**Classification totals:** exact 0; strong 1 label / 15 occurrences; needs-human-review 7 labels / 67 occurrences. The current approved mapping remains authoritative.

## Loadability projection

| Stage | Canonical PDFs | Loadable now (exact only) | Loadable if the one strong mapping is approved | Remaining unresolved then |
|---|---:|---:|---:|---:|
| Apertura Zona A 2026 3ªM | 112 | 56 | 66 | 46 |
| Torneo Permanencia 2026 3ªM | 24 | 8 | 10 | 14 |
| **Total** | **136** | **64** | **76** | **60** |

The strong label has 15 occurrences but only 12 otherwise-loadable fixtures: three fixtures still contain another unresolved label. Therefore the exact+strong total is 76, not 79. This differs from a naive occurrence count and is intentional.

## Every unresolved fixture occurrence

Each `Missing labels` cell lists every unresolved occurrence in that PDF. `H–A` preserves PDF orientation and score.

| Stage | PDF | Date | Match | Home – Away | H–A | Missing labels |
|---|---|---|---:|---|---:|---|
| Apertura | `06e4c463` | 2026-03-29 | 2 | C.A. Banfield B – C.S. y D. Defensores de Banfield | 30–20 | C.S. y D. Defensores de Banfield |
| Apertura | `0a696099` | 2026-04-26 | 5 | C.S. y D. Defensores de Banfield – C.A. Defensores de Moreno | 27–22 | C.S. y D. Defensores de Banfield; C.A. Defensores de Moreno |
| Apertura | `0eb7448c` | 2026-06-19 | 13 | S.A.P.A. – C.A. Defensores de Moreno | 32–34 | C.A. Defensores de Moreno |
| Apertura | `16279ade` | 2026-06-14 | 12 | C.A. y S. Villa Calzada – A.A. Argentinos Juniors D | 26–23 | A.A. Argentinos Juniors D |
| Apertura | `168b3d46` | 2026-04-12 | 3 | A.A.C.F. Quilmes C – C.S. y C. Deportivo Laferrere | 39–44 | C.S. y C. Deportivo Laferrere |
| Apertura | `1bf41516` | 2026-04-12 | 3 | C.S. y D. Defensores de Banfield – C.A. y S. Villa Calzada | 20–30 | C.S. y D. Defensores de Banfield |
| Apertura | `207f1af4` | 2026-04-12 | 3 | Municipalidad de Avellaneda – Argentinos Juniors D | 30–27 | Municipalidad de Avellaneda |
| Apertura | `23b5eb48` | 2026-05-24 | 9 | S.A.P.A. – A.A. Argentinos Juniors D | 29–34 | A.A. Argentinos Juniors D |
| Apertura | `26504f88` | 2026-07-12 | 15 | C.A. Banfield B – C.A. Defensores de Moreno | 41–32 | C.A. Defensores de Moreno |
| Permanencia | `2ce572e6` | 2026-08-09 | 1 | Municipalidad de Vicente López C – A.A. Argentinos Juniors D | 28–19 | Municipalidad de Vicente López C; A.A. Argentinos Juniors D |
| Apertura | `3e781047` | 2026-05-17 | 8 | C.A. San Telmo B – Municipalidad de Avellaneda | 25–18 | Municipalidad de Avellaneda |
| Apertura | `3ed3d994` | 2026-06-07 | 11 | A.A.C.F. Quilmes C – C.S. y D. Defensores de Banfield | 26–26 | C.S. y D. Defensores de Banfield |
| Apertura | `40b613ae` | 2026-06-28 | 13 | Club Deportivo Morón – C.S. y D. Defensores de Banfield | 37–29 | C.S. y D. Defensores de Banfield |
| Apertura | `49675794` | 2026-05-10 | 7 | C.S. y C. Deportivo Laferrere – S.A.P.A. | 44–28 | C.S. y C. Deportivo Laferrere |
| Apertura | `4fcc6f38` | 2026-03-29 | 2 | C.S. y C. Deportivo Laferrere – Ci.De.Co. B | 38–33 | C.S. y C. Deportivo Laferrere |
| Apertura | `51b6349b` | 2026-06-07 | 11 | A.A. Argentinos Juniors D – C.A. Banfield B | 28–27 | A.A. Argentinos Juniors D |
| Permanencia | `5400cb62` | 2026-08-23 | 3 | C.A. Banfield B – A.A. Argentinos Juniors D | 41–24 | A.A. Argentinos Juniors D |
| Apertura | `58cb62e2` | 2026-05-17 | 8 | C.A. Defensores de Moreno – Ci.De.Co. B | 20–33 | C.A. Defensores de Moreno |
| Apertura | `5acbd4c9` | 2026-07-12 | 15 | S.A.P.A. – C.S. y D. Defensores de Banfield | 32–32 | C.S. y D. Defensores de Banfield |
| Apertura | `5c2c13fe` | 2026-04-19 | 4 | A.A. Argentinos Juniors D – Ci.De.Co. B | 19–29 | A.A. Argentinos Juniors D |
| Apertura | `6284e655` | 2026-05-03 | 6 | A.A. Argentinos Juniors D – C.A. Temperley | 34–28 | A.A. Argentinos Juniors D |
| Permanencia | `629f2340` | 2026-08-16 | 2 | C.A. Defensores de Moreno – U.N.La.M. | 21–22 | C.A. Defensores de Moreno |
| Apertura | `62d83c69` | 2026-05-31 | 10 | Muñiz Handball B – Municipalidad de Avellaneda | 19–27 | Municipalidad de Avellaneda |
| Apertura | `66dda079` | 2026-05-03 | 6 | U.N.La.M. – C.S. y C. Deportivo Laferrere | 27–31 | C.S. y C. Deportivo Laferrere |
| Permanencia | `68ff5491` | 2026-08-16 | 2 | C.S. y D. Defensores de Banfield – C.A. Banfield B | 27–28 | C.S. y D. Defensores de Banfield |
| Apertura | `6ae20454` | 2026-07-12 | 15 | C.S. y C. Deportivo Laferrere – Muñiz Handball B | 32–18 | C.S. y C. Deportivo Laferrere |
| Permanencia | `6cbc0df9` | 2026-08-09 | 1 | S.A.P.A. – C.S. y D. Defensores de Banfield | 27–36 | C.S. y D. Defensores de Banfield |
| Apertura | `6d8042d7` | 2026-04-19 | 4 | C.A. Banfield B – Municipalidad de Avellaneda | 20–18 | Municipalidad de Avellaneda |
| Permanencia | `7149f4f5` | 2026-08-16 | 2 | Palermo Handball – Municipalidad de Tres de Febrero B | 28–26 | Municipalidad de Tres de Febrero B |
| Apertura | `77424089` | 2026-06-28 | 13 | A.A. Argentinos Juniors D – Club Comunicaciones C | 22–27 | A.A. Argentinos Juniors D |
| Permanencia | `7a49553e` | 2026-08-09 | 1 | Municipalidad de San Martín (Ce.M.E.F) – Muñiz Handball B | 19–23 | Municipalidad de San Martín (Ce.M.E.F) |
| Apertura | `7a9c7958` | 2026-06-14 | 12 | C.A. Defensores de Moreno – C.S. y C. Deportivo Laferrere | 29–34 | C.A. Defensores de Moreno; C.S. y C. Deportivo Laferrere |
| Permanencia | `7ab5b597` | 2026-08-23 | 3 | Municipalidad de Pilar – C.S. y D. Defensores de Banfield | 25–23 | C.S. y D. Defensores de Banfield |
| Apertura | `7e5e3b0c` | 2026-05-31 | 10 | U.N.La.M. – A.A. Argentinos Juniors D | 24–29 | A.A. Argentinos Juniors D |
| Apertura | `87824fd1` | 2026-05-24 | 9 | A.A.C.F. Quilmes C – C.A. Defensores de Moreno | 31–24 | C.A. Defensores de Moreno |
| Apertura | `8d91507b` | 2026-06-28 | 13 | A.A.C.F. Quilmes C – Municipalidad de Avellaneda | 25–31 | Municipalidad de Avellaneda |
| Apertura | `8ec581e2` | 2026-03-22 | 1 | C.S. y D. Defensores de Banfield – Argentinos Juniors D | 28–25 | C.S. y D. Defensores de Banfield |
| Apertura | `92933072` | 2026-06-14 | 12 | Municipalidad de Avellaneda – Ci.De.Co. B | 18–23 | Municipalidad de Avellaneda |
| Apertura | `92dd6bc0` | 2026-03-24 | 1 | Municipalidad de Avellaneda – C.S. y C. Deportivo Laferrere | 29–26 | Municipalidad de Avellaneda; C.S. y C. Deportivo Laferrere |
| Apertura | `95c1fb04` | 2026-06-07 | 11 | C.S. y C. Deportivo Laferrere – Club Comunicaciones C | 27–32 | C.S. y C. Deportivo Laferrere |
| Apertura | `9cb2938d` | 2026-06-19 | 11 | Municipalidad de Avellaneda – U.N.La.M. | 30–19 | Municipalidad de Avellaneda |
| Apertura | `9d109e9c` | 2026-05-31 | 10 | C.A. y S. Villa Calzada – C.S. y C. Deportivo Laferrere | 30–30 | C.S. y C. Deportivo Laferrere |
| Apertura | `a29fcdc5` | 2026-05-03 | 6 | C.A. San Telmo B – C.S. y D. Defensores de Banfield | 28–22 | C.S. y D. Defensores de Banfield |
| Apertura | `acb26c27` | 2026-04-26 | 5 | Municipalidad de Avellaneda – C.A. y S. Villa Calzada | 18–18 | Municipalidad de Avellaneda |
| Apertura | `adfcc64d` | 2026-05-31 | 10 | C.A. Defensores de Moreno – C.A. Temperley | 22–30 | C.A. Defensores de Moreno |
| Apertura | `ae1c18ce` | 2026-07-05 | 14 | C.S. y D. Defensores de Banfield – C.S. y C. Deportivo Laferrere | 28–35 | C.S. y D. Defensores de Banfield; C.S. y C. Deportivo Laferrere |
| Apertura | `ae2bd97e` | 2026-05-03 | 6 | Club Comunicaciones C – Municipalidad de Avellaneda | 24–25 | Municipalidad de Avellaneda |
| Apertura | `bac63f38` | 2026-04-19 | 4 | C.S. y C. Deportivo Laferrere – C.A. Temperley | 40–28 | C.S. y C. Deportivo Laferrere |
| Apertura | `c034f812` | 2026-05-10 | 7 | Municipalidad de Avellaneda – C.A. Defensores de Moreno | 35–15 | Municipalidad de Avellaneda; C.A. Defensores de Moreno |
| Permanencia | `c30c4379` | 2026-08-23 | 3 | Municipalidad de Vicente López C – S.A.G. Polvorines D | 29–26 | Municipalidad de Vicente López C |
| Apertura | `c7242176` | 2026-05-10 | 7 | Club Deportivo Morón – A.A. Argentinos Juniors D | 27–27 | A.A. Argentinos Juniors D |
| Permanencia | `cfa52ff0` | 2026-08-23 | 3 | Municipalidad de Tres de Febrero B – C.A. Defensores de Moreno | 38–26 | Municipalidad de Tres de Febrero B; C.A. Defensores de Moreno |
| Apertura | `d073a201` | 2026-04-26 | 5 | Club Deportivo Morón – C.S. y C. Deportivo Laferrere | 28–38 | C.S. y C. Deportivo Laferrere |
| Permanencia | `d14d6166` | 2026-08-16 | 2 | S.A.G. Polvorines D – Municipalidad de San Martín (Ce.M.E.F) | 22–16 | Municipalidad de San Martín (Ce.M.E.F) |
| Apertura | `d1f0916e` | 2026-05-31 | 10 | C.S. y D. Defensores de Banfield – Ci.De.Co. B | 28–28 | C.S. y D. Defensores de Banfield |
| Apertura | `d5aef2fc` | 2026-07-12 | 15 | A.A. Argentinos Juniors D – C.A. San Telmo B | 19–31 | A.A. Argentinos Juniors D |
| Apertura | `d6e5fa90` | 2026-07-05 | 14 | C.A. Defensores de Moreno – A.A. Argentinos Juniors D | 22–29 | C.A. Defensores de Moreno; A.A. Argentinos Juniors D |
| Apertura | `d88ad5ec` | 2026-05-10 | 7 | C.S. y D. Defensores de Banfield – U.N.La.M. | 29–31 | C.S. y D. Defensores de Banfield |
| Permanencia | `dab3bc3b` | 2026-08-09 | 1 | U.N.La.M. – Municipalidad de Tres de Febrero B | 23–12 | Municipalidad de Tres de Febrero B |
| Apertura | `de06d6df` | 2026-04-26 | 5 | A.A.C.F. Quilmes C – A.A. Argentinos Juniors D | 24–27 | A.A. Argentinos Juniors D |
| Apertura | `e046de08` | 2026-03-29 | 2 | S.A.P.A. – Municipalidad de Avellaneda | 27–34 | Municipalidad de Avellaneda |
| Apertura | `e35d0597` | 2026-05-17 | 8 | A.A. Argentinos Juniors D – C.S. y C. Deportivo Laferrere | 31–43 | A.A. Argentinos Juniors D; C.S. y C. Deportivo Laferrere |
| Permanencia | `e65db31c` | 2026-08-16 | 2 | A.A. Argentinos Juniors D – S.A.P.A. | 23–29 | A.A. Argentinos Juniors D |
| Apertura | `eb70dcd0` | 2026-04-19 | 4 | Club Comunicaciones C – C.S. y D. Defensores de Banfield | 33–22 | C.S. y D. Defensores de Banfield |
| Apertura | `ef1e286c` | 2026-07-09 | 15 | Club Deportivo Morón – Municipalidad de Avellaneda | 19–24 | Municipalidad de Avellaneda |
| Apertura | `f01ed450` | 2026-05-03 | 6 | C.A. Defensores de Moreno – Muñiz Handball B | 11–22 | C.A. Defensores de Moreno |
| Permanencia | `f803f086` | 2026-08-09 | 1 | Municipalidad de Pilar – C.A. Defensores de Moreno | 31–19 | C.A. Defensores de Moreno |
| Apertura | `f98382b1` | 2026-06-15 | 12 | C.S. y D. Defensores de Banfield – C.A. Temperley | 31–38 | C.S. y D. Defensores de Banfield |
| Apertura | `fb0f8683` | 2026-06-07 | 11 | Club Deportivo Morón – C.A. Defensores de Moreno | 29–23 | C.A. Defensores de Moreno |
| Apertura | `fbe11e0d` | 2026-05-17 | 8 | C.S. y D. Defensores de Banfield – Muñiz Handball B | 26–23 | C.S. y D. Defensores de Banfield |
| Apertura | `fe38e946` | 2026-06-27 | 13 | C.S. y C. Deportivo Laferrere – C.A. San Telmo B | 26–34 | C.S. y C. Deportivo Laferrere |
| Apertura | `feebb0e7` | 2026-05-24 | 9 | Municipalidad de Avellaneda – C.S. y D. Defensores de Banfield | 34–22 | Municipalidad de Avellaneda; C.S. y D. Defensores de Banfield |

## Risks and safest next step

- **Risk:** the seven unreviewed labels may create a new club/variant if imported without an approved ID mapping; suffix loss would merge distinct `B`/`C` teams.
- **Risk:** shared terms (`Defensores`, `Banfield`, `Municipalidad`) are insufficient evidence and would create false identity merges.
- **Risk:** the `A.A.`/non-`A.A.` Argentinos labels are strongly, but not textually exactly, linked; approving it without checking the current `CompetitionTeam.id` would bypass the ID requirement.

**Safest next step:** bring up the DB only for a read-only query of the two stages' `CompetitionTeam`/club/variant rows; have a human approve or reject the one strong Argentinos mapping against that ID, then separately review the seven collision-sensitive labels. Only after explicit approval should any mapping or fixture derivation be changed.
