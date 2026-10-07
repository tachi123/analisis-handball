"""Services package initialization with shared utilities."""

import re
import unicodedata


def normalize_competition_team_name(value: str) -> str:
    """Normalize a competition team name preserving the suffix.

    Only normalizes accents, punctuation, and whitespace.
    Never drops the letter suffix (A, B, C, D) that distinguishes teams.

    Examples:
        "Banfield  B  " -> "Banfield B"
        "Comunicaciones  C  " -> "Comunicaciones C"
        "Atlético  A  " -> "Atletico A"
    """
    if not value:
        return ""

    # Normalize unicode (decompose accents)
    decomposed = unicodedata.normalize("NFD", value)
    # Remove combining marks (accents)
    without_accents = "".join(
        char for char in decomposed if unicodedata.category(char) != "Mn"
    )

    # Normalize whitespace: collapse multiple spaces, trim
    normalized_whitespace = re.sub(r"\s+", " ", without_accents).strip()

    # The suffix is the last letter (A-Z) after the last space
    # We need to preserve it. The pattern is: "ClubName SUFFIX"
    # where SUFFIX is typically a single letter A, B, C, D
    parts = normalized_whitespace.rsplit(" ", 1)
    if len(parts) == 2 and len(parts[1]) == 1 and parts[1].isalpha():
        # Has a valid single-letter suffix
        club_part = parts[0].strip()
        suffix = parts[1].upper()
        return f"{club_part} {suffix}"

    # If no clear suffix pattern, return the whitespace-normalized version
    return normalized_whitespace