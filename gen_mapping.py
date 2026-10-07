import json, hashlib
from collections import Counter

with open('resources/planillas/_discovery/bootstrap-manifest.json', encoding='utf-8') as f:
    bootstrap = json.load(f)

mappings = []
for alias in bootstrap['aliases']:
    for stage_key in alias['stage_keys']:
        ext_code = alias['external_codes'][stage_key]
        mappings.append({
            'source_label': alias['source_label'],
            'stage_key': stage_key,
            'external_code': ext_code
        })

mappings.sort(key=lambda x: (x['stage_key'], x['source_label']))

mapping = {
    'schema_version': 2,
    'bootstrap_manifest_sha256': hashlib.sha256(json.dumps(bootstrap, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')).hexdigest(),
    'mappings': mappings
}

with open('resources/planillas/_discovery/bootstrap-mapping.json', 'w', encoding='utf-8') as f:
    json.dump(mapping, f, ensure_ascii=False, indent=2, sort_keys=True)

print('Created bootstrap-mapping.json')
codes = [m['external_code'] for m in mappings]
dups = {c: n for c, n in Counter(codes).items() if n > 1}
print('Duplicates:', dups if dups else 'none')