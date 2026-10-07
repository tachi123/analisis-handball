import json

with open('resources/planillas/_discovery/bootstrap-manifest.json', encoding='utf-8') as f:
    manifest = json.load(f)

stage_map = {'apertura-3m-2026': 'APE_2026_3M', 'permanencia-3m-2026': 'PER_2026_3M'}

def slug(s):
    return s.replace(' ', '_').replace('.', '').replace('(', '').replace(')', '').replace('í', 'i').replace('ó', 'o').replace('á', 'a').replace('é', 'e').replace('ú', 'u')

for alias in manifest['aliases']:
    stage_key = alias['stage_keys'][0]
    stage_prefix = stage_map[stage_key]
    club_slug = slug(alias['club'])
    variant = alias['variant'] or 'MAIN'
    ext_code = f'{stage_prefix}_{club_slug}_{variant}'
    print(f'{alias["source_label"]:50s} -> {ext_code}')