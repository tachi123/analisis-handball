import sys
sys.path.insert(0, '/app/app')
sys.path.insert(0, '/app/scripts')
from sqlalchemy.orm import joinedload as jl
from app.database import SessionLocal
from app.models import Match, MatchSquad, CanonicalEvent, CanonicalEventRevision, CanonicalEvidence, OfficialSnapshot, AnalysisSession, VideoSource, GoalkeeperShot, ScheduledMatch
from app.services.canonical_analysis_service import read_metrics, read_reconciliation, read_state
from app.services.report_service import ReportService, PUBLIC_METRIC_NAMES, is_public_metric
from unicodedata import normalize
import json
import re

def slugify(name: str) -> str:
    nfkd = normalize('NFKD', name)
    ascii_only = nfkd.encode('ascii', 'ignore').decode('ascii')
    lowered = ascii_only.lower()
    parts = ''.join(char if char.isalnum() or char == ' ' else ' ' for char in lowered).split()
    return '-'.join(parts) or 'unknown'

db = SessionLocal()

# Override DATABASE_URL
import os
os.environ['DATABASE_URL'] = 'postgresql://postgres:postgres@localhost:5435/sapa_stats'

match = db.get(Match, 99)
print('Exporting Match ' + str(match.id))

metrics_data = read_metrics(db, 99)
eligibility = metrics_data.get('eligibility', {})
print('Eligible events: ' + str(eligibility.get('eligible', 0)))

recon_data = read_reconciliation(db, 99)

events = metrics_data.get('events', [])
eligible_events = [e for e in events if e.get('active') and e.get('payload', {}).get('fact_kind') == 'observed'
                   and e.get('payload', {}).get('evidence_state') == 'confirmed']

evidence_rows = []
seq = 1
for event in eligible_events:
    payload = event['payload']
    revision = event.get('revision', 1)
    event_id = event['id']
    ref = 'Sequence ' + str(seq)
    seq += 1
    period = payload.get('period', 1)
    reg_seconds = payload.get('regulation_seconds')
    clock_unverified = bool(payload.get('clock_unverified'))

    evidence_rows.append({
        'reference': ref,
        'period': period,
        'regulation_seconds': reg_seconds,
        'clock_unverified': clock_unverified,
        'public_observation': payload.get('team_action', 'Canonical observation'),
        'public_approved': True,
        'media_public_approved': False,
        'public_media_url': None,
    })

# Build players from match squad
players_data = []
squad = db.query(MatchSquad).options(jl(MatchSquad.player)).filter_by(match_id=99).all()

gk_designated_players = set()
if match.canonical_analysis_enabled:
    for event in eligible_events:
        payload = event['payload']
        if payload.get('kind') == 'shot' and payload.get('goalkeeper_id') is not None:
            gk_designated_players.add(payload['goalkeeper_id'])

squad_player_ids = set()
for s in squad:
    pid = s.player_id if s.player else None
    if pid is not None:
        squad_player_ids.add(pid)

for s in squad:
    player = s.player
    is_gk = s.is_goalkeeper
    player_id = player.id if player else None

    gk_designated = (player_id in gk_designated_players) if player_id is not None else False

    if is_gk or gk_designated:
        role = 'goalkeeper'
        gk_metrics = {'saves': 0, 'shots_faced': 0, 'goals_conceded': 0, 'save_rate': None}
        gk_count = 0

        for event in eligible_events:
            payload = event['payload']
            if payload.get('kind') == 'shot' and payload.get('goalkeeper_id') == player_id:
                gk_count += 1
                outcome = payload.get('outcome')
                if outcome == 'save':
                    gk_metrics['saves'] += 1
                elif outcome == 'goal':
                    gk_metrics['goals_conceded'] += 1
                gk_metrics['shots_faced'] += 1

        denom = gk_metrics['saves'] + gk_metrics['goals_conceded']
        if denom:
            gk_metrics['save_rate'] = round(gk_metrics['saves'] / denom, 4)

        player_name = player.name if player else ('Goalkeeper ' + (str(player.default_jersey_number) if player and player.default_jersey_number else '1'))

        if player and player.team_id:
            if player.team_id == match.home_team_id:
                side = 'home'
            elif player.team_id == match.away_team_id:
                side = 'away'
            else:
                side = 'unknown'
        else:
            side = 'unknown'

        players_data.append({
            'slug': (slugify(player.name) if player and player.name else ('gk-' + (str(player.default_jersey_number) if player and player.default_jersey_number else '1')))[:32],
            'name': player_name,
            'jersey_number': player.default_jersey_number if player else 1,
            'team_side': side,
            'role': role,
            'metrics': gk_metrics,
            'evidence': [],
        })
    else:
        field_shots = 0
        field_goals = 0
        field_assists = 0
        field_turnovers = 0
        field_recoveries = 0
        field_sanctions = 0

        for event in eligible_events:
            payload = event['payload']
            kind = payload.get('kind')
            outcome = payload.get('outcome')
            pid = payload.get('player_id')

            if pid == player_id:
                if kind == 'shot':
                    field_shots += 1
                    if outcome == 'goal':
                        field_goals += 1
                elif kind == 'turnover':
                    field_turnovers += 1
                elif kind == 'recovery':
                    field_recoveries += 1
                elif kind == 'foul_sanction':
                    field_sanctions += 1

        shot_conversion = None
        if field_shots > 0:
            shot_conversion = round(field_goals / field_shots, 4)

        player_name = player.name if player else ('Player ' + str(player_id) if player_id else 'Unknown')

        if player and player.team_id:
            if player.team_id == match.home_team_id:
                side = 'home'
            elif player.team_id == match.away_team_id:
                side = 'away'
            else:
                side = 'unknown'
        else:
            side = 'unknown'

        players_data.append({
            'slug': (slugify(player.name) if player and player.name else ('player-' + str(player_id)))[:32],
            'name': player_name,
            'jersey_number': player.default_jersey_number if player else 0,
            'team_side': side,
            'role': 'field_player',
            'metrics': {
                'shot_conversion': shot_conversion,
                'shots': field_shots,
                'goals': field_goals,
                'assists': field_assists,
                'turnovers': field_turnovers,
                'recoveries': field_recoveries,
                'sanctions': field_sanctions,
            },
            'evidence': [],
        })

home_team = match.home_team
away_team = match.away_team
source_label = 'Match broadcast'
source_status = 'public_reference'

if match.canonical_analysis_enabled:
    source_label = 'Canonical eligible event ledger'
    source_status = 'canonical-eligible'

# ── Build team_summary ─────────────────────────────────────────────
home_eligible = [e for e in eligible_events if e['payload'].get('team_id') == match.home_team_id]
away_eligible = [e for e in eligible_events if e['payload'].get('team_id') == match.away_team_id]

def team_stats(events):
    shots = 0; goals = 0; turnovers = 0; recoveries = 0; sanctions = 0
    for ev in events:
        payload = ev['payload']
        kind = payload.get('kind')
        outcome = payload.get('outcome')
        pid = payload.get('player_id')
        tid = payload.get('team_id')
        if kind == 'shot':
            shots += 1
            if outcome == 'goal':
                goals += 1
        elif kind == 'turnover':
            turnovers += 1
        elif kind == 'recovery':
            recoveries += 1
        elif kind == 'foul_sanction':
            sanctions += 1
    return {'shots': shots, 'goals': goals, 'turnovers': turnovers, 'recoveries': recoveries, 'sanctions': sanctions}

home_stats = team_stats(home_eligible)
away_stats = team_stats(away_eligible)

team_summary = {
    'home': {
        'name': home_team.name,
        'side': 'home',
        **home_stats,
    },
    'away': {
        'name': away_team.name,
        'side': 'away',
        **away_stats,
    },
}

# ── Build incidents ──────────────────────────────────────────────────
# Incidents are chronological, period-separated events with public-safe data
incidents = []
for ev in eligible_events:
    payload = ev['payload']
    kind = payload.get('kind')
    outcome = payload.get('outcome')
    player_id = payload.get('player_id')
    team_id = payload.get('team_id')
    period = payload.get('period')
    reg_seconds = payload.get('regulation_seconds')
    clock_unverified = bool(payload.get('clock_unverified'))

    # Get player name safely
    player_name = None
    player_slug = None
    if player_id is not None:
        player = next((p for p in players_data if p.get('jersey_number') or p.get('role')), None)
        # Find by player_id in squad
        for s in squad:
            if s.player_id == player_id and s.player:
                player_name = s.player.name
                player_slug = slugify(s.player.name)[:32]
                break

    # Map kind+outcome to incident type (Spanish labels)
    incident_type_map = {
        'shot': 'Lanzamiento',
        'turnover': 'Pérdida',
        'recovery': 'Recuperación',
        'foul_sanction': 'Sanción',
        'other': 'Incidencia de juego',
    }
    incident_type = incident_type_map.get(kind, 'Incidencia')

    # Map outcome to result description
    outcome_map = {
        'goal': 'Gol',
        'save': 'Atajada',
        'miss': 'Fuera',
        'woodwork': 'Palo/Travesaño',
        'blocked': 'Bloqueado',
        'bad_pass': 'Pase perdido',
        'bad_reception': 'Recepción perdida',
        'foul': 'Falta',
        'yellow_card': 'Tarjeta amarilla',
        'red_card': 'Tarjeta roja',
        'two_minute_exclusion': 'Exclusión 2 min',
        'blue_card': 'Tarjeta azul',
    }
    outcome_desc = outcome_map.get(outcome, outcome or '')

    # Clock source label
    if reg_seconds is not None and not clock_unverified:
        clock_label = 'Tiempo oficial ' + str(reg_seconds // 60) + ':' + str(reg_seconds % 60).zfill(2)
    elif clock_unverified:
        clock_label = 'Reloj sin verificar'
    else:
        clock_label = None

    incidents.append({
        'reference': 'Sequence ' + str(ev.get('sequence', 1)),
        'period': period,
        'regulation_seconds': reg_seconds,
        'clock_unverified': clock_unverified,
        'clock_label': clock_label,
        'incident_type': incident_type,
        'outcome': outcome_desc,
        'team_side': 'home' if team_id == match.home_team_id else ('away' if team_id == match.away_team_id else 'unknown'),
        'player_name': player_name,
        'player_slug': player_slug,
        'event_kind': kind,
    })

# Sort incidents by period and regulation_seconds, then sequence
incidents.sort(key=lambda x: (x['period'] or 0, x['regulation_seconds'] or 0, x['reference']))

package_dict = {
    'match_id': 99,
    'report_version': 1,
    'schema_version': 'public-report-v1',
    'match': match,
    'home_team': home_team,
    'away_team': away_team,
    'coaching_question': 'Analysis of Match ' + str(match.id),
    'pattern_statement': 'Match analysis covering ' + str(len(eligible_events)) + ' approved canonical events',
    'action_kind': 'keep',
    'action_text': 'Export approved facts for public report',
    'uncertainty_disclosure': 'Generated from canonical analysis; partial data may apply',
    'source_label': source_label,
    'source_status': source_status,
    'metrics': metrics_data.get('metrics', {}),
    'reconciliation': recon_data.get('discrepancies', []),
    'evidence': evidence_rows,
    'players': players_data,
    'team_summary': team_summary,
    'incidents': incidents,
}

# Now run public_projection_from_package_type logic
evidence_items = []
for item in package_dict.get('evidence', []):
    if not item.get('public_approved', True):
        continue
    public_item = {
        'reference': item.get('reference'),
        'period': item.get('period'),
        'regulation_seconds': item.get('regulation_seconds'),
        'clock_unverified': item.get('clock_unverified', False),
        'observation': item.get('public_observation', ''),
        'media_available': bool(item.get('media_public_approved', False) and item.get('public_media_url')),
    }
    if public_item['media_available']:
        public_item['media_url'] = item.get('public_media_url')
    evidence_items.append(public_item)

metrics = {}
for name, value in package_dict.get('metrics', {}).items():
    if is_public_metric(name) and isinstance(value, dict):
        metric = {}
        for field in ('count', 'numerator', 'denominator', 'excluded', 'unknown', 'clock_unverified'):
            if field in value:
                metric[field] = value[field]
        if metric:
            metrics[name] = metric

all_periods = sorted({item.get('period') for item in evidence_items if item.get('period') is not None})
coverage = None
if all_periods:
    has_half1 = 1 in all_periods
    has_half2 = 2 in all_periods
    if has_half1 and has_half2:
        status = 'complete'
        label = None
    else:
        status = 'partial'
        analyzed = [p for p in all_periods if p is not None]
        label = 'Analysis covering periods ' + ', '.join(str(p) for p in analyzed)
    coverage = {
        'analyzed_periods': all_periods,
        'status': status,
        'label': label,
    }

report = {
    'schema_version': package_dict.get('schema_version', 'public-report-v1'),
    'report_version': package_dict.get('report_version', 1),
    'match': {
        'date': package_dict['match'].date.isoformat() if hasattr(package_dict['match'], 'date') and package_dict['match'].date else (package_dict.get('match', {}).get('date').isoformat() if isinstance(package_dict.get('match'), dict) and package_dict.get('match').get('date') else None),
        'home_team': package_dict['match'].home_team.name if hasattr(package_dict['match'], 'home_team') else (package_dict.get('match', {}).get('home_team', {}).get('name') if isinstance(package_dict.get('match'), dict) else None),
        'away_team': package_dict['match'].away_team.name if hasattr(package_dict['match'], 'away_team') else (package_dict.get('match', {}).get('away_team', {}).get('name') if isinstance(package_dict.get('match'), dict) else None),
    },
    'source': {'label': package_dict.get('source_label', ''), 'status': package_dict.get('source_status', '')},
    'coaching': {
        'question': package_dict.get('coaching_question', ''),
        'pattern_statement': package_dict.get('pattern_statement', ''),
        'action': {'kind': package_dict.get('action_kind', 'keep'), 'text': package_dict.get('action_text', '')},
    },
    'metrics': metrics,
    'reconciliation': package_dict.get('reconciliation', []),
    'uncertainty_disclosure': package_dict.get('uncertainty_disclosure', ''),
    'players': package_dict.get('players'),
    'evidence': evidence_items,
    'coverage': coverage,
    'team_summary': team_summary,
    'incidents': incidents,
}

# Verify all player slugs pass the regex
print('Players: ' + str(len(report.get('players', []))))
all_slugs_valid = True
for p in report.get('players', []):
    slug = p['slug']
    valid = bool(re.match(r'^[a-z0-9-]+$', slug))
    if not valid:
        all_slugs_valid = False
        print('  INVALID slug: ' + p['name'] + ' -> ' + slug)
if all_slugs_valid:
    print('  All player slugs are valid (pass /^[a-z0-9-]+$/ regex)')

# Write the report
output_path = 'reports/public/report.json'
with open(output_path, 'w', encoding='utf-8', newline='') as f:
    json.dump(report, f, ensure_ascii=False, indent=2)

# Also write the legacy-matched path for compatibility
legacy_path = 'reports/public/report_match99.json'
import shutil
shutil.copy(output_path, legacy_path)

print('Report exported to ' + output_path)
print('Legacy path also updated: ' + legacy_path)

# Print summary
print()
print('---SUMMARY---')
summary = {
    'match_id': match.id,
    'home_team': match.home_team.name if match.home_team else None,
    'away_team': match.away_team.name if match.away_team else None,
    'date': str(match.date) if match.date else None,
    'schema_version': report['schema_version'],
    'report_version': report['report_version'],
    'coverage_status': report.get('coverage', {}).get('status', 'none'),
    'evidence_count': len(report.get('evidence', [])),
    'players_count': len(report.get('players', [])),
    'metrics_count': len(metrics),
    'home_team_name': match.home_team.name,
    'away_team_name': match.away_team.name,
    'team_summary': team_summary,
    'incidents_count': len(incidents),
}
print(json.dumps(summary, ensure_ascii=False))

db.close()