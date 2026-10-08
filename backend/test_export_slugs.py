import sys
sys.path.insert(0, '/app/app')
sys.path.insert(0, '/app/scripts')
from sqlalchemy.orm import joinedload as jl
from app.database import SessionLocal
from app.models import Match, MatchSquad
from app.services.canonical_analysis_service import read_metrics, read_reconciliation
from unicodedata import normalize
import re

def slugify(name: str) -> str:
    nfkd = normalize('NFKD', name)
    ascii_only = nfkd.encode('ascii', 'ignore').decode('ascii')
    lowered = ascii_only.lower()
    parts = ''.join(char if char.isalnum() or char == ' ' else ' ' for char in lowered).split()
    return '-'.join(parts) or 'unknown'

db = SessionLocal()
match = db.get(Match, 99)
print('Match found:', match is not None)

if match:
    print('Match ID:', match.id, 'Date:', match.date, 'canonical_analysis_enabled:', match.canonical_analysis_enabled)

    metrics_data = read_metrics(db, 99)
    eligibility = metrics_data.get('eligibility', {})
    print('Eligible events:', eligibility.get('eligible', 0))

    recon_data = read_reconciliation(db, 99)
    disc = recon_data.get('discrepancies', [])
    print('Reconciliation discrepancies:', len(disc), 'entries')

    events = metrics_data.get('events', [])
    eligible_events = [e for e in events if e.get('active') and e.get('payload', {}).get('fact_kind') == 'observed'
                       and e.get('payload', {}).get('evidence_state') == 'confirmed']
    print('Eligible events count:', len(eligible_events))

    squad = db.query(MatchSquad).options(jl(MatchSquad.player)).filter_by(match_id=99).all()
    print('Squad players:', len(squad))

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

    players_data = []
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

    print()
    print('=== Players slug validation ===')
    all_valid = True
    for p in players_data:
        slug = p['slug']
        valid = bool(re.match(r'^[a-z0-9-]+$', slug))
        status = 'OK' if valid else 'FAIL'
        if not valid:
            all_valid = False
        print('  ' + status + ': ' + p['name'] + ' -> ' + slug)

    print()
    print('All slugs valid:', all_valid)

db.close()