import ast
import json
from pathlib import Path
import subprocess
import sys

import pytest

from app.services.fixture_seeder import validate_fixture
from app.services.planilla_derivation_service import canonical_json, derive_fixtures, sha256_text, suggest_team_mapping


ROOT_DIR = Path(__file__).resolve().parents[2]
MANIFEST = ROOT_DIR / "resources" / "planillas" / "_discovery" / "manifest.json"
IDENTITIES = ROOT_DIR / "resources" / "planillas" / "_discovery" / "identities" / "identity-summary.json"
SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "derive_planilla_fixtures.py"
SERVICE = Path(__file__).resolve().parents[1] / "app" / "services" / "planilla_derivation_service.py"


def field(record, name):
    return record["fields"][name]["value"]


def reviewed_mapping(manifest):
    labels = sorted({field(record, side) for record in manifest["records"] for side in ("home_name", "away_name") if field(record, side)})
    return {"schema_version": 1, "manifest_sha256": sha256_text(canonical_json(manifest)), "labels": {label: {"club": f"Reviewed {number}", "variant": None} for number, label in enumerate(labels, 1)}}


def rules():
    return {"schema_version": 1, "captured_at": "2026-08-26", "round_inference": "ascending_unique_date"}


def test_real_artifact_records_create_seeder_compatible_stages_and_exclude_missing_team():
    corpus = json.loads(MANIFEST.read_text(encoding="utf-8"))
    selected = []
    for stage in ("2026_Apertura_Zona_A _Mayores_3º_División_Masculino", "2026_Torneo_Permanencia_Mayores_3º_División_Masculino"):
        selected.append(next(record for record in corpus["records"] if record["source_path"].startswith(stage) and field(record, "home_name") and field(record, "away_name")))
    missing = {**selected[0], "source_path": "2026_Apertura_Zona_A _Mayores_3º_División_Masculino/synthetic-blank.pdf", "fields": {**selected[0]["fields"], "away_name": {"value": None}}}
    manifest = {"schema_version": 1, "records": selected + [missing]}

    derived, report = derive_fixtures(manifest, reviewed_mapping(manifest), rules())

    assert [fixture["stage"]["name"] for fixture in derived["fixtures"]] == ["Apertura Zona A 2026 3ªM", "Torneo Permanencia 2026 3ªM"]
    assert report["counts"] == {"fixtures_by_stage": {"Apertura Zona A 2026 3ªM": 1, "Torneo Permanencia 2026 3ªM": 1}, "rounds_by_stage": {"Apertura Zona A 2026 3ªM": 1, "Torneo Permanencia 2026 3ªM": 1}, "resolved_by_mapping": 2, "reconciled": 0, "unresolved": 1}
    assert report["unresolved"][0]["source_path"] == missing["source_path"]
    assert all(validate_fixture(fixture) for fixture in derived["fixtures"])


def test_keys_rounds_and_serialization_are_byte_stable_without_guessing_labels():
    records = [{"sha256": "b" * 64, "source_path": "2026_Apertura_Zona_A _Mayores_3º_División_Masculino/b.pdf", "page_count": 1, "rosters": {}, "fields": {name: {"value": value} for name, value in {"home_name": "Home", "away_name": "Away", "home_score": 1, "away_score": 2, "date": "2026-04-12", "time": "19:00", "venue": "Venue", "court": "Court"}.items()}}, {"sha256": "b" * 64, "source_path": "2026_Apertura_Zona_A _Mayores_3º_División_Masculino/a.pdf", "page_count": 1, "rosters": {}, "fields": {name: {"value": value} for name, value in {"home_name": "Unreviewed", "away_name": "Away", "home_score": 3, "away_score": 4, "date": "2026-03-29", "time": "20:00", "venue": "Venue", "court": "Court"}.items()}}]
    manifest = {"schema_version": 1, "records": records}
    mapping = reviewed_mapping(manifest)
    del mapping["labels"]["Unreviewed"]

    first, report = derive_fixtures(manifest, mapping, rules())
    second, _ = derive_fixtures(manifest, mapping, rules())

    assert canonical_json(first).encode() == canonical_json(second).encode()
    assert first["fixtures"][0]["rounds"][0]["entries"][0]["entry_key"] == "planilla:bbbbbbbb:2"
    assert report["unresolved"][0]["reasons"] == ["home_team_unresolved"]


def test_cli_is_model_free_and_rejects_unbound_mapping(tmp_path):
    imports = [node.module or "" for node in ast.walk(ast.parse(SERVICE.read_text(encoding="utf-8"))) if isinstance(node, ast.ImportFrom)]
    assert not any(module.startswith(("app.database", "app.models", "sqlalchemy")) for module in imports)
    manifest = {"schema_version": 1, "records": []}
    for name, value in (("manifest.json", manifest), ("identities.json", {"input": {"source_paths": []}}), ("mapping.json", {"schema_version": 1, "manifest_sha256": "wrong", "labels": {}}), ("rules.json", rules())):
        (tmp_path / name).write_text(json.dumps(value), encoding="utf-8")
    result = subprocess.run([sys.executable, str(SCRIPT), "--manifest", str(tmp_path / "manifest.json"), "--identities", str(tmp_path / "identities.json"), "--mapping", str(tmp_path / "mapping.json"), "--rules", str(tmp_path / "rules.json"), "--output", str(tmp_path / "derived.json"), "--unresolved-output", str(tmp_path / "report.json")], capture_output=True, text=True)
    assert result.returncode == 2
    assert "--bootstrap-report" in result.stderr


def test_suggestions_cover_every_labeled_name_and_preserve_competition_variants():
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    suggestions = suggest_team_mapping(manifest)

    labels = {field(record, side) for record in manifest["records"] for side in ("home_name", "away_name") if field(record, side)}
    assert set(suggestions["labels"]) == labels
    sample = {"records": [{"source_path": "2026_Apertura_Zona_A _Mayores_3º_División_Masculino/sample.pdf", "fields": {"home_name": {"value": "C.S. y C. Deportivo Laferrere B"}}}]}
    assert suggest_team_mapping(sample)["labels"]["C.S. y C. Deportivo Laferrere B"] == {"club": "Deportivo Laferrere", "variant": "B"}
    sample["records"][0]["fields"]["home_name"]["value"] = "C.A. y S. Villa Calzada"
    assert suggest_team_mapping(sample)["labels"]["C.A. y S. Villa Calzada"] == {"club": "Villa Calzada", "variant": None}


def test_schema_v2_mapping_covers_all_136_canonical_labelled_pdfs_without_alias_loss():
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    mapping = json.loads((ROOT_DIR / "resources" / "planillas" / "_discovery" / "team-mapping.json").read_text(encoding="utf-8"))

    derived, report = derive_fixtures(manifest, mapping, rules())

    entries = [entry for fixture in derived["fixtures"] for round_ in fixture["rounds"] for entry in round_["entries"]]
    assert len(entries) == 136
    assert report["counts"]["unresolved"] == 0
    assert {entry["planilla"]["sha256"] for entry in entries} == {record["sha256"] for record in manifest["records"]}
    assert any(entry["home"]["club"] == "Municipalidad de San Martín (Ce.M.E.F)" or entry["away"]["club"] == "Municipalidad de San Martín (Ce.M.E.F)" for entry in entries)


def test_reconciliation_requires_exactly_one_inverted_candidate():
    stage = "2026_Apertura_Zona_A _Mayores_3º_División_Masculino"

    def record(sha, home, away, day, score=(20, 18)):
        values = {"home_name": home, "away_name": away, "home_score": score[0], "away_score": score[1], "date": day, "time": "19:00", "venue": "Venue", "court": "Court"}
        return {"sha256": sha * 64, "source_path": f"{stage}/{sha}.pdf", "page_count": 1, "rosters": {}, "fields": {name: {"value": value} for name, value in values.items()}}

    complete = record("a", "Opposition", "Inferred", "2026-04-01")
    unique_manifest = {"schema_version": 1, "records": [complete, record("b", None, "Opposition", "2026-04-03")]}
    unique, unique_report = derive_fixtures(unique_manifest, reviewed_mapping(unique_manifest), rules())
    unique_entry = next(entry for round_ in unique["fixtures"][0]["rounds"] for entry in round_["entries"] if entry.get("provenance"))
    assert unique_report["counts"]["reconciled"] == 1
    assert unique_entry["home"] == {"club": "Reviewed 2", "variant": None}
    assert unique_entry["provenance"] == "reconciled_from:aaaaaaaa"

    ambiguous_manifest = {"schema_version": 1, "records": [complete, record("c", "Opposition", "Other", "2026-04-02"), record("d", None, "Opposition", "2026-04-03")]}
    _, ambiguous = derive_fixtures(ambiguous_manifest, reviewed_mapping(ambiguous_manifest), rules())
    assert ambiguous["counts"]["reconciled"] == 0
    assert ambiguous["unresolved"][0]["reasons"][-1] == "reconciliation_ambiguous"

    missing_manifest = {"schema_version": 1, "records": [record("e", None, "Other", "2026-05-01")]}
    _, missing = derive_fixtures(missing_manifest, reviewed_mapping(missing_manifest), rules())
    assert missing["unresolved"][0]["reasons"][-1] == "reconciliation_no_candidate"
