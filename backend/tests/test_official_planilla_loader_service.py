import hashlib
import json

from app.models import OfficialBatchRun, OfficialSnapshot, ScheduledMatch
from app.services.official_planilla_loader_service import load_approved_planillas, rollback_batch
from app.services.pdf_service import PDFService


def _write_inputs(tmp_path, *, approval_sha=None, home="SAPA"):
    corpus = tmp_path / "corpus"; (corpus / "sheets").mkdir(parents=True)
    sheet = corpus / "sheets" / "sheet.pdf"; sheet.write_bytes(b"local-pdf")
    derived = {"schema_version": 1, "manifest_sha256": "manifest", "mapping_sha256": "mapping", "fixtures": [{
        "source": {"label": "official", "captured_at": "2026-01-01"},
        "stage": {"season": 2026, "name": "Stage", "category": "Senior", "division": "A", "gender": "M"},
        "rounds": [{"number": 1, "entries": [{"entry_key": "planilla:abc:1", "fixture_key": "planilla:abc:1", "kind": "match",
            "home": {"club": "SAPA", "variant": None}, "away": {"club": "Banfield", "variant": "B"}, "date": "2026-01-01",
            "result": {"home": 28, "away": 24, "status": "reported"},
            "planilla": {"source_path": "sheets/sheet.pdf", "sha256": hashlib.sha256(b"local-pdf").hexdigest(), "page_count": 1, "size": 9}}]}]}]}
    derived_path = tmp_path / "derived-fixtures.json"; derived_path.write_text(json.dumps(derived), encoding="utf-8")
    sha = hashlib.sha256(derived_path.read_bytes()).hexdigest()
    approval = {"status": "completed", "approver": "maintainer", "manifest_sha256": "manifest", "mapping_sha256": "mapping", "derived_sha256": approval_sha or sha, "pre_derivation_approval_sha256": "not-a-real-approval"}
    approval_path = tmp_path / "approval.json"; approval_path.write_text(json.dumps(approval), encoding="utf-8")
    return derived_path, approval_path, corpus, home


def _preview(home="SAPA"):
    return {"match_info": {"date": "2026-01-01", "home_score": 28, "away_score": 24},
        "home_team": {"name": home, "players": [{"name": "H", "number": 7, "goals": 2, "yellow": 0, "two_min": 0, "red": 0, "blue": 0}]},
        "away_team": {"name": "Banfield B", "players": []}, "provenance": {"filename": "sheet.pdf", "content_type": "application/pdf", "size_bytes": 9, "sha256": hashlib.sha256(b"local-pdf").hexdigest(), "page_count": 1}}


def test_loader_requires_completed_bootstrap_evidence_before_snapshot_contract(session, tmp_path, monkeypatch):
    derived, approval, corpus, _ = _write_inputs(tmp_path)
    monkeypatch.setattr(PDFService, "preview_femebal_sheet", staticmethod(lambda *_: _preview()))

    first = load_approved_planillas(session, derived, approval, source_root=corpus)
    second = load_approved_planillas(session, derived, approval, source_root=corpus)

    assert first.rejected and second.rejected
    assert session.query(ScheduledMatch).count() == session.query(OfficialSnapshot).count() == 0


def test_loader_rejects_hash_mismatch_before_fixture_write(session, tmp_path):
    derived, _, corpus, _ = _write_inputs(tmp_path, approval_sha="wrong")
    approval = tmp_path / "approval.json"

    result = load_approved_planillas(session, derived, approval, source_root=corpus)

    assert result.rejected and session.query(ScheduledMatch).count() == session.query(OfficialSnapshot).count() == 0
    assert session.query(OfficialBatchRun).one().status == "rejected"


def test_loader_rejects_missing_completed_bootstrap_evidence_without_fixture_write(session, tmp_path):
    derived, approval, corpus, _ = _write_inputs(tmp_path)

    result = load_approved_planillas(session, derived, approval, source_root=corpus)

    assert result.rejected and session.query(ScheduledMatch).count() == session.query(OfficialSnapshot).count() == 0


def test_loader_rejects_before_pdf_parsing_when_bootstrap_evidence_is_missing(session, tmp_path, monkeypatch):
    derived, approval, corpus, _ = _write_inputs(tmp_path)
    monkeypatch.setattr(PDFService, "preview_femebal_sheet", staticmethod(lambda *_: _preview("Lanus")))

    result = load_approved_planillas(session, derived, approval, source_root=corpus)

    assert result.rejected and result.skipped == []
    assert session.query(ScheduledMatch).count() == 0


def test_loader_rejects_before_pdf_read_when_bootstrap_evidence_is_missing(session, tmp_path):
    derived, approval, corpus, _ = _write_inputs(tmp_path)

    result = load_approved_planillas(session, derived, approval, source_root=corpus)

    assert result.rejected and result.skipped == []
    assert session.query(OfficialBatchRun).one().status == "rejected"


def test_rejected_loader_has_no_batch_owned_snapshot_to_roll_back(session, tmp_path, monkeypatch):
    derived, approval, corpus, _ = _write_inputs(tmp_path)
    monkeypatch.setattr(PDFService, "preview_femebal_sheet", staticmethod(lambda *_: _preview()))
    result = load_approved_planillas(session, derived, approval, source_root=corpus)

    assert result.rejected
    assert session.query(OfficialSnapshot).count() == session.query(ScheduledMatch).count() == 0
