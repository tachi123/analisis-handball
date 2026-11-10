import re

path = r"J:\Documents\Repositorios\analisis-handball\frontend\src\api\client.ts"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

new_section = """// ─── Standings ────────────────────────────────────────────────────────────────
export const getStandings = (stageId: number) =>
  http.get<StandingsResponse>(/api/v1/standings?stage_id=${stageId}).then(r => r.data)

"""

# Insert after confirmFixtureReview line
marker = 'export const confirmFixtureReview = (fixtureKey: string, confirmation: FixtureConfirmation) =>'
if marker in content:
    # Replace that line with the marker followed by our new section (using positional replace)
    content = content.replace(marker, marker + "\n" + new_section, 1)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("Patched successfully")
else:
    print("Marker not found in file")