import json

with open('resources/planillas/_discovery/bootstrap-report.json', encoding='utf-8') as f:
    report = json.load(f)

with open('resources/planillas/_discovery/bootstrap-approval.json', encoding='utf-8') as f:
    approval = json.load(f)

print('Report stages:')
for s in report['stages']:
    print(f'  {s["key"]}: {s["id"]}')

print('Approval stages:')
for s in approval['stages']:
    print(f'  {s["key"]}: {s["id"]}')