"""Tests for normalize_competition_team_name utility.

Covers suffix-preserving normalization per spec:
- Preserves single-letter suffix (A, B, C, D)
- Normalizes accents, punctuation, whitespace only
- Never drops letters after club name
"""

import pytest

from app.services import normalize_competition_team_name


class TestNormalizePreservesSuffix:
    """Suffix preservation is the critical invariant."""

    def test_suffix_b_with_whitespace(self):
        """Suffix B preserved with extra whitespace."""
        assert normalize_competition_team_name("Banfield  B  ") == "Banfield B"

    def test_suffix_c_with_whitespace(self):
        """Suffix C preserved with extra whitespace."""
        assert normalize_competition_team_name("Comunicaciones  C  ") == "Comunicaciones C"

    def test_suffix_a_with_accent(self):
        """Accent removed, suffix A preserved."""
        assert normalize_competition_team_name("Atlético  A  ") == "Atletico A"

    def test_suffix_lowercase_normalized_to_uppercase(self):
        """Lowercase suffix normalized to uppercase; club name case preserved."""
        assert normalize_competition_team_name("banfield  b  ") == "banfield B"

    def test_punctuation_preserved_suffix_intact(self):
        """Punctuation preserved (only accents removed), suffix preserved."""
        assert normalize_competition_team_name("C.A. Banfield  B  ") == "C.A. Banfield B"


class TestNormalizeEdgeCases:
    """Edge cases and non-suffix patterns."""

    def test_no_suffix_returns_whitespace_normalized(self):
        """An absent variant stays absent; normalization never manufactures one."""
        assert normalize_competition_team_name("  SAPA   ") == "SAPA"
        assert normalize_competition_team_name("  Banfield   ") == "Banfield"

    def test_empty_string_returns_empty(self):
        """Empty string returns empty."""
        assert normalize_competition_team_name("") == ""
        assert normalize_competition_team_name(None) == ""

    def test_multi_letter_suffix_not_recognized(self):
        """Multi-letter suffix (e.g., 'Juniors') not treated as suffix."""
        result = normalize_competition_team_name("Argentinos  Juniors  ")
        assert result == "Argentinos Juniors"

    def test_single_letter_club_name_with_suffix(self):
        """Single letter club name with suffix handled correctly."""
        assert normalize_competition_team_name("A  B  ") == "A B"

    def test_multiple_spaces_between_parts(self):
        """Multiple spaces collapsed to single space."""
        assert normalize_competition_team_name("Club    Atletico    A") == "Club Atletico A"

    def test_tab_and_newline_normalized(self):
        """Tabs and newlines normalized to spaces."""
        assert normalize_competition_team_name("Banfield\tB\n") == "Banfield B"

    def test_suffix_with_non_alpha_not_recognized(self):
        """Non-alphabetic suffix not recognized."""
        assert normalize_competition_team_name("Banfield  1  ") == "Banfield 1"

    def test_mixed_case_club_name_preserved(self):
        """Club name case preserved, only suffix uppercased."""
        assert normalize_competition_team_name("bAnFiElD  b  ") == "bAnFiElD B"
