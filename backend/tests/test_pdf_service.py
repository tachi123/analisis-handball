import hashlib
import json
from pathlib import Path

import pdfplumber
import pytest

from app.services.pdf_header_parser import parse_header_blocks, parse_header_pages
from app.schemas import PDFPreview
from app.services.pdf_service import PDFParseError, PDFService


FIXTURES_DIR = Path(__file__).parent / "fixtures"
SAMPLE_SHEET = (
    Path(__file__).resolve().parents[2]
    / "resources"
    / "planillas"
    / "planilla_banfield_b_vs_sapa.pdf"
)
PLANILLAS_DIR = SAMPLE_SHEET.parent
MULTI_PAGE_FILENAMES = (
    "020924c1e932fdb0.pdf", "27652047cf48aab4.pdf", "2f9955aed9c3138a.pdf", "7c5e0248513cd3b0.pdf",
    "a1f001feaf543c73.pdf", "a646d2dc7b0e0ee9.pdf", "a6f34e0c4a7d950a.pdf", "ba47c22446ddfec7.pdf",
)


def planilla(filename: str) -> Path:
    return next(PLANILLAS_DIR.rglob(filename))


def test_preview_composes_evidenced_header_fields_and_legacy_values():
    contents = SAMPLE_SHEET.read_bytes()

    preview = PDFService.preview_femebal_sheet(
        contents,
        SAMPLE_SHEET.name,
        "application/pdf",
    )

    assert preview["provenance"] == {
        "filename": SAMPLE_SHEET.name,
        "content_type": "application/pdf",
        "size_bytes": len(contents),
        "sha256": hashlib.sha256(contents).hexdigest(),
        "page_count": 1,
    }
    assert preview["home_team"]["players"]
    assert preview["match_info"] == {
        "tournament": "Metropolitano Apertura Zona A",
        "venue": "Lanus Este",
        "court": "CI.DE.CO Gimnasio 1",
        "date": "2026-05-31",
        "time": "19:45",
        "category": preview["fields"]["category"]["value"],
        "match_number": "10",
        "home_score": 31,
        "away_score": 31,
    }
    assert (preview["home_team"]["name"], preview["away_team"]["name"]) == ("C.A. Banfield B", "S.A.P.A.")
    assert (preview["match_info"]["home_score"], preview["match_info"]["away_score"]) == (31, 31)
    assert preview["fields"]["home_score"] == {
        "value": 31,
        "raw": "Equip o local\n31\nC.A. Banfield B",
        "source": {"page": 1, "table": 1, "label": "Equip o local"},
        "confidence": "high",
        "warnings": [],
    }
    assert PDFPreview.model_validate(preview).fields["tournament"].source.label == "Torneo"


def test_preview_retains_unresolved_field_warnings_without_legacy_defaults(monkeypatch):
    unresolved_fields = (
        "venue", "court", "date", "time", "category", "match_number", "tournament",
        "home_name", "away_name", "home_score", "away_score",
    )
    monkeypatch.setattr(
        "app.services.pdf_service.parse_header_pages",
        lambda pages, word_pages=None: {
            "fields": {
                field: {"value": None, "raw": None, "source": None, "confidence": "unresolved", "warnings": [f"{field} is missing"]}
                for field in unresolved_fields
            },
            "warnings": ["home_score is missing", "away_score is missing"],
        },
    )

    preview = PDFService.preview_femebal_sheet(SAMPLE_SHEET.read_bytes(), SAMPLE_SHEET.name, "application/pdf")

    assert preview["home_team"]["name"] == ""
    assert preview["away_team"]["name"] == ""
    assert "home_score" not in preview["match_info"]
    assert "away_score" not in preview["match_info"]
    assert "home_score is missing" in preview["warnings"]
    assert "No se pudo identificar el marcador oficial" in preview["warnings"]


def test_preview_rejects_an_unreadable_pdf_fixture():
    with pytest.raises(PDFParseError, match="No se pudo leer el PDF de planilla"):
        PDFService.preview_femebal_sheet(
            (FIXTURES_DIR / "invalid_sheet.pdf").read_bytes(),
            "invalid_sheet.pdf",
            "application/pdf",
        )


def test_header_parser_extracts_evidenced_facts_from_banfield_sheet():
    with pdfplumber.open(SAMPLE_SHEET) as pdf:
        page = pdf.pages[0]
        parsed = parse_header_blocks(page.extract_tables(), page.extract_text())

    fields = parsed["fields"]
    assert {field: fields[field]["value"] for field in ("tournament", "venue", "court", "date", "time", "match_number")} == {
        "tournament": "Metropolitano Apertura Zona A", "venue": "Lanus Este", "court": "CI.DE.CO Gimnasio 1",
        "date": "2026-05-31", "time": "19:45", "match_number": "10",
    }
    assert fields["category"]["value"] == fields["category"]["raw"].split("\n", 1)[1]
    assert (fields["home_name"]["value"], fields["home_score"]["value"]) == ("C.A. Banfield B", 31)
    assert (fields["away_name"]["value"], fields["away_score"]["value"]) == ("S.A.P.A.", 31)
    assert fields["home_score"]["source"] == {"page": 1, "table": 1, "label": "Equip o local"}


def test_header_parser_uses_labels_for_sides_and_preserves_degraded_text():
    fixture = json.loads((FIXTURES_DIR / "banfield_b_vs_sapa_blocks.json").read_text(encoding="utf-8"))
    parsed = parse_header_blocks(fixture["tables"], fixture["text"])

    assert parsed["fields"]["home_name"]["value"] == "C.A. Banfield B"
    assert parsed["fields"]["away_name"]["value"] == "S.A.P.A."
    assert parsed["fields"]["category"]["value"] == "Mayores - 3� Divisi�n"
    assert parsed["fields"]["category"]["warnings"] == ["category contains encoding-degraded source text"]


def test_header_parser_does_not_infer_missing_scores():
    parsed = parse_header_blocks([[["Equipo local\nC.A. Banfield B", "Equipo visitante\nS.A.P.A."]]], None)

    assert parsed["fields"]["home_score"]["value"] is None
    assert parsed["fields"]["away_score"]["value"] is None
    assert "home_score is missing in labelled source blocks" in parsed["warnings"]


def test_header_parser_aggregates_later_page_evidence_and_rejects_conflicts():
    parsed = parse_header_pages([
        ([[["Cancha:\nCourt One"]]], "", 1),
        ([[["Cancha:\nCourt Two", "Equipo local\n18\nHome"]]], "", 2),
    ])

    assert parsed["fields"]["court"]["value"] is None
    assert "court is conflicting in labelled source blocks" in parsed["warnings"]
    assert parsed["fields"]["home_score"]["source"] == {"page": 2, "table": 0, "label": "Equipo local"}


@pytest.mark.parametrize("filename", MULTI_PAGE_FILENAMES)
def test_preview_reads_every_real_multi_page_planilla(filename):
    sheet = planilla(filename)

    preview = PDFService.preview_femebal_sheet(sheet.read_bytes(), sheet.name, "application/pdf")

    assert preview["provenance"]["page_count"] == 2


def test_real_apertura_layout_recovers_split_labelled_team_name():
    sheet = planilla("020924c1e932fdb0.pdf")

    preview = PDFService.preview_femebal_sheet(sheet.read_bytes(), sheet.name, "application/pdf")

    assert preview["home_team"]["name"]
    assert preview["away_team"]["name"] == "C.A. Defensores de Moreno"
    assert preview["match_info"]["away_score"] == 23
    assert preview["fields"]["away_name"]["confidence"] == "high"


def test_real_permanencia_layout_retains_clean_header_scores_and_rosters():
    sheet = planilla("f0c3941767714bf6.pdf")

    preview = PDFService.preview_femebal_sheet(sheet.read_bytes(), sheet.name, "application/pdf")

    assert preview["home_team"]["name"]
    assert preview["away_team"]["name"] == "S.A.G. Polvorines D"
    assert (preview["match_info"]["home_score"], preview["match_info"]["away_score"]) == (33, 22)
    assert (len(preview["home_team"]["players"]), len(preview["away_team"]["players"])) == (14, 14)


def test_parse_sheet_merges_page_two_roster_rows_with_provenance(monkeypatch):
    roster_header = ["N° Local", "Nombre", "G", "A", "2M", "R", "B", "N° Visitante", "Nombre", "G", "A", "2M", "R", "B"]
    pages = [
        FakePage([
            [["Equipo local\n10\nHome", "Equipo visitante\n8\nAway"]],
            [roster_header, [1, "First Home", 2, "-", 0, "-", "-", 2, "First Away", 1, "-", 0, "-", "-"]],
        ], "Torneo Test"),
        FakePage([[roster_header, [3, "Later Home", 1, "-", 0, "-", "-", 4, "Later Away", 0, "-", 0, "-", "-"]]], ""),
    ]
    monkeypatch.setattr("app.services.pdf_service.pdfplumber.open", lambda _: FakePDF(pages))

    parsed = PDFService.parse_femebal_sheet(object())

    assert [player["name"] for player in parsed["home_team"]["players"]] == ["First Home", "Later Home"]
    assert [player["source"] for player in parsed["away_team"]["players"]] == [{"page": 1}, {"page": 2}]


class FakePage:
    def __init__(self, tables, text):
        self.tables = tables
        self.text = text

    def extract_tables(self):
        return self.tables

    def extract_text(self):
        return self.text


class FakePDF:
    def __init__(self, pages):
        self.pages = pages

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False
