import json

with open('resources/planillas/_discovery/bootstrap-manifest.json', encoding='utf-8') as f:
    manifest = json.load(f)

stage_map = {'apertura-3m-2026': 'APE_2026_3M', 'permanencia-3m-2026': 'PER_2026_3M'}

def slug(s):
    return s.replace(' ', '_').replace('.', '').replace('(', '').replace(')', '').replace('í', 'i').replace('ó', 'o').replace('á', 'a').replace('é', 'e').replace('ú', 'u')

# Regenerate external_code for each (club, variant, stage_key) combination correctly
for alias in manifest['aliases']:
    # Remove old external_code if present
    if 'external_code' in alias:
        del alias['external_code']
    # Generate per stage_key
    for stage_key in alias['stage_keys']:
        stage_prefix = stage_map[stage_key]
        club_slug = slug(alias['club'])
        variant = alias['variant'] or 'MAIN'
        ext_code = f'{stage_prefix}_{club_slug}_{variant}'
        # Store in a new structure or overwrite for single stage
        # We'll store a mapping of stage_key -> external_code
        if 'external_codes' not in alias:
            alias['external_codes'] = {}
        alias['external_codes'][stage_key] = ext_code

with open('resources/planillas/_discovery/bootstrap-manifest.json', 'w', encoding='utf-8') as f:
    json.dump(manifest, f, ensure_ascii=False, indent=2, sort_keys=True)

print('Regenerated manifest with per-stage external_codes')
# Verify
for alias in manifest['aliases']:
    for stage_key, ext in alias['external_codes'].items():
        print(f'{alias["source_label"]:50s} [{stage_key}] -> {ext}')