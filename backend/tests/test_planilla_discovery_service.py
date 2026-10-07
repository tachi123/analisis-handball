import ast
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from app.services.planilla_discovery_service import (
    build_manifest,
    discover_pdf_paths,
    scan_planillas,
    sha256_file,
    write_browsable_index,
    write_manifest_artifacts,
)
from app.services.pdf_service import PDFService
from app.services.pdf_sheet_text_parser import parse_femebal_sheet


PLANILLAS_DIR = Path(__file__).resolve().parents[2] / "resources" / "planillas"
SAMPLE_SHEET = PLANILLAS_DIR / "planilla_banfield_b_vs_sapa.pdf"
SECOND_SHEET = next(PLANILLAS_DIR.rglob("f0c3941767714bf6.pdf"))


def copy_corpus_sheet(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(source.read_bytes())


def test_discover_pdf_paths_recurses_case_insensitively_in_stable_order(tmp_path):
    copy_corpus_sheet(SAMPLE_SHEET, tmp_path / "Zeta.PDF")
    copy_corpus_sheet(SECOND_SHEET, tmp_path / "nested" / "alpha.pdf")
    (tmp_path / "nested" / "ignored.txt").write_text("not a PDF", encoding="utf-8")

    paths = discover_pdf_paths(tmp_path)

    assert [path.relative_to(tmp_path).as_posix() for path in paths] == ["nested/alpha.pdf", "Zeta.PDF"]


def test_scan_canonicalizes_real_corpus_copies_and_preserves_source_bytes(tmp_path):
    canonical = tmp_path / "Alpha.pdf"
    alias = tmp_path / "nested" / "alpha-copy.PDF"
    other = tmp_path / "Beta.pdf"
    copy_corpus_sheet(SAMPLE_SHEET, canonical)
    copy_corpus_sheet(SAMPLE_SHEET, alias)
    copy_corpus_sheet(SECOND_SHEET, other)
    source_hashes = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in (canonical, alias, other)}

    records = scan_planillas(tmp_path, PDFService.parse_femebal_sheet)

    assert [(record["source_path"], record["duplicate_aliases"]) for record in records if record["duplicate_aliases"]] == [
        ("Alpha.pdf", ["nested/alpha-copy.PDF"])
    ]
    assert [record["sha256"] for record in records] == sorted(record["sha256"] for record in records)
    assert all(record["parsed"] is not None for record in records)
    assert {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in source_hashes} == source_hashes


def test_scan_continues_after_a_canonical_parser_error(tmp_path):
    copy_corpus_sheet(SAMPLE_SHEET, tmp_path / "broken.pdf")
    copy_corpus_sheet(SECOND_SHEET, tmp_path / "valid.pdf")

    def parse_sheet(path: Path) -> dict:
        if path.name == "broken.pdf":
            raise ValueError("unreadable planilla")
        return {"filename": path.name}

    records = scan_planillas(tmp_path, parse_sheet)
    by_path = {record["source_path"]: record for record in records}

    assert by_path["broken.pdf"]["parse_error"] == "unreadable planilla"
    assert by_path["broken.pdf"]["parsed"] is None
    assert by_path["valid.pdf"] == {
        "sha256": sha256_file(tmp_path / "valid.pdf"),
        "source_path": "valid.pdf",
        "duplicate_aliases": [],
        "parsed": {"filename": "valid.pdf"},
        "parse_error": None,
        "page_count": 1,
    }


def test_discovery_service_has_no_database_or_model_dependency():
    source = Path(__file__).resolve().parents[1] / "app" / "services" / "planilla_discovery_service.py"
    imports = [node.module or "" for node in ast.walk(ast.parse(source.read_text(encoding="utf-8"))) if isinstance(node, ast.ImportFrom)]

    assert not any(module.startswith(("app.database", "app.models", "sqlalchemy")) for module in imports)


def test_cli_import_does_not_load_database_models_or_sqlalchemy():
    script = Path(__file__).resolve().parents[1] / "scripts" / "discover_planillas.py"
    code = f"""
import importlib.util
import sys
spec = importlib.util.spec_from_file_location("discover_planillas_import_guard", {str(script)!r})
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
blocked = [name for name in sys.modules if name == "app.database" or name.startswith("app.models") or name.startswith("sqlalchemy")]
raise SystemExit(f"unexpected imports: {{blocked}}" if blocked else 0)
"""

    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)

    assert result.returncode == 0, result.stderr


def test_pure_discovery_parser_preserves_existing_manifest_bytes(tmp_path):
    copy_corpus_sheet(SAMPLE_SHEET, tmp_path / "sample.pdf")

    existing = build_manifest(scan_planillas(tmp_path, PDFService.parse_femebal_sheet))
    pure = build_manifest(scan_planillas(tmp_path, parse_femebal_sheet))
    existing_paths = write_manifest_artifacts(existing, tmp_path / "existing")
    pure_paths = write_manifest_artifacts(pure, tmp_path / "pure")

    assert [path.read_bytes() for path in pure_paths] == [path.read_bytes() for path in existing_paths]


def test_manifest_writers_are_byte_stable_and_list_duplicate_copies(tmp_path):
    copy_corpus_sheet(SAMPLE_SHEET, tmp_path / "Alpha.pdf")
    copy_corpus_sheet(SAMPLE_SHEET, tmp_path / "nested" / "alpha-copy.pdf")
    manifest = build_manifest(scan_planillas(tmp_path, PDFService.parse_femebal_sheet))

    first_paths = write_manifest_artifacts(manifest, tmp_path / "first")
    second_paths = write_manifest_artifacts(manifest, tmp_path / "second")

    assert [path.read_bytes() for path in first_paths] == [path.read_bytes() for path in second_paths]
    record = manifest["records"][0]
    assert record["duplicate_aliases"] == ["nested/alpha-copy.pdf"]
    assert "duplicate" in record["quality_flags"]
    csv_row = next(__import__("csv").DictReader(first_paths[1].open(encoding="utf-8")))
    assert json.loads(csv_row["duplicate_aliases_json"]) == ["nested/alpha-copy.pdf"]


@pytest.mark.parametrize(("filename", "home", "away", "score"), (
    ("6f168c0ec9b85fe2.pdf", "C.A. Banfield B", "C.S. y D. Defensores de Banfield", (30, 20)),
    ("b864a52aab3bfaba.pdf", "C.S. y D. Defensores de Banfield", "C.A. Defensores de Moreno", (27, 22)),
    ("ba02911b82ccf22d.pdf", "S.A.P.A.", "C.A. Defensores de Moreno", (32, 34)),
    ("2f3b3adfa6080a74.pdf", "C.A. y S. Villa Calzada", "A.A. Argentinos Juniors D", (26, 23)),
    ("a1f001feaf543c73.pdf", "A.A.C.F. Quilmes C", "C.S. y C. Deportivo Laferrere", (39, 44)),
    ("df5dca93a384e19f.pdf", "C.S. y D. Defensores de Banfield", "C.A. y S. Villa Calzada", (20, 30)),
))
def test_positioned_header_recovery_resolves_formerly_unlabelled_official_sheets(filename, home, away, score):
    parsed = parse_femebal_sheet(next(PLANILLAS_DIR.rglob(filename)))

    assert (parsed["home_team"]["name"], parsed["away_team"]["name"]) == (home, away)
    assert (parsed["match_info"]["home_score"], parsed["match_info"]["away_score"]) == score


def test_browsable_index_is_deterministic_and_does_not_mutate_originals(tmp_path):
    canonical = tmp_path / "source" / "original.pdf"
    duplicate = tmp_path / "source" / "nested" / "duplicate.pdf"
    copy_corpus_sheet(SAMPLE_SHEET, canonical)
    copy_corpus_sheet(SAMPLE_SHEET, duplicate)
    source_hashes = {path: sha256_file(path) for path in (canonical, duplicate)}
    manifest = build_manifest(scan_planillas(tmp_path / "source", parse_femebal_sheet))

    first = write_browsable_index(manifest, tmp_path / "source", tmp_path / "indexed")
    first_bytes = first.read_bytes()
    second = write_browsable_index(manifest, tmp_path / "source", tmp_path / "indexed")
    index = json.loads(second.read_text(encoding="utf-8"))

    assert first_bytes == second.read_bytes()
    assert len(index["entries"]) == 1
    entry = index["entries"][0]
    assert entry["alias"].endswith(f"__{entry['sha256'][:8]}.pdf")
    assert entry["source_aliases"] == ["nested/duplicate.pdf", "original.pdf"]
    assert sha256_file(tmp_path / "indexed" / entry["alias"]) == entry["sha256"]
    assert {path: sha256_file(path) for path in source_hashes} == source_hashes


def test_quality_report_lists_real_missing_court_fixture_in_stable_path_order(tmp_path):
    sheet = next(PLANILLAS_DIR.rglob("835c72c27d759de9.pdf"))
    another_sheet = next(PLANILLAS_DIR.rglob("22cc05f8cf53e235.pdf"))
    copy_corpus_sheet(sheet, tmp_path / "zeta.pdf")
    copy_corpus_sheet(another_sheet, tmp_path / "alpha.pdf")
    manifest = build_manifest(scan_planillas(tmp_path, PDFService.parse_femebal_sheet))

    report = write_manifest_artifacts(manifest, tmp_path / "output")[2].read_text(encoding="utf-8")

    assert "missing-court" in manifest["records"][0]["quality_flags"]
    assert report.index("- alpha.pdf") < report.index("- zeta.pdf")


def test_cli_writes_only_named_artifacts_and_returns_clear_exit_codes(tmp_path):
    source = tmp_path / "source"
    copy_corpus_sheet(SAMPLE_SHEET, source / "sample.pdf")
    output = tmp_path / "output"
    script = Path(__file__).resolve().parents[1] / "scripts" / "discover_planillas.py"

    result = subprocess.run([sys.executable, str(script), str(source), str(output)], capture_output=True, text=True)

    assert result.returncode == 0
    assert set(path.name for path in output.iterdir()) == {"manifest.json", "manifest.csv", "report.md"}
    assert "manifest.json" in result.stdout
    invalid = subprocess.run([sys.executable, str(script), str(tmp_path / "missing"), str(output)], capture_output=True, text=True)
    assert invalid.returncode == 2
    assert "source directory does not exist" in invalid.stderr
    blocked_output = tmp_path / "blocked-output"
    blocked_output.write_text("not a directory", encoding="utf-8")
    failed = subprocess.run([sys.executable, str(script), str(source), str(blocked_output)], capture_output=True, text=True)
    assert failed.returncode == 1
    assert "discovery failed" in failed.stderr


@pytest.mark.corpus
def test_cli_discovers_the_real_corpus_read_only_and_byte_stably(tmp_path):
    script = Path(__file__).resolve().parents[1] / "scripts" / "discover_planillas.py"
    source_hashes = {
        path.relative_to(PLANILLAS_DIR).as_posix(): sha256_file(path)
        for path in discover_pdf_paths(PLANILLAS_DIR)
    }
    environment = {**os.environ, "DATABASE_URL": "sqlite:///:memory:"}

    outputs = []
    for name in ("first", "second"):
        output = tmp_path / name
        result = subprocess.run(
            [sys.executable, str(script), str(PLANILLAS_DIR), str(output)],
            capture_output=True,
            text=True,
            env=environment,
        )
        assert result.returncode == 0, result.stderr
        assert set(path.name for path in output.iterdir()) == {"manifest.json", "manifest.csv", "report.md"}
        outputs.append(output)

    manifest = json.loads((outputs[0] / "manifest.json").read_text(encoding="utf-8"))
    records = manifest["records"]
    duplicate_records = [record for record in records if record["duplicate_aliases"]]
    parse_errors = [(record["source_path"], record["parse_error"]) for record in records if record["parse_error"]]
    missing_scores = [
        record["source_path"]
        for record in records
        if record["fields"].get("home_score", {}).get("value") is None
        or record["fields"].get("away_score", {}).get("value") is None
    ]

    assert len(source_hashes) == 138
    assert sum(1 + len(record["duplicate_aliases"]) for record in records) == 138
    assert len(duplicate_records) == 2
    assert sum(1 + len(record["duplicate_aliases"]) for record in duplicate_records) == 4
    assert sum(record["page_count"] > 1 for record in records) == 8
    assert not parse_errors, parse_errors
    assert not missing_scores, missing_scores
    missing_team_labels = [record["source_path"] for record in records if "missing-team-label" in record["quality_flags"]]
    assert not missing_team_labels, missing_team_labels
    assert {
        path.relative_to(PLANILLAS_DIR).as_posix(): sha256_file(path)
        for path in discover_pdf_paths(PLANILLAS_DIR)
    } == source_hashes
    for artifact in ("manifest.json", "manifest.csv", "report.md"):
        assert (outputs[0] / artifact).read_bytes() == (outputs[1] / artifact).read_bytes()
