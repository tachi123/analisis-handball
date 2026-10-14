import sys
sys.path.insert(0, '/app/app')
sys.path.insert(0, '/app/scripts')
from sqlalchemy.orm import joinedload as jl
from app.database import SessionLocal
from app.models import Match, MatchSquad, CanonicalEvent, CanonicalEventRevision, CanonicalEvidence, OfficialSnapshot, AnalysisSession, AnalysisRun, VideoSource, GoalkeeperShot, ScheduledMatch
from app.services.canonical_analysis_service import read_metrics, read_reconciliation, read_state
from app.services.report_service import ReportService, PUBLIC_METRIC_NAMES, is_public_metric
from unicodedata import normalize
import json
import re
from pathlib import Path

def slugify(name: str) -> str:
    nfkd = normalize('NFKD', name)
    ascii_only = nfkd.encode('ascii', 'ignore').decode('ascii')
    lowered = ascii_only.lower()
    parts = ''.join(char if char.isalnum() or char == ' ' else ' ' for char in lowered).split()
    return '-'.join(parts) or 'unknown'

def public_report_key(report: dict) -> str:
    match = report['match']
    return '-'.join((match.get('date') or 'undated', slugify(match.get('home_team') or 'home'), slugify(match.get('away_team') or 'away')))

def write_public_catalog(directory: Path) -> None:
    entries = []
    for path in directory.glob('report_*.json'):
        try:
            candidate = json.loads(path.read_text(encoding='utf-8'))
            if candidate.get('schema_version') != 'public-report-v1':
                continue
            key = public_report_key(candidate)
            if path.name != f'report_{key}.json':
                continue
            match = candidate.get('match', {})
            home_team, away_team = match.get('home_team'), match.get('away_team')
            if not isinstance(home_team, str) or not isinstance(away_team, str):
                continue
            entries.append({'key': key, 'date': match.get('date'), 'home_team': home_team, 'away_team': away_team})
        except (OSError, ValueError, TypeError):
            continue
    entries.sort(key=lambda entry: (entry['date'] or '', entry['home_team'], entry['away_team'], entry['key']), reverse=True)
    (directory / 'reports.json').write_text(json.dumps({'schema_version': 'public-report-catalog-v1', 'reports': entries}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

def public_output_paths(output_path: Path, catalog_directory: Path | None = None) -> tuple[Path, Path]:
    """Return the fallback report path and the directory containing all catalog artifacts."""
    directory = catalog_directory or output_path.parent
    return output_path, directory

db = SessionLocal()

import os

try:
    match_id = int(os.getenv('PUBLIC_REPORT_MATCH_ID', '99'))
except ValueError as error:
    raise RuntimeError('PUBLIC_REPORT_MATCH_ID must be an integer') from error

match = db.get(Match, match_id)
if match is None:
    raise RuntimeError('Match ' + str(match_id) + ' was not found')
print('Exporting Match ' + str(match.id))
active_run = db.query(AnalysisRun).filter_by(match_id=match_id, status='active').one_or_none()
if match.canonical_analysis_enabled and active_run is None:
    raise RuntimeError('Match ' + str(match_id) + ' has canonical analysis enabled but no active analysis run')

metrics_data = read_metrics(db, match_id)
eligibility = metrics_data.get('eligibility', {})
print('Eligible events: ' + str(eligibility.get('eligible', 0)))

recon_data = read_reconciliation(db, match_id)

events = metrics_data.get('events', [])
eligible_events = [e for e in events if e.get('active') and e.get('payload', {}).get('fact_kind') == 'observed'
                   and e.get('payload', {}).get('evidence_state') == 'confirmed']

# Video review persists the exact player position as evidence. Publish that
# timestamp only for the matching active revision, never an inferred clock map.
eligible_by_id = {event['id']: event for event in eligible_events}
video_seconds_by_event = {}
if eligible_by_id:
    revisions = db.query(CanonicalEventRevision).options(jl(CanonicalEventRevision.evidence)).filter(
        CanonicalEventRevision.event_id.in_(eligible_by_id)
    ).all()
    for revision in revisions:
        event = eligible_by_id.get(revision.event_id)
        if not event or revision.revision != event.get('revision'):
            continue
        evidence = next((item for item in revision.evidence if item.kind == 'video' and item.video_anchor_seconds is not None), None)
        if evidence:
            video_seconds_by_event[revision.event_id] = evidence.video_anchor_seconds

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
squad = db.query(MatchSquad).options(jl(MatchSquad.player)).filter_by(match_id=match_id).all()

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
        gk_metrics = {
            'saves': 0, 'shots_faced': 0, 'goals_conceded': 0, 'save_rate': None,
            'saves_7m': 0, 'shots_faced_7m': 0, 'goals_conceded_7m': 0, 'save_rate_7m': None,
            'saves_counterattack': 0, 'shots_faced_counterattack': 0, 'goals_conceded_counterattack': 0, 'save_rate_counterattack': None,
        }
        gk_count = 0

        for event in eligible_events:
            payload = event['payload']
            if payload.get('kind') == 'shot' and payload.get('goalkeeper_id') == player_id:
                gk_count += 1
                outcome = payload.get('outcome')
                shot_zone = payload.get('shot_zone')
                if outcome == 'save':
                    gk_metrics['saves'] += 1
                elif outcome == 'goal':
                    gk_metrics['goals_conceded'] += 1
                if outcome in {'save', 'goal'}:
                    gk_metrics['shots_faced'] += 1
                    if shot_zone == 7:
                        gk_metrics['shots_faced_7m'] += 1
                        gk_metrics['saves_7m' if outcome == 'save' else 'goals_conceded_7m'] += 1
                    elif shot_zone == 8:
                        gk_metrics['shots_faced_counterattack'] += 1
                        gk_metrics['saves_counterattack' if outcome == 'save' else 'goals_conceded_counterattack'] += 1

        denom = gk_metrics['saves'] + gk_metrics['goals_conceded']
        if denom:
            gk_metrics['save_rate'] = round(gk_metrics['saves'] / denom, 4)
        for suffix in ('7m', 'counterattack'):
            faced = gk_metrics[f'shots_faced_{suffix}']
            if faced:
                gk_metrics[f'save_rate_{suffix}'] = round(gk_metrics[f'saves_{suffix}'] / faced, 4)

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
        field_on_target = 0
        field_saves_against = 0
        field_outside_or_woodwork = 0

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
                        field_on_target += 1
                    elif outcome == 'save':
                        field_on_target += 1
                        field_saves_against += 1
                    elif outcome in {'miss', 'woodwork'}:
                        field_outside_or_woodwork += 1
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
                'shots_on_target': field_on_target,
                'saves_against': field_saves_against,
                'outside_or_woodwork': field_outside_or_woodwork,
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

# The report exposes only a validated public YouTube id, never the stored source URL.
# Use the active run's session video source for deterministic output.
video_source = None
if active_run:
    session = db.query(AnalysisSession).filter_by(match_id=match_id, run_id=active_run.id).first()
    if session and session.video_source_id:
        video_source = db.get(VideoSource, session.video_source_id)
if video_source is None:
    # Fallback to any YouTube source for this match (legacy data)
    video_source = db.query(VideoSource).filter_by(match_id=match_id, provider='youtube').first()
public_video = None
if video_source and re.fullmatch(r'[A-Za-z0-9_-]{6,}', video_source.provider_video_id or ''):
    public_video = {
        'provider': 'youtube',
        'video_id': video_source.provider_video_id,
        'availability': video_source.availability_state,
    }

# ── Build team_summary ─────────────────────────────────────────────
home_eligible = [e for e in eligible_events if e['payload'].get('team_id') == match.home_team_id]
away_eligible = [e for e in eligible_events if e['payload'].get('team_id') == match.away_team_id]

def team_stats(events):
    shots = 0; goals = 0; turnovers = 0; recoveries = 0; sanctions = 0; shots_on_target = 0; saves_against = 0; outside_or_woodwork = 0
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
                shots_on_target += 1
            elif outcome == 'save':
                shots_on_target += 1
                saves_against += 1
            elif outcome in {'miss', 'woodwork'}:
                outside_or_woodwork += 1
        elif kind == 'turnover':
            turnovers += 1
        elif kind == 'recovery':
            recoveries += 1
        elif kind == 'foul_sanction':
            sanctions += 1
    return {'shots': shots, 'goals': goals, 'turnovers': turnovers, 'recoveries': recoveries, 'sanctions': sanctions, 'shots_on_target': shots_on_target, 'saves_against': saves_against, 'outside_or_woodwork': outside_or_woodwork}

def public_side(payload):
    team_id = payload.get('team_id')
    return 'home' if team_id == match.home_team_id else ('away' if team_id == match.away_team_id else 'unknown')

def verified_timed(event):
    payload = event['payload']
    return payload.get('period') in {1, 2} and isinstance(payload.get('regulation_seconds'), (int, float)) and not payload.get('clock_unverified')

def period_elapsed_seconds(payload):
    # Some sources store the second half on the continuous match clock; others
    # restart it at zero. Modulo keeps both representations in their half.
    return int(payload['regulation_seconds']) % 1800

def event_reference(event):
    return 'Sequence ' + str(event.get('sequence', 1))

def public_clock(payload):
    return {'period': payload['period'], 'seconds': period_elapsed_seconds(payload)}

def build_phase_analysis(events):
    timed = sorted((event for event in events if verified_timed(event)), key=lambda event: (
        event['payload']['period'], period_elapsed_seconds(event['payload']), event.get('sequence', 0)
    ))
    blocks = []
    for period in (1, 2):
        for block_index in range(3):
            start_seconds = block_index * 600
            end_seconds = start_seconds + 600
            within = [event for event in timed if event['payload']['period'] == period and start_seconds <= period_elapsed_seconds(event['payload']) < end_seconds]
            home = team_stats([event for event in within if public_side(event['payload']) == 'home'])
            away = team_stats([event for event in within if public_side(event['payload']) == 'away'])
            winner = 'draw' if home['goals'] == away['goals'] else ('home' if home['goals'] > away['goals'] else 'away')
            blocks.append({'period': period, 'start_seconds': start_seconds, 'end_seconds': end_seconds, 'home': home, 'away': away, 'winner': winner})

    def scoring_run_entry(goals, side):
        return {'team_side': side, 'goals': len(goals), 'start': public_clock(goals[0]['payload']), 'end': public_clock(goals[-1]['payload'])}

    scoring_runs = []
    current_side = None
    current_goals = []
    for event in timed:
        payload = event['payload']
        if payload.get('kind') != 'shot' or payload.get('outcome') != 'goal' or public_side(payload) == 'unknown':
            continue
        side = public_side(payload)
        if side != current_side:
            if len(current_goals) >= 2:
                scoring_runs.append(scoring_run_entry(current_goals, current_side))
            current_side, current_goals = side, [event]
        else:
            current_goals.append(event)
    if len(current_goals) >= 2:
        scoring_runs.append(scoring_run_entry(current_goals, current_side))

    quick_concessions = []
    terminals = {'shot', 'turnover'}
    for previous, following in zip(timed, timed[1:]):
        before, after = previous['payload'], following['payload']
        delta = period_elapsed_seconds(after) - period_elapsed_seconds(before)
        if before['period'] != after['period'] or delta < 0 or delta > 10:
            continue
        if before.get('kind') not in terminals or after.get('kind') != 'shot' or after.get('outcome') != 'goal':
            continue
        from_side, scored_side = public_side(before), public_side(after)
        if from_side == 'unknown' or scored_side == 'unknown' or from_side == scored_side:
            continue
        quick_concessions.append({'conceding_side': from_side, 'scoring_side': scored_side, 'seconds_after_terminal': delta, 'terminal_kind': before.get('kind'), 'terminal_outcome': before.get('outcome'), 'at': public_clock(after)})

    def goalkeeper_stats(opponent_events):
        summary = team_stats(opponent_events)
        seven_meters = team_stats([event for event in opponent_events if event['payload'].get('kind') == 'shot' and event['payload'].get('shot_zone') == 7])
        return {
            'opponent_attempts': summary['shots'], 'opponent_on_target': summary['shots_on_target'], 'goals_conceded': summary['goals'], 'saves': summary['saves_against'],
            'seven_meters': {'attempts': seven_meters['shots'], 'on_target': seven_meters['shots_on_target'], 'goals': seven_meters['goals'], 'saves': seven_meters['saves_against']},
        }

    goalkeeper_context = {
        'home': {'total': goalkeeper_stats(away_eligible), 'first_half': goalkeeper_stats([event for event in away_eligible if event['payload'].get('period') == 1]), 'second_half': goalkeeper_stats([event for event in away_eligible if event['payload'].get('period') == 2])},
        'away': {'total': goalkeeper_stats(home_eligible), 'first_half': goalkeeper_stats([event for event in home_eligible if event['payload'].get('period') == 1]), 'second_half': goalkeeper_stats([event for event in home_eligible if event['payload'].get('period') == 2])},
    }
    return {'block_seconds': 600, 'blocks': blocks, 'scoring_runs': scoring_runs, 'quick_concessions': quick_concessions, 'goalkeeper_context': goalkeeper_context}

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

phase_analysis = build_phase_analysis(eligible_events)

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
        'passive': 'Pasivo',
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
        'video_seconds': video_seconds_by_event.get(ev['id']),
    })

# Sort incidents by period and regulation_seconds, then sequence
incidents.sort(key=lambda x: (x['period'] or 0, x['regulation_seconds'] or 0, x['reference']))

package_dict = {
    'match_id': match_id,
    'report_version': 1,
    'schema_version': 'public-report-v1',
    'match': match,
    'home_team': home_team,
    'away_team': away_team,
    'coaching_question': 'Match analysis',
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
    'phase_analysis': phase_analysis,
    'incidents': incidents,
    'video': public_video,
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
    'phase_analysis': phase_analysis,
    'incidents': incidents,
    'video': public_video,
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

# Write the fallback report and the complete catalog artifact set. When the
# catalog directory differs, keep the explicit output path as a compatible copy.
output_path, output_directory = public_output_paths(
    Path(os.getenv('PUBLIC_REPORT_OUTPUT', 'reports/public/report.json')),
    Path(os.environ['PUBLIC_REPORT_CATALOG_OUTPUT']) if os.getenv('PUBLIC_REPORT_CATALOG_OUTPUT') else None,
)
output_directory.mkdir(parents=True, exist_ok=True)
serialized_report = json.dumps(report, ensure_ascii=False, indent=2)
fallback_path = output_directory / 'report.json'
fallback_path.write_text(serialized_report, encoding='utf-8')
if output_path != fallback_path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(serialized_report, encoding='utf-8')

# Store each exported match under a deterministic public key; no database ID
# appears in static filenames or the catalog.
public_path = output_directory / ('report_' + public_report_key(report) + '.json')
if public_path != fallback_path:
    public_path.write_text(serialized_report, encoding='utf-8')
write_public_catalog(output_directory)

print('Report exported to ' + str(output_path))
print('Public fallback report updated: ' + str(fallback_path))
print('Public match report updated: ' + str(public_path))
print('Public report catalog updated: ' + str(output_directory / 'reports.json'))

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
