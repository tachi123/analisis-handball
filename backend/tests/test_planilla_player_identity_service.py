import json

import pytest
import app.services.planilla_player_identity_service as identity_service

from app.services.planilla_player_identity_service import (
    CONFLICT_SIMILARITY_THRESHOLD,
    NAME_SIMILARITY_THRESHOLD,
    build_identities,
    flatten_manifest,
    multiset_dice_score,
    name_similarity,
    normalize_name,
    write_identity_artifacts,
)


def manifest(*records):
    return {"schema_version": 1, "records": list(records)}


def record(sha, stage, tournament, home, away, local=(), visitante=()):
    return {
        "sha256": sha,
        "source_path": f"{stage}/{sha}.pdf",
        "fields": {"tournament": {"value": tournament}, "home_name": {"value": home}, "away_name": {"value": away}},
        "rosters": {"local": list(local), "visitante": list(visitante)},
    }


def player(name, number, page=1, **stats):
    return {"name": name, "number": number, "source": {"page": page}, **stats}


@pytest.mark.parametrize(
    ("variant", "expected"),
    [
        ("García, Ana María", "ana garcia maria"),
        ("ana maria garcia", "ana garcia maria"),
        ("ANA-MARIA GARCIA", "ana garcia maria"),
    ],
)
def test_normalize_name_folds_accents_case_punctuation_and_token_order(variant, expected):
    assert normalize_name(variant) == expected


def test_name_similarity_is_identical_for_accent_case_and_order_variants():
    assert name_similarity("García, Ana María", "ana maria garcia") == 1.0


def test_multiset_dice_score_includes_the_exact_threshold_boundary():
    shared = [f"shared{index:03}" for index in range(90)]
    left = " ".join(shared + [f"left{index:03}" for index in range(10)])
    right = " ".join(shared + [f"right{index:03}" for index in range(10)])

    score = multiset_dice_score(left, right)

    assert score == pytest.approx(NAME_SIMILARITY_THRESHOLD)
    assert score >= NAME_SIMILARITY_THRESHOLD


def test_multiset_dice_score_excludes_a_near_miss_below_the_threshold():
    shared = [f"shared{index:03}" for index in range(89)]
    left = " ".join(shared + [f"left{index:03}" for index in range(11)])
    right = " ".join(shared + [f"right{index:03}" for index in range(11)])

    score = multiset_dice_score(left, right)

    assert score == pytest.approx(0.89)
    assert score < NAME_SIMILARITY_THRESHOLD


def test_flatten_manifest_builds_stable_row_ids_and_stage_tournament_scopes():
    rows = flatten_manifest(manifest(record("b" * 64, "Apertura", "Metro A", "Club Á", "Club B", local=[player("Ana", 7)])))

    assert rows[0]["row_id"] == f"{'b' * 64}:local:1:0"
    assert rows[0]["scope"] == {"source_stage": "Apertura", "tournament": "a metro"}
    assert rows[0]["normalized_team"] == "a club"


def test_build_identities_auto_groups_same_scope_team_and_records_jerseys():
    source = manifest(
        record("a" * 64, "Apertura", "Metro", "Club", "Rival", local=[player("García, Ana María", 7, goals=2)]),
        record("b" * 64, "Apertura", "Metro", "Club", "Rival", local=[player("ana maria garcia", 7, goals=3)]),
    )

    result = build_identities(source)

    assert [(link["tier"], link["reasons"]) for link in result["links"]] == [("auto_group", ["same_team", "same_jersey"])]
    assert result["identities"][0]["tier"] == "auto_group"
    assert result["identities"][0]["jerseys"] == [7]
    assert result["identities"][0]["notes"] == []
    assert result["identities"][0]["preview"] == {"appearances": 2, "goals": 5, "yellow": 0, "two_min": 0, "red": 0, "blue": 0}


@pytest.mark.parametrize(
    ("left", "right", "expected_tier", "reason"),
    [
        (record("a" * 64, "Apertura", "Metro", "Club A", "Rival", local=[player("Ana García", 7)]), record("b" * 64, "Apertura", "Metro", "Club B", "Rival", local=[player("Ana García", 7)]), "review", "different_team"),
        (record("a" * 64, "Apertura", "Metro", None, "Rival", local=[player("Ana García", 7)]), record("b" * 64, "Apertura", "Metro", "Club", "Rival", local=[player("Ana García", 7)]), "review", "missing_team_label"),
    ],
)
def test_build_identities_keeps_nonmatching_team_or_missing_team_candidates_separate(left, right, expected_tier, reason):
    result = build_identities(manifest(left, right))

    assert result["links"][0]["tier"] == expected_tier
    assert reason in result["links"][0]["reasons"]
    assert len(result["identities"]) == 2


def test_build_identities_auto_groups_same_team_jersey_swap_with_a_non_blocking_note():
    result = build_identities(manifest(
        record("a" * 64, "Apertura", "Metro", "Club", "Rival", local=[player("Ana García", 1)]),
        record("b" * 64, "Apertura", "Metro", "Club", "Rival", local=[player("Ana García", 8)]),
    ))

    assert result["links"][0]["tier"] == "auto_group"
    assert result["links"][0]["reasons"] == ["same_team", "jersey_variation"]
    assert len(result["identities"]) == 1
    assert result["identities"][0]["jerseys"] == [1, 8]
    assert result["identities"][0]["notes"] == ["jersey_variation"]


def test_build_identities_auto_groups_same_team_when_a_jersey_is_missing():
    result = build_identities(manifest(
        record("a" * 64, "Apertura", "Metro", "Club", "Rival", local=[player("Ana García", None)]),
        record("b" * 64, "Apertura", "Metro", "Club", "Rival", local=[player("Ana García", 7)]),
    ))

    assert result["links"][0]["tier"] == "auto_group"
    assert result["links"][0]["reasons"] == ["same_team", "missing_jersey"]
    assert result["identities"][0]["jerseys"] == [7]
    assert result["identities"][0]["notes"] == []


def test_build_identities_reports_same_team_below_threshold_name_collision_as_conflict():
    result = build_identities(manifest(
        record("a" * 64, "Apertura", "Metro", "Club", "Rival", local=[player("Ana María García", 7)]),
        record("b" * 64, "Apertura", "Metro", "Club", "Rival", local=[player("Ana García González", 8)]),
    ))

    assert result["links"][0]["tier"] == "conflict"
    assert result["links"][0]["reasons"] == ["same_team", "below_threshold_name_collision"]
    assert len(result["identities"]) == 2


def test_build_identities_reports_the_two_thirds_same_team_collision_boundary_as_conflict():
    result = build_identities(manifest(
        record("a" * 64, "Apertura", "Metro", "Club", "Rival", local=[player("Ana María García", 7)]),
        record("b" * 64, "Apertura", "Metro", "Club", "Rival", local=[player("Ana María López", 8)]),
    ))

    assert result["links"][0]["score"] == pytest.approx(CONFLICT_SIMILARITY_THRESHOLD)
    assert result["links"][0]["tier"] == "conflict"


def test_build_identities_leaves_below_two_thirds_same_team_noise_unlinked():
    result = build_identities(manifest(
        record("a" * 64, "Apertura", "Metro", "Club", "Rival", local=[player("Ana María García López", 7)]),
        record("b" * 64, "Apertura", "Metro", "Club", "Rival", local=[player("Ana María Paz Sol", 8)]),
    ))

    assert result["links"] == []
    assert len(result["identities"]) == 2


def test_build_identities_requires_two_shared_tokens_for_a_same_team_conflict():
    result = build_identities(manifest(
        record("a" * 64, "Apertura", "Metro", "Club", "Rival", local=[player("Ana García", 7)]),
        record("b" * 64, "Apertura", "Metro", "Club", "Rival", local=[player("Ana", 8)]),
    ))

    assert multiset_dice_score("ana garcia", "ana") == pytest.approx(CONFLICT_SIMILARITY_THRESHOLD)
    assert result["links"] == []
    assert len(result["identities"]) == 2


def test_build_identities_never_links_equal_rows_across_stages():
    result = build_identities(manifest(
        record("a" * 64, "Apertura", "Metro", "Club", "Rival", local=[player("Ana García", 7)]),
        record("b" * 64, "Permanencia", "Metro", "Club", "Rival", local=[player("Ana García", 7)]),
    ))

    assert result["links"] == []
    assert len(result["identities"]) == 2


def test_override_merge_joins_review_rows_in_order_and_keeps_provenance():
    source = manifest(
        record("a" * 64, "Apertura", "Metro", "Club", "Rival", local=[player("Ana García", None)]),
        record("b" * 64, "Apertura", "Metro", "Club", "Rival", local=[player("Ana García", 7)]),
    )
    row_ids = [row["row_id"] for row in flatten_manifest(source)]

    result = build_identities(source, {"schema_version": 1, "links": [{"action": "merge", "left_row_id": row_ids[1], "right_row_id": row_ids[0]}]})

    assert result["identities"][0]["member_row_ids"] == row_ids
    assert result["identities"][0]["tier"] == "review"
    assert result["identities"][0]["provenance"] == [{"action": "merge", "sequence": 0, "left_row_id": row_ids[1], "right_row_id": row_ids[0]}]


def test_override_split_separates_an_auto_group():
    source = manifest(
        record("a" * 64, "Apertura", "Metro", "Club", "Rival", local=[player("Ana García", 7)]),
        record("b" * 64, "Apertura", "Metro", "Club", "Rival", local=[player("Ana García", 7)]),
    )
    row_ids = [row["row_id"] for row in flatten_manifest(source)]

    result = build_identities(source, {"schema_version": 1, "links": [{"action": "split", "left_row_id": row_ids[0], "right_row_id": row_ids[1]}]})

    assert [identity["member_row_ids"] for identity in result["identities"]] == [[row_ids[0]], [row_ids[1]]]


@pytest.mark.parametrize("overrides", [
    {"schema_version": 2, "links": []},
    {"schema_version": 1, "links": [{"action": "unknown", "left_row_id": "a", "right_row_id": "b"}]},
    {"schema_version": 1, "links": [{"action": "accept", "left_row_id": "a", "right_row_id": "b"}]},
])
def test_invalid_override_document_fails_before_a_result_is_built(overrides):
    source = manifest(record("a" * 64, "Apertura", "Metro", "Club", "Rival", local=[player("Ana", 7)]))

    with pytest.raises(ValueError):
        build_identities(source, overrides)


def test_later_override_action_wins_and_transitive_rejection_fails():
    source = manifest(*[
        record(character * 64, "Apertura", "Metro", "Club", "Rival", local=[player("Ana García", 7)])
        for character in "ab"
    ])
    row_ids = [row["row_id"] for row in flatten_manifest(source)]
    later_split = {"schema_version": 1, "links": [
        {"action": "merge", "left_row_id": row_ids[0], "right_row_id": row_ids[1]},
        {"action": "split", "left_row_id": row_ids[0], "right_row_id": row_ids[1]},
    ]}

    assert len(build_identities(source, later_split)["identities"]) == 2
    review_source = manifest(*[
        record(character * 64, "Apertura", "Metro", "Club", "Rival", local=[player("Ana García", None)])
        for character in "abc"
    ])
    review_row_ids = [row["row_id"] for row in flatten_manifest(review_source)]
    with pytest.raises(ValueError, match="contradicts"):
        build_identities(review_source, {"schema_version": 1, "links": [
            {"action": "merge", "left_row_id": review_row_ids[0], "right_row_id": review_row_ids[1]},
            {"action": "merge", "left_row_id": review_row_ids[1], "right_row_id": review_row_ids[2]},
            {"action": "reject", "left_row_id": review_row_ids[0], "right_row_id": review_row_ids[2]},
        ]})


def test_writers_are_byte_stable_for_all_review_artifacts(tmp_path):
    source = manifest(
        record("a" * 64, "Apertura", "Metro", "Club", "Rival", local=[player("Ana María García", 7, goals=2)]),
        record("b" * 64, "Apertura", "Metro", "Club", "Rival", local=[player("Ana García González", 7, yellow=1)]),
    )
    result = build_identities(source)
    first, second = tmp_path / "first", tmp_path / "second"

    write_identity_artifacts(result, first)
    write_identity_artifacts(result, second)

    filenames = ("identities.json", "identities.csv", "conflicts.md", "identity-summary.json")
    assert {name: (first / name).read_bytes() for name in filenames} == {name: (second / name).read_bytes() for name in filenames}
    assert len((first / "identities.csv").read_text(encoding="utf-8").splitlines()) == 3
    assert "below_threshold_name_collision" in (first / "conflicts.md").read_text(encoding="utf-8")
    assert json.loads((first / "identity-summary.json").read_text(encoding="utf-8"))["aggregate_totals"] == {"appearances": 2, "goals": 2, "yellow": 1, "two_min": 0, "red": 0, "blue": 0}


def test_writer_failure_while_staging_keeps_existing_artifacts(tmp_path, monkeypatch):
    result = build_identities(manifest(record("a" * 64, "Apertura", "Metro", "Club", "Rival", local=[player("Ana", 7)])))
    filenames = ("identities.json", "identities.csv", "conflicts.md", "identity-summary.json")
    for filename in filenames:
        (tmp_path / filename).write_text("previous\n", encoding="utf-8")
    original_mkstemp, calls = identity_service.tempfile.mkstemp, 0

    def fail_on_second_tempfile(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("simulated staging failure")
        return original_mkstemp(*args, **kwargs)

    monkeypatch.setattr(identity_service.tempfile, "mkstemp", fail_on_second_tempfile)
    with pytest.raises(OSError, match="staging failure"):
        write_identity_artifacts(result, tmp_path)
    assert {(tmp_path / filename).read_text(encoding="utf-8") for filename in filenames} == {"previous\n"}
