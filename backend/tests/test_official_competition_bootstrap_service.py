import json
from copy import deepcopy
from pathlib import Path
import subprocess
import sys

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.services.official_competition_bootstrap_service import (
    BootstrapEvidenceError,
    BootstrapLifecycleError,
    build_evidence_manifest,
    bootstrap_competition,
    dry_run,
    rehearse_competition,
    rollback_competition,
    sha256,
    validate_approval_evidence,
)
from app.database import Base
from app.models import Club, CompetitionTeam, FixtureImport, Season, TeamRegistration, TournamentStage


ROOT = Path(__file__).resolve().parents[2]
DISCOVERY_PATH = ROOT / "resources" / "planillas" / "_discovery" / "manifest.json"
BOOTSTRAP_PATH = ROOT / "resources" / "planillas" / "_discovery" / "bootstrap-manifest.json"
SCRIPT = ROOT / "backend" / "scripts" / "bootstrap_official_3m_competition.py"


def artifacts():
    return json.loads(DISCOVERY_PATH.read_text(encoding="utf-8")), json.loads(BOOTSTRAP_PATH.read_text(encoding="utf-8"))


def approval_artifacts(discovery, bootstrap):
    evidence = build_evidence_manifest(discovery, bootstrap)
    report = {"schema_version": 1, "bootstrap_manifest_sha256": sha256(bootstrap), "stages": []}
    for stage_number, stage in enumerate(evidence["stages"], start=1):
        targets = {(alias["club"], alias["variant"]) for alias in bootstrap["aliases"] if stage["key"] in alias["stage_keys"]}
        report["stages"].append({"key": stage["key"], "id": stage_number,
                                 "teams": [{"club": club, "variant": variant, "competition_team_id": index + 100 * stage_number}
                                           for index, (club, variant) in enumerate(sorted(targets), start=1)]})
    ids = {stage["key"]: {(team["club"], team["variant"]): team["competition_team_id"] for team in stage["teams"]}
           for stage in report["stages"]}
    mappings = sorted(({"source_label": alias["source_label"], "stage_key": stage_key,
                        "competition_team_id": ids[stage_key][(alias["club"], alias["variant"])]}
                       for alias in bootstrap["aliases"] for stage_key in alias["stage_keys"]),
                      key=lambda item: (item["stage_key"], item["source_label"]))
    mapping = {"schema_version": 1, "bootstrap_manifest_sha256": sha256(bootstrap), "mappings": mappings}
    return {
        "schema_version": 1, "approval_required": True, "status": "approved", "approver": "competition-maintainer",
        "bootstrap_manifest_sha256": sha256(bootstrap), "mapping_sha256": sha256(mapping),
        "reconciliation_report_sha256": sha256(evidence), "bootstrap_report_sha256": sha256(report),
        "stages": [{"key": stage["key"], "id": stage["id"]} for stage in report["stages"]], "mappings": mappings,
    }, mapping, report


def rehash_approval(approval, discovery, bootstrap, report):
    evidence = build_evidence_manifest(discovery, bootstrap)
    ids = {stage["key"]: {(team["club"], team["variant"]): team["competition_team_id"] for team in stage["teams"]}
           for stage in report["stages"]}
    mappings = sorted(({"source_label": alias["source_label"], "stage_key": stage_key,
                        "competition_team_id": ids[stage_key][(alias["club"], alias["variant"])]}
                       for alias in bootstrap["aliases"] for stage_key in alias["stage_keys"]),
                      key=lambda item: (item["stage_key"], item["source_label"]))
    mapping = {"schema_version": 1, "bootstrap_manifest_sha256": sha256(bootstrap), "mappings": mappings}
    approval.update({
        "mapping_sha256": sha256(mapping),
        "reconciliation_report_sha256": sha256(evidence),
        "bootstrap_report_sha256": sha256(report),
        "stages": [{"key": stage["key"], "id": stage["id"]} for stage in report["stages"]],
        "mappings": mappings,
    })
    return mapping


def test_real_corpus_builds_byte_stable_hash_bound_evidence_for_every_source():
    discovery, bootstrap = artifacts()

    first = build_evidence_manifest(discovery, bootstrap)
    second = build_evidence_manifest(discovery, bootstrap)

    assert sha256(first) == sha256(second)
    assert first["canonical_pdf_count"] == 136
    assert first["source_path_count"] == 138
    assert [stage["key"] for stage in first["stages"]] == ["apertura-3m-2026", "permanencia-3m-2026"]
    fixtures = [fixture for stage in first["stages"] for fixture in stage["fixtures"]]
    assert len(fixtures) == 136
    assert sum(1 + len(fixture["source_aliases"]) for fixture in fixtures) == 138
    assert len({fixture["sha256"] for fixture in fixtures}) == 136
    assert all(len(fixture["sha256"]) == 64 for fixture in fixtures)


def test_real_manifest_preserves_all_recovered_labels_and_variants_without_fuzzy_aliases():
    discovery, bootstrap = artifacts()
    evidence = build_evidence_manifest(discovery, bootstrap)

    recovered = {label for stage in evidence["stages"] for fixture in stage["fixtures"] for label in fixture["labels"]}
    aliases = {item["source_label"]: item for item in bootstrap["aliases"]}
    assert recovered == set(aliases)
    assert aliases["A.A. Argentinos Juniors D"]["club"] == "Argentinos Juniors"
    assert aliases["Argentinos Juniors D"]["variant"] == "D"
    assert aliases["Municipalidad de Tres de Febrero B"]["variant"] == "B"
    assert aliases["Municipalidad de Vicente López C"]["variant"] == "C"
    assert aliases["S.A.G. Polvorines D"]["variant"] == "D"
    assert aliases["Municipalidad de San Martín (Ce.M.E.F)"]["club"] == "Municipalidad de San Martín (Ce.M.E.F)"
    assert "Municipalidad de San Martín" not in aliases


def test_rejects_cross_stage_reuse_and_unapproved_fuzzy_association():
    discovery, bootstrap = artifacts()
    wrong_stage = deepcopy(bootstrap)
    alias = next(item for item in wrong_stage["aliases"] if item["source_label"] == "Municipalidad de Avellaneda")
    alias["stage_keys"] = ["permanencia-3m-2026"]
    with pytest.raises(BootstrapEvidenceError, match="exactly cover observed labels"):
        build_evidence_manifest(discovery, wrong_stage)

    fuzzy = deepcopy(bootstrap)
    fuzzy["aliases"].append({"source_label": "Municipalidad de San Martín", "club": "Municipalidad de San Martín (Ce.M.E.F)", "variant": None, "stage_keys": ["permanencia-3m-2026"]})
    with pytest.raises(BootstrapEvidenceError, match="exactly cover observed labels"):
        build_evidence_manifest(discovery, fuzzy)


def test_rejects_stale_or_wrong_approval_evidence_and_dry_run_cannot_load():
    discovery, bootstrap = artifacts()
    plan = dry_run(bootstrap, discovery)
    approval, mapping, report = approval_artifacts(discovery, bootstrap)

    assert plan["mode"] == "dry-run"
    assert plan["approval_required"] is True
    assert validate_approval_evidence(bootstrap, discovery, mapping, report, approval) == plan["evidence"]

    stale = {**approval, "reconciliation_report_sha256": "0" * 64}
    with pytest.raises(BootstrapEvidenceError, match="hashes do not match"):
        validate_approval_evidence(bootstrap, discovery, mapping, report, stale)
    wrong = {**approval, "stages": approval["stages"][:-1]}
    with pytest.raises(BootstrapEvidenceError, match="target stages"):
        validate_approval_evidence(bootstrap, discovery, mapping, report, wrong)
    pending = {**approval, "status": "pending"}
    with pytest.raises(BootstrapEvidenceError, match="explicitly approved"):
        validate_approval_evidence(bootstrap, discovery, mapping, report, pending)


@pytest.mark.parametrize("field", [
    "schema_version", "approval_required", "approver", "bootstrap_manifest_sha256", "mapping_sha256",
    "reconciliation_report_sha256", "bootstrap_report_sha256", "stages", "mappings",
])
def test_rejects_each_missing_approval_binding(field):
    discovery, bootstrap = artifacts()
    approval, mapping, report = approval_artifacts(discovery, bootstrap)
    approval.pop(field)

    with pytest.raises(BootstrapEvidenceError):
        validate_approval_evidence(bootstrap, discovery, mapping, report, approval)


@pytest.mark.parametrize("field, value", [
    ("schema_version", 2), ("approval_required", False), ("approver", " "),
    ("bootstrap_manifest_sha256", "0" * 64), ("mapping_sha256", "0" * 64),
    ("reconciliation_report_sha256", "0" * 64), ("bootstrap_report_sha256", "0" * 64),
    ("stages", []), ("mappings", []),
])
def test_rejects_each_wrong_or_partial_approval_binding(field, value):
    discovery, bootstrap = artifacts()
    approval, mapping, report = approval_artifacts(discovery, bootstrap)
    approval[field] = value

    with pytest.raises(BootstrapEvidenceError):
        validate_approval_evidence(bootstrap, discovery, mapping, report, approval)


def test_rejects_changed_stage_or_competition_team_identity_and_widened_mapping():
    discovery, bootstrap = artifacts()
    approval, mapping, report = approval_artifacts(discovery, bootstrap)
    report["stages"][0]["id"] += 2
    with pytest.raises(BootstrapEvidenceError, match="hashes"):
        validate_approval_evidence(bootstrap, discovery, mapping, report, approval)

    approval, mapping, report = approval_artifacts(discovery, bootstrap)
    report["stages"][0]["teams"][0]["competition_team_id"] += 50
    with pytest.raises(BootstrapEvidenceError, match="target CompetitionTeam IDs"):
        validate_approval_evidence(bootstrap, discovery, mapping, report, approval)

    approval, mapping, report = approval_artifacts(discovery, bootstrap)
    mapping["mappings"][0]["competition_team_id"] += 1
    with pytest.raises(BootstrapEvidenceError, match="exactly cover"):
        validate_approval_evidence(bootstrap, discovery, mapping, report, approval)

    approval, mapping, report = approval_artifacts(discovery, bootstrap)
    mapping["mappings"].append({"source_label": "Unapproved", "stage_key": "apertura-3m-2026", "competition_team_id": 101})
    with pytest.raises(BootstrapEvidenceError, match="exactly cover"):
        validate_approval_evidence(bootstrap, discovery, mapping, report, approval)

    approval, mapping, report = approval_artifacts(discovery, bootstrap)
    approval["mappings"] = [*approval["mappings"], {"source_label": "Unapproved", "stage_key": "apertura-3m-2026", "competition_team_id": 101}]
    with pytest.raises(BootstrapEvidenceError, match="approval mappings"):
        validate_approval_evidence(bootstrap, discovery, mapping, report, approval)


def test_rejects_fully_rehashed_approval_with_duplicate_target_stage_ids():
    discovery, bootstrap = artifacts()
    approval, _, report = approval_artifacts(discovery, bootstrap)
    report["stages"][1]["id"] = report["stages"][0]["id"]
    mapping = rehash_approval(approval, discovery, bootstrap, report)

    with pytest.raises(BootstrapEvidenceError, match="distinct positive target-stage IDs"):
        validate_approval_evidence(bootstrap, discovery, mapping, report, approval)


def test_rejects_fully_rehashed_approval_with_reused_competition_team_id():
    discovery, bootstrap = artifacts()
    approval, _, report = approval_artifacts(discovery, bootstrap)
    report["stages"][1]["teams"][0]["competition_team_id"] = report["stages"][0]["teams"][0]["competition_team_id"]
    mapping = rehash_approval(approval, discovery, bootstrap, report)

    with pytest.raises(BootstrapEvidenceError, match="must not reuse CompetitionTeam IDs"):
        validate_approval_evidence(bootstrap, discovery, mapping, report, approval)


def test_rejects_fully_rehashed_approval_with_same_stage_reused_competition_team_id():
    discovery, bootstrap = artifacts()
    approval, _, report = approval_artifacts(discovery, bootstrap)
    report["stages"][0]["teams"][1]["competition_team_id"] = report["stages"][0]["teams"][0]["competition_team_id"]
    mapping = rehash_approval(approval, discovery, bootstrap, report)

    with pytest.raises(BootstrapEvidenceError, match="must not reuse CompetitionTeam IDs"):
        validate_approval_evidence(bootstrap, discovery, mapping, report, approval)


def test_rejects_discovery_sha_or_source_count_changes_before_approval():
    discovery, bootstrap = artifacts()
    changed = deepcopy(discovery)
    changed["records"] = changed["records"][:-1]

    with pytest.raises(BootstrapEvidenceError, match="not bound"):
        build_evidence_manifest(changed, bootstrap)


def lifecycle_approval(bootstrap, report):
    mappings = sorted((
        {"source_label": alias["source_label"], "stage_key": stage_key,
         "competition_team_id": next(team["competition_team_id"] for stage in report["stages"] if stage["key"] == stage_key for team in stage["teams"] if (team["club"], team["variant"]) == (alias["club"], alias["variant"]))}
        for alias in bootstrap["aliases"] for stage_key in alias["stage_keys"]
    ), key=lambda item: (item["stage_key"], item["source_label"]))
    mapping = {"schema_version": 1, "bootstrap_manifest_sha256": sha256(bootstrap), "mappings": mappings}
    return {"schema_version": 1, "approval_required": True, "status": "approved", "approver": "maintainer",
            "bootstrap_manifest_sha256": sha256(bootstrap), "bootstrap_report_sha256": sha256(report),
            "mapping_sha256": sha256(mapping),
            "stages": [{"key": stage["key"], "id": stage["id"]} for stage in report["stages"]], "mappings": mappings}


def lifecycle_inputs(session, bootstrap):
    discovery, _ = artifacts()
    reconciliation = build_evidence_manifest(discovery, bootstrap)
    report = rehearse_competition(session, bootstrap)
    approval = lifecycle_approval(bootstrap, report)
    mapping = {"schema_version": 1, "bootstrap_manifest_sha256": sha256(bootstrap), "mappings": approval["mappings"]}
    approval["reconciliation_report_sha256"] = sha256(reconciliation)
    return discovery, mapping, reconciliation, report, approval


def test_lifecycle_is_idempotent_stage_local_and_preserves_existing_fourth_division(session):
    _, bootstrap = artifacts()
    season = Season(year=2026)
    fourth = TournamentStage(season=season, name="4ª Permanencia", category="Mayores", division="4ª División", gender="Masculino")
    legacy_club = Club(name="Argentinos Juniors")
    session.add_all([season, fourth, legacy_club]); session.flush()
    legacy = CompetitionTeam(club=legacy_club, stage=fourth, suffix="D", variant_key="D")
    session.add(legacy); session.flush()
    discovery, mapping, reconciliation, report, approval = lifecycle_inputs(session, bootstrap)

    first = bootstrap_competition(session, bootstrap, discovery, mapping, reconciliation, report, approval)
    second = bootstrap_competition(session, bootstrap, discovery, mapping, reconciliation, report, approval)

    assert first == second
    assert {stage["key"] for stage in first["stages"]} == {"apertura-3m-2026", "permanencia-3m-2026"}
    teams = [team["competition_team_id"] for stage in first["stages"] for team in stage["teams"]]
    assert len(teams) == len(set(teams))
    assert session.get(CompetitionTeam, legacy.id).stage_id == fourth.id
    assert session.query(FixtureImport).filter_by(source_label="official-3m-bootstrap:v1").count() == 2


@pytest.mark.parametrize("tamper", ["manifest", "mapping", "reconciliation", "report"])
def test_lifecycle_rejects_stale_raw_evidence_before_flush_or_write(session, tamper):
    _, bootstrap = artifacts()
    discovery, mapping, reconciliation, report, approval = lifecycle_inputs(session, bootstrap)
    values = {"bootstrap": bootstrap, "discovery": discovery, "mapping": mapping, "reconciliation": reconciliation, "report": report}
    if tamper == "manifest":
        values["bootstrap"] = {**bootstrap, "discovery_manifest_sha256": "0" * 64}
    elif tamper == "mapping":
        values["mapping"] = {**mapping, "mappings": mapping["mappings"][:-1]}
    elif tamper == "reconciliation":
        values["reconciliation"] = {**reconciliation, "canonical_pdf_count": 0}
    else:
        values["report"] = {**report, "stages": report["stages"][:-1]}
    flushes = []
    event.listen(session, "before_flush", lambda *_: flushes.append(True))

    with pytest.raises((BootstrapEvidenceError, BootstrapLifecycleError)):
        bootstrap_competition(session, values["bootstrap"], values["discovery"], values["mapping"], values["reconciliation"], values["report"], approval)

    assert flushes == []
    assert session.query(TournamentStage).count() == 0
    assert session.query(Club).count() == 0


def test_lifecycle_dry_rehearsal_and_rollback_remove_only_owned_rows(session):
    _, bootstrap = artifacts()
    discovery, mapping, reconciliation, report, approval = lifecycle_inputs(session, bootstrap)
    assert session.query(Season).count() == 0
    bootstrap_competition(session, bootstrap, discovery, mapping, reconciliation, report, approval)
    audit = session.query(FixtureImport).filter_by(source_label="official-3m-bootstrap:v1").first()

    rollback_competition(session, audit.id, approval)

    assert session.query(TournamentStage).count() == 0
    assert session.query(CompetitionTeam).count() == 0
    assert session.query(TeamRegistration).count() == 0
    assert session.query(FixtureImport).count() == 0


def test_dry_run_cli_does_not_write_report(tmp_path):
    discovery, bootstrap = artifacts()
    database = tmp_path / "dry-run.db"
    Base.metadata.create_all(create_engine(f"sqlite:///{database}"))
    approval, mapping, report = approval_artifacts(discovery, bootstrap)
    reconciliation = build_evidence_manifest(discovery, bootstrap)
    files = {"manifest.json": bootstrap, "discovery.json": discovery, "mapping.json": mapping, "reconciliation.json": reconciliation, "bootstrap-report.json": report, "approval.json": approval}
    for name, value in files.items():
        (tmp_path / name).write_text(json.dumps(value), encoding="utf-8")
    output = tmp_path / "must-not-exist.json"
    result = subprocess.run([sys.executable, str(SCRIPT), "--database-url", f"sqlite:///{database}", "--manifest", str(tmp_path / "manifest.json"), "--discovery", str(tmp_path / "discovery.json"), "--mapping", str(tmp_path / "mapping.json"), "--reconciliation", str(tmp_path / "reconciliation.json"), "--bootstrap-report", str(tmp_path / "bootstrap-report.json"), "--approval", str(tmp_path / "approval.json"), "--report", str(output), "--dry-run"], capture_output=True, text=True)

    assert result.returncode == 0, result.stderr
    assert not output.exists()
    assert '"stages"' in result.stdout
    with sessionmaker(bind=create_engine(f"sqlite:///{database}"))() as db:
        assert db.query(TournamentStage).count() == 0


def test_lifecycle_runs_against_migrated_sqlite_schema(migrated_db):
    _, bootstrap = artifacts()
    with sessionmaker(bind=migrated_db)() as db:
        discovery, mapping, reconciliation, report, approval = lifecycle_inputs(db, bootstrap)
        result = bootstrap_competition(db, bootstrap, discovery, mapping, reconciliation, report, approval)

        assert result == report
        assert db.query(TournamentStage).count() == 2
