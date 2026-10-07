import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import OfficialBatchRun, OfficialSnapshot, ScheduledMatch
from app.services.official_planilla_loader_service import rollback_batch
from app.services.pdf_service import PDFService
from app.services.planilla_derivation_service import canonical_json, sha256_text


ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
DERIVE = BACKEND / "scripts" / "derive_planilla_fixtures.py"
LOAD = BACKEND / "scripts" / "load_planilla_official.py"
SAMPLE = ROOT / "resources" / "planillas" / "planilla_banfield_b_vs_sapa.pdf"
STAGE = "2026_Apertura_Zona_A _Mayores_3º_División_Masculino"


def _copied_inputs(tmp_path):
    corpus = tmp_path / "official_planillas"
    sheet = corpus / STAGE / SAMPLE.name
    sheet.parent.mkdir(parents=True)
    shutil.copy2(SAMPLE, sheet)
    preview = PDFService.preview_femebal_sheet(sheet.read_bytes(), sheet.name, "application/pdf")
    info = preview["match_info"]
    record = {
        "sha256": preview["provenance"]["sha256"], "size": preview["provenance"]["size_bytes"],
        "page_count": preview["provenance"]["page_count"], "mtime": None,
        "source_path": f"{STAGE}/{sheet.name}", "rosters": {},
        "fields": {key: {"value": value} for key, value in {
            "home_name": preview["home_team"]["name"], "away_name": preview["away_team"]["name"],
            "home_score": info["home_score"], "away_score": info["away_score"], "date": info["date"],
            "time": info["time"], "venue": info["venue"], "court": info["court"],
        }.items()},
    }
    manifest = {"schema_version": 1, "records": [record]}
    mapping = {"schema_version": 1, "manifest_sha256": sha256_text(canonical_json(manifest)), "labels": {
        "C.A. Banfield B": {"club": "Banfield", "variant": "B"}, "S.A.P.A.": {"club": "S.A.P.A.", "variant": None},
    }}
    rules = {"schema_version": 1, "captured_at": "2026-08-26", "round_inference": "ascending_unique_date"}
    paths = {name: tmp_path / f"{name}.json" for name in ("manifest", "identities", "mapping", "rules", "derived", "report", "approval")}
    paths["manifest"].write_text(json.dumps(manifest), encoding="utf-8")
    paths["identities"].write_text(json.dumps({"input": {"source_paths": [record["source_path"]]}}), encoding="utf-8")
    paths["mapping"].write_text(json.dumps(mapping), encoding="utf-8")
    paths["rules"].write_text(json.dumps(rules), encoding="utf-8")
    return corpus, paths


def _derive(paths):
    result = subprocess.run([sys.executable, str(DERIVE), "--manifest", str(paths["manifest"]), "--identities", str(paths["identities"]), "--mapping", str(paths["mapping"]), "--rules", str(paths["rules"]), "--output", str(paths["derived"]), "--unresolved-output", str(paths["report"])], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    derived_sha = hashlib.sha256(paths["derived"].read_bytes()).hexdigest()
    paths["approval"].write_text(json.dumps({"manifest_sha256": json.loads(paths["derived"].read_text())["manifest_sha256"], "mapping_sha256": json.loads(paths["derived"].read_text())["mapping_sha256"], "derived_sha256": derived_sha}), encoding="utf-8")


def _load(database, corpus, paths):
    return subprocess.run([sys.executable, str(LOAD), "--database-url", f"sqlite:///{database}", "--manifest", str(paths["manifest"]), "--mapping", str(paths["mapping"]), "--derived", str(paths["derived"]), "--approval", str(paths["approval"]), "--source-root", str(corpus)], capture_output=True, text=True)


def test_cli_refuses_a_single_pdf_before_any_derivation_or_load(tmp_path):
    corpus, paths = _copied_inputs(tmp_path)
    database = tmp_path / "proof.db"; engine = create_engine(f"sqlite:///{database}"); Base.metadata.create_all(engine)
    source_hash = hashlib.sha256(next(corpus.rglob("*.pdf")).read_bytes()).hexdigest()

    result = subprocess.run([sys.executable, str(DERIVE), "--manifest", str(paths["manifest"]), "--identities", str(paths["identities"]), "--mapping", str(paths["mapping"]), "--rules", str(paths["rules"]), "--output", str(paths["derived"]), "--unresolved-output", str(paths["report"])], capture_output=True, text=True)

    assert result.returncode == 2 and "--bootstrap-report" in result.stderr
    assert hashlib.sha256(next(corpus.rglob("*.pdf")).read_bytes()).hexdigest() == source_hash
    with sessionmaker(bind=engine)() as db:
        assert db.query(ScheduledMatch).count() == db.query(OfficialSnapshot).count() == 0


def test_loader_cli_requires_completed_bootstrap_bindings_before_fixture_writes(tmp_path):
    corpus, paths = _copied_inputs(tmp_path)
    database = tmp_path / "proof.db"; engine = create_engine(f"sqlite:///{database}"); Base.metadata.create_all(engine)

    result = subprocess.run([sys.executable, str(LOAD), "--database-url", f"sqlite:///{database}", "--manifest", str(paths["manifest"]), "--mapping", str(paths["mapping"]), "--derived", str(paths["derived"]), "--approval", str(paths["approval"]), "--source-root", str(corpus)], capture_output=True, text=True)

    assert result.returncode == 2 and "--bootstrap-report" in result.stderr
    with sessionmaker(bind=engine)() as db:
        assert db.query(ScheduledMatch).count() == db.query(OfficialSnapshot).count() == 0
