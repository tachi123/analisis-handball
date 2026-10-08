import json
d = json.load(open('reports/dist/report.json'))

print('=== MATCH 99 REPORT - FACTUAL CONTENTS ===')
print()

print('MATCH INFO:')
print('  date:', d['match']['date'])
print('  home_team:', d['match']['home_team'])
print('  away_team:', d['match']['away_team'])
print()

print('COVERAGE:')
cov = d.get('coverage')
if cov:
    print('  status:', cov.get('status'))
    print('  analyzed_periods:', cov.get('analyzed_periods'))
    print('  label:', cov.get('label'))
else:
    print('  (none)')
print()

print('EVIDENCE:')
ev = d.get('evidence', [])
print('  total items:', len(ev))
print('  all have reference:', all('reference' in e for e in ev))
print('  references (first 5):', [e.get('reference') for e in ev[:5]])
print('  periods (unique):', sorted(set(e.get('period') for e in ev)))
print('  regulation_seconds (first 3):', [e.get('regulation_seconds') for e in ev[:3]])
print('  clock_unverified (first 3):', [e.get('clock_unverified') for e in ev[:3]])
print('  observation (first 3):', [e.get('observation') for e in ev[:3]])
print('  media_available (first 3):', [e.get('media_available') for e in ev[:3]])
print()

print('PLAYERS:')
players = d.get('players')
if players:
    print('  total count:', len(players))
    roles = {}
    for p in players:
        role = p.get('role', 'unknown')
        roles[role] = roles.get(role, 0) + 1
    print('  roles:', roles)
    for p in players[:5]:
        print('   -', p.get('name'), '| role:', p.get('role'), '| team_side:', p.get('team_side'), '| jersey:', p.get('jersey_number'))
    print('  all player slugs:', [p.get('slug') for p in players])
else:
    print('  (none)')
print()

print('METRICS:')
metrics = d.get('metrics', {})
print('  total metric names:', len(metrics))
print('  metric names:', list(metrics.keys())[:10], '...')
for name, value in list(metrics.items())[:5]:
    print('   -', name + ':', value)
print()

print('SOURCE:')
print('  label:', d.get('source', {}).get('label'))
print('  status:', d.get('source', {}).get('status'))
print()

recon = d.get('reconciliation')
if recon is not None:
    print('  reconciliation count:', len(recon))
else:
    print('  reconciliation: none')
print()

print('UNCERTAINTY DISCLOSURE:', d.get('uncertainty_disclosure'))
print('SCHEMA VERSION:', d.get('schema_version'))
print('REPORT VERSION:', d.get('report_version'))