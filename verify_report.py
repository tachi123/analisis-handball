import json
data = json.load(open("reports/public/report_match99.json"))
refs = [e.get("reference", "") for e in data.get("evidence", [])]
print("Has canonical references:", any("canonical:" in r for r in refs))
print("Reference sample:", refs[:3])
print("Evidence keys:", list(data["evidence"][0].keys()) if data["evidence"] else "no evidence")
print("Total evidence items:", len(data.get("evidence", [])))