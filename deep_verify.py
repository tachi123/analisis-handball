import json
data = json.load(open("reports/public/report_match99.json"))

# Check for any database IDs or raw private payloads
print("=== Check for database IDs / raw private payloads ===")

# Check evidence fields
for i, e in enumerate(data.get("evidence", [])):
    for key in e.keys():
        if key in ("reference", "id", "analysis_event_id", "package_id"):
            print(f"  Evidence item {i} has restricted key: {key} = {e[key]}")

# Check players for raw IDs
for i, p in enumerate(data.get("players", [])):
    if "slug" in p and p["slug"].startswith("player-") or p["slug"].startswith("gk-"):
        # This is expected - slugs are derived from names
        pass
    if "name" in p:
        print(f"  Player {i}: {p['name']}, slug: {p.get('slug')}, team_side: {p.get('team_side')}, role: {p.get('role')}")

# Check metrics for any private data
for name, value in data.get("metrics", {}).items():
    print(f"  Metric {name}: count={value.get('count')}, numerator={value.get('numerator')}, denominator={value.get('denominator')}")

# Check coverage
cov = data.get("coverage", {})
print(f"Coverage: status={cov.get('status')}, label={cov.get('label')}")

# Check summary info
print(f"\nMatch: {data.get('match', {})}")
print(f"Source: {data.get('source', {})}")
print(f"Uncertainty: {data.get('uncertainty_disclosure')}")

# Check no raw DB IDs leaked
all_keys = set()
for e in data.get("evidence", []):
    all_keys.update(e.keys())
for p in data.get("players", []):
    all_keys.update(p.keys())
for k in data.get("metrics", {}).keys():
    all_keys.add(k)

restricted = ["id", "event_id", "analysis_event_id", "report_package_id", "revision"]
found_restricted = [k for k in restricted if k in all_keys]
if found_restricted:
    print(f"WARNING: Restricted keys found in output: {found_restricted}")
else:
    print("\nNo restricted database IDs leaked to public JSON")

print(f"\nTotal evidence: {len(data.get('evidence', []))}")
print(f"Total players: {len(data.get('players', []))}")