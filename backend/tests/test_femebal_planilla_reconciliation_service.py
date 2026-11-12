from app.services.femebal_planilla_reconciliation_service import build_femebal_planilla_reconciliation


def test_reconciles_by_explicit_tracker_pdf_url_despite_header_date_difference():
    manifest = {"records": [{"source_path": "permanencia/sheet.pdf", "sha256": "abc", "page_count": 1,
        "fields": {"date": {"value": "2026-10-10"}, "home_score": {"value": 26}, "away_score": {"value": 28}}}]}
    fixture = {"rounds": [{"entries": [{"kind": "match", "fixture_key": "femebal:1", "date": "2026-10-09",
        "result": {"home": 26, "away": 28}, "evidence": {"tracker_match_id": "1", "planillas": [{"pdf_url": "https://example.test/sheet.pdf"}]}}]}]}

    result = build_femebal_planilla_reconciliation(manifest, fixture, source_stage="permanencia")

    assert result["counts"] == {"local_records": 1, "linked": 1, "unmatched": 0}
    assert result["links"][0]["fixture_key"] == "femebal:1"
    assert result["links"][0]["official_planilla_date"] == "2026-10-10"


def test_reconciles_explicit_pdf_when_tracker_has_no_reported_score():
    manifest = {"records": [{"source_path": "permanencia/sheet.pdf", "sha256": "abc",
        "fields": {"date": {"value": "2026-11-01"}, "home_score": {"value": 29}, "away_score": {"value": 28}}}]}
    fixture = {"rounds": [{"entries": [{"kind": "match", "fixture_key": "femebal:1", "date": "2026-11-01",
        "evidence": {"tracker_match_id": "1", "planillas": [{"pdf_url": "https://example.test/sheet.pdf"}]}}]}]}

    result = build_femebal_planilla_reconciliation(manifest, fixture, source_stage="permanencia")

    assert result["counts"]["linked"] == 1


def test_planilla_score_overrides_a_stale_reported_tracker_score():
    manifest = {"records": [{"source_path": "permanencia/sheet.pdf", "sha256": "abc",
        "fields": {"date": {"value": "2026-08-23"}, "home_score": {"value": 16}, "away_score": {"value": 12}}}]}
    fixture = {"rounds": [{"entries": [{"kind": "match", "fixture_key": "femebal:1", "date": "2026-08-23",
        "result": {"home": 2, "away": 0}, "evidence": {"tracker_match_id": "1",
        "planillas": [{"pdf_url": "https://example.test/sheet.pdf"}]}}]}]}

    result = build_femebal_planilla_reconciliation(manifest, fixture, source_stage="permanencia")

    assert result["counts"]["linked"] == 1
    assert result["links"][0]["tracker_score_disagrees"] is True


def test_reconciles_by_date_and_team_labels_when_tracker_url_is_missing():
    manifest = {"records": [{"source_path": "permanencia/late.pdf", "sha256": "abc",
        "fields": {"date": {"value": "2026-11-08"}, "home_name": {"value": "C.A. Lanús C"},
                   "away_name": {"value": "Municipalidad de San Martín (Ce.M.E.F)"},
                   "home_score": {"value": 35}, "away_score": {"value": 20}}}]}
    fixture = {"rounds": [{"entries": [{"kind": "match", "fixture_key": "femebal:1", "date": "2026-11-08",
        "result": {"home": 35, "away": 20}, "evidence": {"tracker_match_id": "1",
        "tracker_labels": {"home": "C.A. Lanús C", "away": "Municipalidad de San Martín (Ce.M.E.F)"},
        "planillas": []}}]}]}

    result = build_femebal_planilla_reconciliation(manifest, fixture, source_stage="permanencia")

    assert result["counts"] == {"local_records": 1, "linked": 1, "unmatched": 0}
    assert result["links"][0]["fixture_key"] == "femebal:1"
    assert result["links"][0]["match_method"] == "date_and_team_labels"
    assert result["links"][0]["pdf_url"] is None
