from datetime import date

import pytest
from alembic import command
from sqlalchemy import create_engine, inspect

from app.models import (CanonicalEvent, CanonicalEventRevision, Match, MatchSquad, OfficialSnapshot,
                        OfficialSnapshotPlayer, Player, ScheduledMatch, StageRoster, Team, User)
from app.schemas import CanonicalEventCommand, CanonicalEventRevisionInput
from app.services.canonical_analysis_service import (
    CanonicalMatchState, CanonicalStateConflictError, CanonicalValidationError, _roster_sources, apply_transition,
    _project_match_state, order_key, read_metrics, revision_payload, validate_command,
)


def command_for(**values):
    return CanonicalEventCommand(period=1, evidence_state="ambiguous", **{"kind": "shot", **values})


@pytest.mark.parametrize("state", [None, "unknown", "off"])
def test_roster_listed_player_is_recordable_with_unknown_or_contradictory_context(state):
    command = command_for(team_id=1, player_id=10, outcome="miss")
    validate_command(command, actor_id=1, match_team_ids={1, 2}, roster_sources={10: "official_planilla"})
    state_context = CanonicalMatchState(player_states={10: state} if state else {})
    apply_transition(state_context, command, 1)


def test_validates_match_membership_and_preserves_revision_reason():
    with pytest.raises(CanonicalValidationError, match="roster or official planilla"):
        validate_command(command_for(team_id=1, player_id=10), actor_id=1, match_team_ids={1, 2}, roster_sources={})
    revision = CanonicalEventRevisionInput(kind="shot", period=1, evidence_state="confirmed", reason="correct player")
    assert revision_payload(revision)["kind"] == "shot"
    assert "reason" not in revision_payload(revision)


def test_goalkeeper_change_requires_an_active_player_from_the_selected_team():
    command = CanonicalEventCommand(kind="goalkeeper_change", period=1, team_id=2, player_id=10,
                                    outcome="active", evidence_state="confirmed")

    with pytest.raises(CanonicalValidationError, match="active goalkeeper must belong"):
        validate_command(command, actor_id=1, match_team_ids={1, 2}, roster_sources={10: "match_squad"},
                         player_team_ids={10: 1})


def test_shot_zone_is_optional_for_shots_and_rejected_elsewhere():
    assert command_for(shot_zone=7).shot_zone == 7
    assert command_for().shot_zone is None
    with pytest.raises(ValueError, match="shot_zone"):
        CanonicalEventCommand(kind="other", period=1, evidence_state="confirmed", shot_zone=1)
    with pytest.raises(ValueError):
        command_for(shot_zone=10)


def test_resolves_match_squad_planilla_and_fixture_roster_sources(session, registration, round_, stage):
    squad_player, planilla_player, fixture_player = (Player(name=name) for name in ("Squad", "Planilla", "Fixture"))
    session.add_all([squad_player, planilla_player, fixture_player])
    session.flush()
    fixture = ScheduledMatch(stage_id=stage.id, round_id=round_.id, home_registration_id=registration.id,
                             away_registration_id=registration.id, match_number_label="1")
    session.add(fixture)
    session.flush()
    match = Match(scheduled_match_id=fixture.id)
    session.add(match)
    session.flush()
    snapshot = OfficialSnapshot(id="planilla", match_id=match.id, source_filename="sheet.pdf",
                                source_content_type="application/pdf", source_size_bytes=1, source_sha256="x",
                                source_page_count=1, source_path="sheet.pdf", confirmed_date=date(2026, 1, 1),
                                home_team_name="Home", away_team_name="Away", home_score=0, away_score=0)
    session.add_all([snapshot, MatchSquad(match_id=match.id, player_id=squad_player.id, jersey_number=1),
                     OfficialSnapshotPlayer(snapshot_id="planilla", side="home", player_id=planilla_player.id,
                                            name="Planilla", jersey_number=2, official_goals=0, official_yellow=0,
                                            official_2min=0, official_red=0, official_blue=0),
                     StageRoster(registration_id=registration.id, player_id=fixture_player.id, jersey_number=3)])
    session.flush()

    assert _roster_sources(session, match) == {
        squad_player.id: "match_squad",
        planilla_player.id: "official_planilla",
        fixture_player.id: "fixture_stage_roster",
    }
def test_clock_unverified_events_use_server_sequence_for_ordering():
    assert order_key(command_for(clock_unverified=True), 7) == (1, float("inf"), 7)


def test_canonical_migration_is_reversible(alembic_config):
    config, url = alembic_config
    command.upgrade(config, "head")
    engine = create_engine(url)
    try:
        assert {"canonical_events", "canonical_event_revisions", "canonical_evidence", "canonical_projections"} <= set(inspect(engine).get_table_names())
        command.downgrade(config, "20260824_0014")
        assert not {"canonical_events", "canonical_event_revisions", "canonical_evidence", "canonical_projections"} & set(inspect(engine).get_table_names())
    finally:
        engine.dispose()


def test_match_cutover_migration_defaults_to_legacy_fallback_and_is_reversible(alembic_config):
    config, url = alembic_config
    command.upgrade(config, "head")
    engine = create_engine(url)
    try:
        assert "canonical_analysis_enabled" in {column["name"] for column in inspect(engine).get_columns("matches")}
        command.downgrade(config, "20260825_0015")
        assert "canonical_analysis_enabled" not in {column["name"] for column in inspect(engine).get_columns("matches")}
    finally:
        engine.dispose()


def transition(state, event_id, **values):
    return apply_transition(state, command_for(**values), event_id)


def test_kickoff_turnover_recovery_transfers_possession_with_observed_bases():
    state = CanonicalMatchState()
    transition(state, 1, kind="other", team_id=1, outcome="kickoff")
    transition(state, 2, kind="turnover", team_id=1, outcome="interception")
    transition(state, 3, kind="recovery", team_id=2, outcome="interception")

    assert state.possession.team_id == 2
    assert state.possession.start_basis == "recovery:3"
    assert state.possession.terminal_basis is None
    assert [(item.team_id, item.start_basis, item.terminal_basis) for item in state.completed_possessions] == [
        (1, "kickoff:1", "turnover:2")
    ]


def test_pre_match_kickoff_command_keeps_video_evidence_and_establishes_possession():
    kickoff = CanonicalEventCommand(
        kind="other", period=1, regulation_seconds=None, clock_unverified=True, team_id=1,
        player_id=None, related_player_id=None, outcome="kickoff", fact_kind="observed",
        evidence_state="confirmed", uncertainty=["clock_unverified"], note=None,
        evidence=[{"kind": "video", "reference": "https://youtu.be/abcdefghijk",
                   "video_source_id": 4, "video_anchor_seconds": 17.5, "uncertainty": []}],
    )
    validate_command(kickoff, actor_id=1, match_team_ids={1, 2}, roster_sources={})
    state = apply_transition(CanonicalMatchState(), kickoff, 1)

    assert kickoff.regulation_seconds is None
    assert kickoff.clock_unverified is True
    assert kickoff.evidence[0].video_anchor_seconds == 17.5
    assert state.possession is not None
    assert state.possession.team_id == 1
    assert state.possession.start_basis == "kickoff:1"


@pytest.mark.parametrize("values", [
    {"team_id": None},
    {"team_id": 3},
    {"team_id": 1, "evidence": []},
    {"team_id": 1, "evidence": [{"kind": "video", "reference": " ", "video_source_id": 4, "video_anchor_seconds": 1}]},
])
def test_kickoff_requires_a_match_team_and_usable_video_evidence(values):
    kickoff = CanonicalEventCommand(kind="other", period=1, outcome="kickoff", evidence_state="confirmed", **values)
    with pytest.raises(CanonicalValidationError):
        validate_command(kickoff, actor_id=1, match_team_ids={1, 2}, roster_sources={})


def test_unresolved_loss_closes_possession_without_claiming_recovery_or_owner():
    state = CanonicalMatchState()
    transition(state, 1, kind="other", team_id=1, outcome="kickoff")
    transition(state, 2, kind="turnover", team_id=1, outcome="unresolved_loss")

    assert state.possession.team_id == 1
    assert state.possession.unresolved is True
    assert state.possession.terminal_basis == "turnover:2"


def test_metrics_scope_possessions_to_their_period_when_previous_period_stays_open(session):
    home, away = Team(id=1, name="Home"), Team(id=2, name="Away")
    analyst = User(id=1, email="analyst@example.com", hashed_password="x", full_name="Analyst")
    match = Match(id=1, home_team=home, away_team=away)
    payloads = [
        {"kind": "other", "period": 1, "team_id": 1, "outcome": "kickoff"},
        {"kind": "other", "period": 2, "team_id": 2, "outcome": "kickoff"},
        {"kind": "turnover", "period": 2, "team_id": 2, "outcome": "interception"},
    ]
    events = []
    for sequence, payload in enumerate(payloads, 1):
        event = CanonicalEvent(match=match, sequence=sequence)
        event.revisions = [CanonicalEventRevision(
            revision=1, actor_id=1, reason="created",
            payload={**payload, "clock_unverified": False, "fact_kind": "observed",
                     "evidence_state": "confirmed", "uncertainty": []},
        )]
        events.append(event)
    session.add_all([home, away, analyst, match, *events])
    session.commit()

    metrics = read_metrics(session, match.id)

    assert metrics["metrics"]["possessions"]["count"] == 1
    assert metrics["metrics"]["turnovers"]["count"] == 1
    assert metrics["metrics"]["team:2:turnovers"]["count"] == 1


def test_completed_period_one_possession_survives_period_two_kickoff(session):
    home, away = Team(id=1, name="Home"), Team(id=2, name="Away")
    analyst = User(id=1, email="analyst@example.com", hashed_password="x", full_name="Analyst")
    match = Match(id=1, home_team=home, away_team=away)
    payloads = [
        {"kind": "other", "period": 1, "team_id": 1, "outcome": "kickoff"},
        {"kind": "shot", "period": 1, "team_id": 1, "outcome": "goal"},
        {"kind": "other", "period": 2, "team_id": 2, "outcome": "kickoff"},
    ]
    events = []
    for sequence, payload in enumerate(payloads, 1):
        event = CanonicalEvent(match=match, sequence=sequence)
        event.revisions = [CanonicalEventRevision(
            revision=1, actor_id=1, reason="created",
            payload={**payload, "clock_unverified": False, "fact_kind": "observed",
                     "evidence_state": "confirmed", "uncertainty": []},
        )]
        events.append(event)
    session.add_all([home, away, analyst, match, *events])
    session.commit()

    state = _project_match_state([
        (event.sequence, event.id, CanonicalEventCommand(**event.revisions[0].payload)) for event in events
    ])
    metrics = read_metrics(session, match.id)

    assert [(possession.team_id, possession.start_basis, possession.terminal_basis)
            for possession in state.completed_possessions] == [(1, f"kickoff:{events[0].id}", f"shot:{events[1].id}")]
    assert state.possession.team_id == 2
    assert metrics["metrics"]["possessions"]["count"] == 1


def test_shot_preserves_each_terminal_result_and_goal_updates_only_analytical_score():
    state = CanonicalMatchState()
    transition(state, 1, kind="shot", team_id=1, player_id=10, outcome="goal")
    transition(state, 2, kind="shot", team_id=1, player_id=10, outcome="save")
    transition(state, 3, kind="shot", team_id=1, player_id=10, outcome="miss")
    transition(state, 4, kind="shot", team_id=1, player_id=10, outcome="woodwork")
    transition(state, 5, kind="shot", team_id=1, player_id=10, outcome="blocked")

    assert state.analytical_score == {1: 1}
    assert [(shot.event_id, shot.result) for shot in state.shots] == [
        (1, "goal"), (2, "save"), (3, "miss"), (4, "woodwork"), (5, "blocked"),
    ]
    with pytest.raises(CanonicalValidationError, match="terminal result"):
        transition(state, 6, kind="shot", team_id=1, outcome="goal_or_save")


def test_transition_rejects_arbitrary_outcomes_and_duplicate_kickoffs():
    with pytest.raises(CanonicalValidationError, match="supported outcome"):
        transition(CanonicalMatchState(), 1, kind="other", outcome="anything_else")
    state = CanonicalMatchState()
    transition(state, 1, kind="other", team_id=1, outcome="kickoff")
    with pytest.raises(CanonicalStateConflictError, match="already open"):
        transition(state, 2, kind="other", team_id=2, outcome="kickoff")


def test_save_uses_active_opposing_goalkeeper_or_explicit_unknown_fallback():
    state = CanonicalMatchState()
    transition(state, 1, kind="goalkeeper_change", team_id=2, player_id=20, outcome="active")
    transition(state, 2, kind="shot", team_id=1, player_id=10, outcome="save")
    transition(state, 3, kind="goalkeeper_change", team_id=2, outcome="unknown")
    transition(state, 4, kind="shot", team_id=1, player_id=10, outcome="save")

    assert [shot.goalkeeper_id for shot in state.shots] == [20, None]


def test_goalkeeper_tracking_accepts_one_team_without_opponent_roster_state():
    state = CanonicalMatchState()
    transition(state, 1, kind="goalkeeper_change", team_id=2, player_id=20, outcome="active")

    assert state.active_goalkeepers == {2: 20}


def test_shot_keeps_explicit_opposing_goalkeeper_without_reusing_related_player():
    state = CanonicalMatchState()
    transition(state, 1, kind="shot", team_id=1, player_id=10, related_player_id=11, goalkeeper_id=20, outcome="goal")

    assert state.shots[0].player_id == 10
    assert state.shots[0].goalkeeper_id == 20


def test_lineup_substitution_marks_player_active_and_related_player_inactive():
    state = CanonicalMatchState()
    transition(state, 1, kind="lineup_change", team_id=1, player_id=11, outcome="on")
    transition(state, 2, kind="lineup_change", team_id=1, player_id=12, related_player_id=11, outcome="substitution")
    assert state.player_states == {11: "off", 12: "on"}
    transition(state, 3, kind="shot", team_id=1, player_id=11, outcome="miss")

    transition(state, 4, kind="lineup_change", team_id=1, player_id=11, related_player_id=12, outcome="substitution")
    assert state.player_states == {11: "on", 12: "off"}


def test_discipline_accepts_each_visible_sanction_without_blocking_capture():
    state = CanonicalMatchState()
    for event_id, outcome in enumerate(("seven_meter", "two_minute_exclusion", "yellow_card", "red_card", "blue_card"), 1):
        transition(state, event_id, kind="foul_sanction", team_id=1, outcome=outcome)

    assert [item["sanction"] for item in state.discipline] == [
        "seven_meter", "two_minute_exclusion", "yellow_card", "red_card", "blue_card",
    ]


def test_discipline_preserves_unknown_subject_without_blocking_capture():
    state = CanonicalMatchState()
    transition(state, 5, kind="foul_sanction", team_id=1, outcome="two_minute_exclusion", uncertainty=["subject_unknown"])
    assert state.discipline == [{"event_id": 5, "team_id": 1, "player_id": None,
                                 "sanction": "two_minute_exclusion", "uncertainty": ["subject_unknown"]}]
