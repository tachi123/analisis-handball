from datetime import date

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app
from app.models import AnalysisCodebookEntry, AnalysisEvent, AnalysisSession, CanonicalEvent, CanonicalEventRevision, Event, GoalkeeperShot, Match, MatchSquad, OfficialSnapshot, OfficialSnapshotPlayer, Player, Team, TimeAnchor, TimeSegment, User, VideoSource
from app.security import create_access_token
from app.services import canonical_analysis_service as canonical_service


def kickoff_command(period=1, team_id=1):
    return {"kind": "other", "period": period, "regulation_seconds": 0, "clock_unverified": False,
            "team_id": team_id, "outcome": "kickoff", "evidence_state": "confirmed",
            "evidence": [{"kind": "video", "reference": "https://youtu.be/abcdefghijk", "video_source_id": 4,
                          "video_anchor_seconds": 17, "uncertainty": []}]}


def canonical_client(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'canonical-routes.db'}", connect_args={"check_same_thread": False})
    factory = sessionmaker(bind=engine)
    Base.metadata.create_all(engine)
    db = factory()
    home, away = Team(id=1, name="Home"), Team(id=2, name="Away")
    db.add_all([User(id=1, email="analyst@example.com", hashed_password="x", full_name="Analyst"),
                User(id=2, email="admin@example.com", hashed_password="x", full_name="Admin", role="admin"),
                User(id=3, email="other@example.com", hashed_password="x", full_name="Other"), home, away,
                Player(id=10, name="Shooter", team=home), Player(id=11, name="Substitute", team=home),
                Player(id=20, name="Keeper", team=away), Match(id=1, home_team=home, away_team=away, canonical_analysis_enabled=True),
                OfficialSnapshot(id="pdf-1", match_id=1, source_filename="sheet.pdf", source_content_type="application/pdf",
                    source_size_bytes=1, source_sha256="a", source_page_count=1, source_path="sheet.pdf",
                    confirmed_date=date.today(), home_team_name="Home", away_team_name="Away", home_score=2, away_score=0),
                Event(match_id=1, action_type="legacy"),
                AnalysisCodebookEntry(id=1, version="mvp-1", code="shot", category="attack"),
                 AnalysisEvent(match_id=1, codebook_entry_id=1, analyst_id=1, evidence_state="confirmed"),
                 GoalkeeperShot(match_id=1),
                 VideoSource(id=4, match_id=1, original_url="https://youtu.be/abcdefghijk", provider="youtube", provider_video_id="abcdefghijk", availability_state="ready")])
    db.commit()
    db.add_all([MatchSquad(match_id=1, player_id=10, jersey_number=10), MatchSquad(match_id=1, player_id=11, jersey_number=11),
                MatchSquad(match_id=1, player_id=20, jersey_number=1, is_goalkeeper=True)])
    db.add(CanonicalEventRevision(event=CanonicalEvent(match_id=1, sequence=1), revision=1, actor_id=1,
                                  reason="fixture kickoff", payload={"kind": "other", "period": 1,
                                  "regulation_seconds": 0, "clock_unverified": False, "team_id": 1,
                                  "player_id": None, "related_player_id": None, "outcome": "kickoff",
                                  "fact_kind": "observed", "evidence_state": "confirmed", "uncertainty": [],
                                  "note": None, "evidence": []}))
    db.commit()
    db.close()

    def override_db():
        db = factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_db
    return TestClient(app), engine, factory


def test_authenticated_canonical_commands_and_reads(tmp_path):
    client, engine, _ = canonical_client(tmp_path)
    headers = {"Authorization": f"Bearer {create_access_token({'sub': '1'})}"}
    command = {"kind": "shot", "period": 1, "team_id": 1, "player_id": 10, "outcome": "goal", "evidence_state": "confirmed"}
    try:
        assert client.post("/api/v1/matches/1/canonical-events", json=command).status_code == 403
        created = client.post("/api/v1/matches/1/canonical-events", json=command, headers=headers)
        assert created.status_code == 201
        assert created.json()["payload"]["roster_source"] == "match_squad"
        event_id = created.json()["id"]
        assert client.get("/api/v1/matches/1/canonical-state", headers=headers).json()["analytical_score"] == {"1": 1}
        metrics = client.get("/api/v1/matches/1/canonical-metrics", headers=headers).json()
        reconciliation = client.get("/api/v1/matches/1/canonical-reconciliation", headers=headers).json()
        assert metrics["eligibility"]["eligible"] == 2
        assert metrics["coverage"]["eligible_events"] == 2
        assert metrics["metrics"]["shots"]["evidence"] == [{"event_id": event_id, "revision_id": 1}]
        assert reconciliation["official"] == {"snapshot_id": "pdf-1", "home_score": 2, "away_score": 0}
        assert reconciliation["discrepancies"][0]["discrepancy"] == -1
        revised = client.patch(f"/api/v1/canonical-events/{event_id}", json={**command, "note": "reviewed", "reason": "footage review"}, headers=headers)
        assert revised.status_code == 200 and revised.json()["revision"] == 2
        deactivated = client.delete(f"/api/v1/canonical-events/{event_id}?reason=duplicate", headers=headers)
        assert deactivated.status_code == 200 and deactivated.json()["active"] is False
        assert next(item for item in client.get("/api/v1/matches/1/canonical-events", headers=headers).json()
                    if item["id"] == event_id)["reason"] == "duplicate"
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def test_route_accepts_wizard_domain_outcomes_and_preserves_substitution_roles(tmp_path):
    client, engine, _ = canonical_client(tmp_path)
    headers = {"Authorization": f"Bearer {create_access_token({'sub': '1'})}"}
    try:
        for outcome in ("goal", "save", "miss", "woodwork", "blocked"):
            response = client.post("/api/v1/matches/1/canonical-events", headers=headers,
                                   json={"kind": "shot", "period": 1, "team_id": 1, "player_id": 10,
                                         "outcome": outcome, "evidence_state": "confirmed"})
            assert response.status_code == 201
        for outcome in ("seven_meter", "two_minute_exclusion", "yellow_card", "red_card", "blue_card"):
            response = client.post("/api/v1/matches/1/canonical-events", headers=headers,
                                   json={"kind": "foul_sanction", "period": 1, "team_id": 1,
                                         "outcome": outcome, "evidence_state": "confirmed"})
            assert response.status_code == 201
        for command in (
            {"kind": "goalkeeper_change", "period": 1, "team_id": 2, "player_id": 20, "outcome": "active", "evidence_state": "confirmed"},
            {"kind": "goalkeeper_change", "period": 1, "team_id": 2, "outcome": "unknown", "evidence_state": "confirmed"},
            {"kind": "lineup_change", "period": 1, "team_id": 1, "player_id": 11, "related_player_id": 10, "outcome": "substitution", "evidence_state": "confirmed"},
        ):
            assert client.post("/api/v1/matches/1/canonical-events", headers=headers, json=command).status_code == 201
        state = client.get("/api/v1/matches/1/canonical-state", headers=headers).json()
        assert state["player_states"] == {"10": "off", "11": "on"}
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def test_route_rejects_an_opposing_player_as_the_active_goalkeeper(tmp_path):
    client, engine, _ = canonical_client(tmp_path)
    headers = {"Authorization": f"Bearer {create_access_token({'sub': '1'})}"}
    try:
        rejected = client.post("/api/v1/matches/1/canonical-events", headers=headers,
                               json={"kind": "goalkeeper_change", "period": 1, "team_id": 2,
                                     "player_id": 10, "outcome": "active", "evidence_state": "confirmed"})

        assert rejected.status_code == 422
        assert "active goalkeeper must belong" in rejected.json()["detail"]
        assert client.get("/api/v1/matches/1/canonical-state", headers=headers).json()["active_goalkeepers"] == {}
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def test_revision_audits_prefilled_shot_correction_and_optional_opposing_goalkeeper(tmp_path):
    client, engine, factory = canonical_client(tmp_path)
    headers = {"Authorization": f"Bearer {create_access_token({'sub': '1'})}"}
    shot = {"kind": "shot", "period": 1, "team_id": 1, "player_id": 10, "related_player_id": 11,
            "goalkeeper_id": 20, "outcome": "goal", "evidence_state": "confirmed",
            "evidence": [{"kind": "video", "reference": "https://youtu.be/abcdefghijk", "video_source_id": 4,
                          "video_anchor_seconds": 33, "uncertainty": []}]}
    try:
        created = client.post("/api/v1/matches/1/canonical-events", json=shot, headers=headers)
        assert created.status_code == 201
        event_id = created.json()["id"]
        revised = client.patch(f"/api/v1/canonical-events/{event_id}", json={**shot, "outcome": "save", "note": "corregido en video", "reason": "Revisión de evidencia"}, headers=headers)
        assert revised.status_code == 200
        assert revised.json()["revision"] == 2
        assert revised.json()["payload"]["player_id"] == 10
        assert revised.json()["payload"]["related_player_id"] == 11
        assert revised.json()["payload"]["goalkeeper_id"] == 20
        db = factory()
        event = db.get(CanonicalEvent, event_id)
        assert [revision.reason for revision in event.revisions] == ["created", "Revisión de evidencia"]
        assert event.revisions[-1].payload["outcome"] == "save"
        db.close()
        invalid = client.patch(f"/api/v1/canonical-events/{event_id}", json={**shot, "goalkeeper_id": 10, "reason": "arquero propio"}, headers=headers)
        assert invalid.status_code == 422
        assert "opposing" in invalid.json()["detail"]
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def test_write_validation_rejects_invalid_outcomes_before_persistence_and_keeps_valid_shots(tmp_path):
    client, engine, factory = canonical_client(tmp_path)
    headers = {"Authorization": f"Bearer {create_access_token({'sub': '1'})}"}
    try:
        invalid = {"kind": "shot", "period": 1, "team_id": 1, "player_id": 10,
                   "outcome": "goal_or_save", "evidence_state": "confirmed"}
        rejected = client.post("/api/v1/matches/1/canonical-events", json=invalid, headers=headers)
        assert rejected.status_code == 422
        assert "terminal result" in rejected.json()["detail"]
        db = factory()
        assert db.query(CanonicalEvent).count() == db.query(CanonicalEventRevision).count() == 1
        db.close()
        metrics = client.get("/api/v1/matches/1/canonical-metrics", headers=headers).json()
        assert "shots" not in metrics["metrics"]

        for outcome in ("goal", "save", "miss", "woodwork", "blocked"):
            response = client.post("/api/v1/matches/1/canonical-events", headers=headers,
                                   json={**invalid, "outcome": outcome})
            assert response.status_code == 201
        assert client.get("/api/v1/matches/1/canonical-metrics", headers=headers).json()["metrics"]["shots"]["count"] == 5
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def test_write_validation_rejects_second_kickoff_and_invalid_revision_without_writing(tmp_path):
    client, engine, factory = canonical_client(tmp_path)
    headers = {"Authorization": f"Bearer {create_access_token({'sub': '1'})}"}
    shot = {"kind": "shot", "period": 1, "team_id": 1, "player_id": 10,
            "outcome": "goal", "evidence_state": "confirmed"}
    try:
        second_kickoff = client.post("/api/v1/matches/1/canonical-events", json=kickoff_command(), headers=headers)
        assert second_kickoff.status_code == 409
        assert second_kickoff.json()["detail"] == "a possession is already open"
        created = client.post("/api/v1/matches/1/canonical-events", json=shot, headers=headers).json()
        rejected = client.patch(f"/api/v1/canonical-events/{created['id']}", headers=headers,
                                json={**shot, "outcome": "not_a_shot_result", "reason": "invalid correction"})
        assert rejected.status_code == 422
        db = factory()
        event = db.get(CanonicalEvent, created["id"])
        assert len(event.revisions) == 1
        db.close()
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def test_generic_events_require_an_active_verified_zero_kickoff_for_their_period(tmp_path):
    client, engine, factory = canonical_client(tmp_path)
    headers = {"Authorization": f"Bearer {create_access_token({'sub': '1'})}"}
    generic = {"kind": "shot", "period": 1, "team_id": 1, "player_id": 10, "outcome": "goal", "evidence_state": "confirmed"}
    kickoff = {"kind": "other", "period": 1, "regulation_seconds": None, "clock_unverified": True,
               "team_id": 1, "outcome": "kickoff", "evidence_state": "confirmed",
               "evidence": [{"kind": "video", "reference": "https://youtu.be/abcdefghijk", "video_source_id": 4,
                             "video_anchor_seconds": 17, "uncertainty": []}]}
    try:
        db = factory()
        db.query(CanonicalEventRevision).delete()
        db.query(CanonicalEvent).delete()
        db.commit()
        db.close()
        assert client.post("/api/v1/matches/1/canonical-events", json=generic, headers=headers).status_code == 422
        created = client.post("/api/v1/matches/1/canonical-events", json=kickoff, headers=headers)
        assert created.status_code == 201
        assert client.post("/api/v1/matches/1/canonical-events", json=generic, headers=headers).status_code == 422
        calibrated = client.patch(f"/api/v1/canonical-events/{created.json()['id']}", headers=headers,
                                  json={**kickoff, "regulation_seconds": 0, "clock_unverified": False,
                                        "reason": "official kickoff calibration"})
        assert calibrated.status_code == 200
        generic_created = client.post("/api/v1/matches/1/canonical-events", json=generic, headers=headers)
        assert generic_created.status_code == 201
        assert client.delete(f"/api/v1/canonical-events/{created.json()['id']}?reason=incorrect", headers=headers).status_code == 422
        assert client.post("/api/v1/matches/1/canonical-events", json={**generic, "period": 2}, headers=headers).status_code == 422
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def test_period_two_kickoff_starts_its_own_possession_projection(tmp_path):
    client, engine, _ = canonical_client(tmp_path)
    headers = {"Authorization": f"Bearer {create_access_token({'sub': '1'})}"}
    try:
        response = client.post("/api/v1/matches/1/canonical-events", json=kickoff_command(period=2, team_id=2), headers=headers)
        assert response.status_code == 201
        state = client.get("/api/v1/matches/1/canonical-state", headers=headers)
        assert state.status_code == 200
        assert state.json()["possession"] == {"team_id": 2, "start_basis": f"kickoff:{response.json()['id']}", "terminal_basis": None, "unresolved": False}
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def test_revision_moving_period_cannot_close_a_possession_in_the_wrong_period(tmp_path):
    client, engine, factory = canonical_client(tmp_path)
    headers = {"Authorization": f"Bearer {create_access_token({'sub': '1'})}"}
    shot = {"kind": "shot", "period": 1, "team_id": 1, "player_id": 10, "outcome": "goal", "evidence_state": "confirmed"}
    try:
        closing = client.post("/api/v1/matches/1/canonical-events", json=shot, headers=headers).json()
        later_kickoff = client.post("/api/v1/matches/1/canonical-events", json={**kickoff_command(), "team_id": 2}, headers=headers)
        assert later_kickoff.status_code == 201
        assert client.post("/api/v1/matches/1/canonical-events", json=kickoff_command(period=2, team_id=2), headers=headers).status_code == 201
        rejected = client.patch(f"/api/v1/canonical-events/{closing['id']}", headers=headers,
                                json={**shot, "period": 2, "reason": "wrong half"})
        assert rejected.status_code == 409
        db = factory()
        assert db.get(CanonicalEvent, closing["id"]).revisions[-1].revision == 1
        db.close()
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def test_deactivating_a_possession_closing_event_rejects_dependent_later_kickoff(tmp_path):
    client, engine, factory = canonical_client(tmp_path)
    headers = {"Authorization": f"Bearer {create_access_token({'sub': '1'})}"}
    shot = {"kind": "shot", "period": 1, "team_id": 1, "player_id": 10, "outcome": "goal", "evidence_state": "confirmed"}
    try:
        closing = client.post("/api/v1/matches/1/canonical-events", json=shot, headers=headers).json()
        assert client.post("/api/v1/matches/1/canonical-events", json={**kickoff_command(), "team_id": 2}, headers=headers).status_code == 201
        rejected = client.delete(f"/api/v1/canonical-events/{closing['id']}?reason=incorrect", headers=headers)
        assert rejected.status_code == 409
        db = factory()
        assert db.get(CanonicalEvent, closing["id"]).revisions[-1].payload.get("active", True) is True
        db.close()
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def test_route_maps_concurrent_canonical_write_conflicts_to_409(tmp_path, monkeypatch):
    client, engine, _ = canonical_client(tmp_path)
    headers = {"Authorization": f"Bearer {create_access_token({'sub': '1'})}"}
    try:
        def conflict(*_args, **_kwargs):
            raise canonical_service.CanonicalWriteConflictError("concurrent canonical write; retry the command")

        monkeypatch.setattr(canonical_service, "create_event", conflict)
        response = client.post("/api/v1/matches/1/canonical-events", headers=headers,
                               json={"kind": "shot", "period": 1, "team_id": 1, "player_id": 10,
                                     "outcome": "goal", "evidence_state": "confirmed"})
        assert response.status_code == 409
        assert response.json()["detail"] == "concurrent canonical write; retry the command"
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def test_revising_the_only_calibrated_kickoff_to_a_generic_event_is_rejected(tmp_path):
    client, engine, _ = canonical_client(tmp_path)
    headers = {"Authorization": f"Bearer {create_access_token({'sub': '1'})}"}
    generic = {"kind": "shot", "period": 1, "team_id": 1, "player_id": 10,
               "outcome": "goal", "evidence_state": "confirmed", "reason": "recategorized"}
    try:
        kickoff = client.get("/api/v1/matches/1/canonical-events", headers=headers).json()[0]
        response = client.patch(f"/api/v1/canonical-events/{kickoff['id']}", json=generic, headers=headers)
        assert response.status_code == 422
        assert "calibrated kickoff" in response.json()["detail"]
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def test_kickoff_requires_match_team_and_usable_video_provenance(tmp_path):
    client, engine, _ = canonical_client(tmp_path)
    headers = {"Authorization": f"Bearer {create_access_token({'sub': '1'})}"}
    kickoff = {"kind": "other", "period": 2, "team_id": 1, "outcome": "kickoff", "evidence_state": "confirmed",
               "evidence": [{"kind": "video", "reference": "https://youtu.be/abcdefghijk", "video_source_id": 4,
                             "video_anchor_seconds": 17, "uncertainty": []}]}
    try:
        assert client.post("/api/v1/matches/1/canonical-events", json={**kickoff, "team_id": None}, headers=headers).status_code == 422
        assert client.post("/api/v1/matches/1/canonical-events", json={**kickoff, "team_id": 99}, headers=headers).status_code == 422
        assert client.post("/api/v1/matches/1/canonical-events", json={**kickoff, "evidence": []}, headers=headers).status_code == 422
        assert client.post("/api/v1/matches/1/canonical-events", json={**kickoff, "evidence": [{"kind": "video", "reference": " ", "video_source_id": 4, "video_anchor_seconds": 17}]}, headers=headers).status_code == 422
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def test_roster_listed_player_is_accepted_without_lineup_substitution_or_goalkeeper_context(tmp_path):
    client, engine, _ = canonical_client(tmp_path)
    headers = {"Authorization": f"Bearer {create_access_token({'sub': '1'})}"}
    command = {"kind": "shot", "period": 1, "team_id": 1, "player_id": 10, "outcome": "miss", "evidence_state": "ambiguous"}
    try:
        # The fixture registers player 10 only in MatchSquad: it creates no lineup,
        # substitution, or active-goalkeeper event before this observed capture.
        response = client.post("/api/v1/matches/1/canonical-events", json=command, headers=headers)
        assert response.status_code == 201
        assert response.json()["payload"]["player_id"] == 10
        assert response.json()["payload"]["roster_source"] == "match_squad"
        assert client.get("/api/v1/matches/1/canonical-state", headers=headers).json()["active_goalkeepers"] == {}
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def test_player_projection_replays_keeper_context_and_discloses_unknowns(tmp_path):
    client, engine, _ = canonical_client(tmp_path)
    headers = {"Authorization": f"Bearer {create_access_token({'sub': '1'})}"}
    try:
        commands = [
            {"kind": "goalkeeper_change", "period": 1, "regulation_seconds": 1, "team_id": 2, "player_id": 20, "outcome": "active", "evidence_state": "confirmed"},
            {"kind": "lineup_change", "period": 1, "regulation_seconds": 2, "team_id": 2, "player_id": 20, "outcome": "on", "evidence_state": "confirmed"},
            {"kind": "shot", "period": 1, "regulation_seconds": 3, "team_id": 1, "player_id": 10, "outcome": "goal", "shot_zone": 7, "evidence_state": "confirmed"},
            {"kind": "goalkeeper_change", "period": 1, "regulation_seconds": 4, "team_id": 2, "outcome": "unknown", "evidence_state": "confirmed"},
            {"kind": "shot", "period": 1, "team_id": 1, "player_id": 10, "outcome": "save", "clock_unverified": True, "evidence_state": "confirmed"},
        ]
        for command in commands:
            assert client.post("/api/v1/matches/1/canonical-events", json=command, headers=headers).status_code == 201
        response = client.get("/api/v1/matches/1/canonical-player-projection?player_id=20&from_regulation_seconds=0&to_regulation_seconds=100", headers=headers)
        assert response.status_code == 200
        projection = response.json()
        assert projection["metrics"]["goals_conceded"] == 1
        assert projection["shot_map"]["zones"]["7"] == 1
        assert projection["participation"]["on"] == 1
        assert projection["shot_map"]["clock_unverified"] == 1
        unverified_evidence = next(item for item in projection["evidence"] if item.get("bucket") == "clock_unverified")
        assert {"id", "revision"} <= set(unverified_evidence)
        assert projection["unfiltered_context"]["canonical_metrics"]
        assert client.post("/api/v1/matches/1/canonical-events", json={"kind": "other", "period": 1, "shot_zone": 1, "evidence_state": "confirmed"}, headers=headers).status_code == 422
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def test_player_projection_accounts_for_unknown_missing_zone_excluded_and_unverified_shots(tmp_path):
    client, engine, factory = canonical_client(tmp_path)
    headers = {"Authorization": f"Bearer {create_access_token({'sub': '1'})}"}
    try:
        db = factory()
        db.add(VideoSource(id=8, match_id=1, original_url="https://youtube.test/watch?v=xyz", provider="youtube", provider_video_id="xyz", availability_state="ready"))
        db.commit()
        db.close()
        commands = [
            {"kind": "goalkeeper_change", "period": 1, "regulation_seconds": 1, "team_id": 2, "player_id": 20, "outcome": "active", "evidence_state": "confirmed"},
            {"kind": "shot", "period": 1, "regulation_seconds": 2, "team_id": 1, "player_id": 10, "outcome": "save", "shot_zone": 1, "evidence_state": "confirmed"},
            {"kind": "shot", "period": 1, "regulation_seconds": 3, "team_id": 1, "player_id": 10, "outcome": "goal", "evidence_state": "confirmed"},
            {"kind": "goalkeeper_change", "period": 1, "regulation_seconds": 4, "team_id": 2, "outcome": "unknown", "evidence_state": "confirmed"},
            {"kind": "shot", "period": 1, "regulation_seconds": 5, "team_id": 1, "player_id": 10, "outcome": "goal", "evidence_state": "confirmed"},
            {"kind": "shot", "period": 1, "team_id": 1, "player_id": 10, "outcome": "save", "clock_unverified": True, "evidence_state": "confirmed", "evidence": [{"kind": "video", "reference": "anchor", "video_source_id": 8, "video_anchor_seconds": 20, "uncertainty": []}]},
            {"kind": "shot", "period": 1, "regulation_seconds": 6, "team_id": 1, "player_id": 10, "outcome": "miss", "evidence_state": "confirmed"},
        ]
        for command in commands:
            assert client.post("/api/v1/matches/1/canonical-events", json=command, headers=headers).status_code == 201
        projection = client.get("/api/v1/matches/1/canonical-player-projection?player_id=20&from_regulation_seconds=0&to_regulation_seconds=100", headers=headers).json()
        assert projection["metrics"]["save_rate"] == {"numerator": 1, "denominator": 2, "value": 0.5}
        assert projection["shot_map"]["recorded"] == 1
        assert projection["shot_map"]["missing_zone"] == 1
        assert projection["shot_map"]["goalkeeper_unknown"] == projection["shot_map"]["unknown"] == 1
        assert projection["shot_map"]["clock_unverified"] == 1
        assert projection["shot_map"]["excluded"] >= 2
        assert all(item["payload"]["outcome"] in {"save", "goal"} for item in projection["evidence"] if item.get("bucket") in {"goalkeeper_unknown", "clock_unverified"})
        assert next(item for item in projection["evidence"] if item.get("bucket") == "clock_unverified")["evidence"]
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def test_player_projection_rejects_invalid_filters(tmp_path):
    client, engine, _ = canonical_client(tmp_path)
    headers = {"Authorization": f"Bearer {create_access_token({'sub': '1'})}"}
    try:
        assert client.get("/api/v1/matches/1/canonical-player-projection?player_id=999", headers=headers).status_code == 422
        assert client.get("/api/v1/matches/1/canonical-player-projection?player_id=20&team_id=999", headers=headers).status_code == 422
        assert client.get("/api/v1/matches/1/canonical-player-projection?player_id=20&from_regulation_seconds=10&to_regulation_seconds=1", headers=headers).status_code == 422
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def test_canonical_metrics_exclude_unknown_player_and_unresolved_possession_claims(tmp_path):
    client, engine, _ = canonical_client(tmp_path)
    headers = {"Authorization": f"Bearer {create_access_token({'sub': '1'})}"}
    try:
        for command in (
            {"kind": "turnover", "period": 1, "team_id": 1, "outcome": "unresolved_loss", "evidence_state": "confirmed", "uncertainty": ["responsibility_unknown"]},
            {"kind": "shot", "period": 1, "team_id": 1, "outcome": "goal", "evidence_state": "confirmed"},
        ):
            assert client.post("/api/v1/matches/1/canonical-events", json=command, headers=headers).status_code == 201
        metrics = client.get("/api/v1/matches/1/canonical-metrics", headers=headers).json()
        assert "player:10:shots" not in metrics["metrics"]
        assert metrics["eligibility"]["unresolved"] == 1
        assert metrics["metrics"]["possessions"]["unknown"] == 1
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def test_revision_evidence_is_distinct_and_foreign_provenance_is_rejected(tmp_path):
    client, engine, factory = canonical_client(tmp_path)
    headers = {"Authorization": f"Bearer {create_access_token({'sub': '1'})}"}
    command = {"kind": "shot", "period": 1, "team_id": 1, "player_id": 10, "outcome": "goal", "evidence_state": "confirmed",
               "evidence": [{"kind": "pdf", "reference": "sheet.pdf#page1", "official_snapshot_id": "pdf-1"}]}
    try:
        created = client.post("/api/v1/matches/1/canonical-events", json=command, headers=headers)
        assert created.status_code == 201
        first = created.json()["evidence"]
        assert first[0]["kind"] == "pdf" and first[0]["official_snapshot_id"] == "pdf-1"
        revised = client.patch(f"/api/v1/canonical-events/{created.json()['id']}", headers=headers,
                               json={**command, "note": "reviewed",
                                     "evidence": [{"kind": "unavailable", "uncertainty": ["recording_missing"]}],
                                     "reason": "footage review"})
        assert revised.status_code == 200
        second = revised.json()["evidence"]
        assert second[0]["kind"] == "unavailable" and second[0]["reference"] is None
        assert {item["id"] for item in first}.isdisjoint({item["id"] for item in second})
        wrong_pdf = client.post("/api/v1/matches/1/canonical-events", headers=headers,
                                json={**command, "evidence": [{"kind": "pdf", "reference": "x", "official_snapshot_id": "nope"}]})
        assert wrong_pdf.status_code == 422
        wrong_video = client.post("/api/v1/matches/1/canonical-events", headers=headers,
                                  json={**command, "evidence": [{"kind": "video", "reference": "x", "video_source_id": 999}]})
        assert wrong_video.status_code == 422
        wrong_fixture = client.post("/api/v1/matches/1/canonical-events", headers=headers,
                                    json={**command, "evidence": [{"kind": "fixture", "reference": "x", "scheduled_match_id": 999}]})
        assert wrong_fixture.status_code == 422
        missing_reference = client.post("/api/v1/matches/1/canonical-events", headers=headers,
                                        json={**command, "evidence": [{"kind": "video"}]})
        assert missing_reference.status_code == 422
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def test_repeated_video_anchor_revisions_retain_latest_video_provenance(tmp_path):
    client, engine, factory = canonical_client(tmp_path)
    headers = {"Authorization": f"Bearer {create_access_token({'sub': '1'})}"}
    command = {"kind": "shot", "period": 1, "team_id": 1, "player_id": 10, "outcome": "goal", "shot_zone": 4, "evidence_state": "confirmed"}
    try:
        db = factory()
        db.add(VideoSource(id=7, match_id=1, original_url="https://youtube.test/watch?v=abc", provider="youtube", provider_video_id="abc", availability_state="ready"))
        db.commit()
        db.close()
        evidence = [{"kind": "video", "reference": "https://youtube.test/watch?v=abc", "video_source_id": 7, "video_anchor_seconds": 50, "uncertainty": ["camera_angle"]}]
        created = client.post("/api/v1/matches/1/canonical-events", json={**command, "evidence": evidence}, headers=headers)
        assert created.status_code == 201
        first = client.patch(f"/api/v1/canonical-events/{created.json()['id']}", json={**command, "regulation_seconds": 60, "evidence": evidence, "reason": "first anchor recalibration"}, headers=headers)
        assert first.status_code == 200
        assert first.json()["evidence"][0]["video_source_id"] == 7
        assert first.json()["evidence"][0]["video_anchor_seconds"] == 50
        assert first.json()["evidence"][0]["uncertainty"] == ["camera_angle"]
        latest_evidence = [{key: value for key, value in item.items() if key != "id"} for item in first.json()["evidence"]]
        second = client.patch(f"/api/v1/canonical-events/{created.json()['id']}", json={**command, "regulation_seconds": 70, "evidence": latest_evidence, "reason": "second anchor recalibration"}, headers=headers)
        assert second.status_code == 200
        assert second.json()["revision"] == 3
        assert second.json()["payload"]["shot_zone"] == 4
        assert [{key: value for key, value in item.items() if key != "id"} for item in second.json()["evidence"]] == latest_evidence
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def test_metrics_exclude_unsupported_goalkeeper_and_possession_claims(tmp_path):
    client, engine, _ = canonical_client(tmp_path)
    headers = {"Authorization": f"Bearer {create_access_token({'sub': '1'})}"}
    try:
        created = client.post("/api/v1/matches/1/canonical-events", headers=headers,
                              json={"kind": "shot", "period": 1, "team_id": 1, "player_id": 10,
                                    "outcome": "save", "evidence_state": "confirmed"})
        assert created.status_code == 201
        metrics = client.get("/api/v1/matches/1/canonical-metrics", headers=headers).json()
        assert not any(name.startswith("goalkeeper:") for name in metrics["metrics"])
        assert all(not {"rate", "efficiency", "percentage"} & set(metric) for metric in metrics["metrics"].values())
        assert metrics["metrics"]["possessions"]["count"] == 1
        reconciliation = client.get("/api/v1/matches/1/canonical-reconciliation", headers=headers).json()
        assert reconciliation["discrepancies"][0]["analytical"] == 0
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def test_discipline_reconciliation_matches_official_cards_without_mutating_snapshot(tmp_path):
    client, engine, factory = canonical_client(tmp_path)
    headers = {"Authorization": f"Bearer {create_access_token({'sub': '1'})}"}
    try:
        db = factory()
        snapshot = db.get(OfficialSnapshot, "pdf-1")
        db.add_all([
            OfficialSnapshotPlayer(snapshot_id="pdf-1", side="home", player_id=None, name="Home A", jersey_number=4,
                                   official_goals=0, official_yellow=1, official_2min=1, official_red=0, official_blue=0),
            OfficialSnapshotPlayer(snapshot_id="pdf-1", side="away", player_id=None, name="Away B", jersey_number=7,
                                   official_goals=0, official_yellow=0, official_2min=0, official_red=0, official_blue=0),
        ])
        before_scores = (snapshot.home_score, snapshot.away_score)
        db.commit()
        db.close()
        for outcome in ("yellow_card", "two_minute_exclusion"):
            assert client.post("/api/v1/matches/1/canonical-events", headers=headers,
                               json={"kind": "foul_sanction", "period": 1, "team_id": 1, "player_id": 10,
                                     "outcome": outcome, "evidence_state": "confirmed"}).status_code == 201
        assert client.post("/api/v1/matches/1/canonical-events", headers=headers,
                           json=kickoff_command(period=2, team_id=2)).status_code == 201
        assert client.post("/api/v1/matches/1/canonical-events", headers=headers,
                           json={"kind": "foul_sanction", "period": 2, "team_id": 2, "outcome": "yellow_card",
                                 "evidence_state": "confirmed"}).status_code == 201
        reconciliation = client.get("/api/v1/matches/1/canonical-reconciliation", headers=headers).json()
        home_discipline = next(item for item in reconciliation["discipline"] if item["side"] == "home")
        away_discipline = next(item for item in reconciliation["discipline"] if item["side"] == "away")
        assert home_discipline["status"] == "match"
        assert home_discipline["official"] == {"yellow": 1, "two_minute": 1, "red": 0}
        assert home_discipline["observed"]["two_minute"] == 1
        assert len(home_discipline["evidence"]) == 2
        assert away_discipline["status"] == "mismatch"
        db = factory()
        after_scores = (db.get(OfficialSnapshot, "pdf-1").home_score, db.get(OfficialSnapshot, "pdf-1").away_score)
        db.close()
        assert after_scores == before_scores
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def test_legacy_dry_run_never_mutates_sources_and_excludes_unreviewed_rows(tmp_path):
    client, engine, factory = canonical_client(tmp_path)
    headers = {"Authorization": f"Bearer {create_access_token({'sub': '1'})}"}
    try:
        before = factory()
        counts = [before.query(model).count() for model in (Event, AnalysisEvent, GoalkeeperShot)]
        before.close()
        mapped = client.get("/api/v1/matches/1/canonical-legacy-dry-run", headers=headers)
        assert mapped.status_code == 200
        assert {item["source_table"] for item in mapped.json()} == {"events", "analysis_events", "goalkeeper_shots"}
        assert all(not item["reviewed"] and not item["eligible"] for item in mapped.json())
        after = factory()
        assert [after.query(model).count() for model in (Event, AnalysisEvent, GoalkeeperShot)] == counts
        after.close()
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def test_cutover_blocks_every_legacy_writer_with_409(tmp_path):
    client, engine, factory = canonical_client(tmp_path)
    headers = {"Authorization": f"Bearer {create_access_token({'sub': '1'})}"}
    try:
        legacy_event = {"game_timestamp": 10.0, "team_action": "attack", "action_type": "Lanzamiento", "match_id": 1}
        assert client.post("/api/v1/matches/1/events", json=legacy_event, headers=headers).status_code == 409
        assert client.patch("/api/v1/analysis-events/1", json={"reason": "tweak"}, headers=headers).status_code == 409
        assert client.delete("/api/v1/matches/1/goalkeeper-shots/1", headers=headers).status_code == 409
        assert client.delete("/api/v1/matches/1/events/last", headers=headers).status_code == 409
        after = factory()
        assert [after.query(model).count() for model in (Event, AnalysisEvent, GoalkeeperShot)] == [1, 1, 1]
        after.close()
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def test_admin_can_roll_back_a_match_to_legacy_read_only_fallback(tmp_path):
    client, engine, factory = canonical_client(tmp_path)
    analyst = {"Authorization": f"Bearer {create_access_token({'sub': '1'})}"}
    admin = {"Authorization": f"Bearer {create_access_token({'sub': '2'})}"}
    command = {"kind": "shot", "period": 1, "team_id": 1, "player_id": 10, "outcome": "goal", "evidence_state": "confirmed"}
    try:
        assert client.put("/api/v1/matches/1/canonical-cutover", json={"enabled": False, "reason": "rollback sample"}, headers=analyst).status_code == 403
        response = client.put("/api/v1/matches/1/canonical-cutover", json={"enabled": False, "reason": "rollback sample"}, headers=admin)
        assert response.status_code == 200 and response.json()["canonical_analysis_enabled"] is False
        assert client.post("/api/v1/matches/1/canonical-events", json=command, headers=analyst).status_code == 409
        assert client.get("/api/v1/matches/1/canonical-events", headers=analyst).status_code == 409
        before = factory(); counts = [before.query(model).count() for model in (Event, AnalysisEvent, GoalkeeperShot)]; before.close()
        assert client.get("/api/v1/matches/1/canonical-legacy-dry-run", headers=analyst).status_code == 200
        after = factory(); assert [after.query(model).count() for model in (Event, AnalysisEvent, GoalkeeperShot)] == counts; after.close()
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def test_analyst_can_enable_a_confirmed_match_but_not_roll_it_back(tmp_path):
    client, engine, factory = canonical_client(tmp_path)
    analyst = {"Authorization": f"Bearer {create_access_token({'sub': '1'})}"}
    command = {"kind": "other", "period": 1, "outcome": "kickoff", "evidence_state": "confirmed"}
    try:
        db = factory()
        db.get(Match, 1).canonical_analysis_enabled = False
        db.commit()
        db.close()
        enabled = client.put("/api/v1/matches/1/canonical-cutover", json={"enabled": True, "reason": "analysis preparation started"}, headers=analyst)
        assert enabled.status_code == 200 and enabled.json()["canonical_analysis_enabled"] is True
        assert client.post("/api/v1/matches/1/canonical-events", json=command, headers=analyst).status_code == 422
        assert client.put("/api/v1/matches/1/canonical-cutover", json={"enabled": False, "reason": "rollback"}, headers=analyst).status_code == 403
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def test_canonical_enable_requires_a_confirmed_official_sheet(tmp_path):
    client, engine, factory = canonical_client(tmp_path)
    analyst = {"Authorization": f"Bearer {create_access_token({'sub': '1'})}"}
    try:
        db = factory()
        db.get(Match, 1).canonical_analysis_enabled = False
        db.get(OfficialSnapshot, "pdf-1").is_confirmed = False
        db.commit()
        db.close()
        response = client.put("/api/v1/matches/1/canonical-cutover", json={"enabled": True, "reason": "analysis preparation started"}, headers=analyst)
        assert response.status_code == 422
        assert response.json()["detail"] == "a confirmed official sheet is required before canonical analysis can start"
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def test_manual_cutover_requires_the_owner_or_an_admin_without_affecting_fixture_matches(tmp_path):
    client, engine, factory = canonical_client(tmp_path)
    owner = {"Authorization": f"Bearer {create_access_token({'sub': '1'})}"}
    other = {"Authorization": f"Bearer {create_access_token({'sub': '3'})}"}
    admin = {"Authorization": f"Bearer {create_access_token({'sub': '2'})}"}
    try:
        db = factory()
        match = db.get(Match, 1)
        match.origin = "manual"
        match.created_by_user_id = 1
        match.canonical_analysis_enabled = False
        db.commit()
        db.close()

        assert client.put("/api/v1/matches/1/canonical-cutover", json={"enabled": True, "reason": "prepare"}, headers=other).status_code == 403
        assert client.put("/api/v1/matches/1/canonical-cutover", json={"enabled": True, "reason": "prepare"}, headers=owner).status_code == 200
        db = factory(); db.get(Match, 1).canonical_analysis_enabled = False; db.commit(); db.close()
        assert client.put("/api/v1/matches/1/canonical-cutover", json={"enabled": True, "reason": "prepare"}, headers=admin).status_code == 200
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def test_last_incident_deletion_allows_pending_kickoff_retry_but_rejects_duplicates(tmp_path):
    client, engine, factory = canonical_client(tmp_path)
    analyst = {"Authorization": f"Bearer {create_access_token({'sub': '1'})}"}
    other = {"Authorization": f"Bearer {create_access_token({'sub': '2'})}"}
    pending = {**kickoff_command(), "regulation_seconds": None, "clock_unverified": True}
    try:
        db = factory(); db.query(CanonicalEventRevision).delete(); db.query(CanonicalEvent).delete(); db.commit(); db.close()
        created = client.post("/api/v1/matches/1/canonical-events", json=pending, headers=analyst)
        assert created.status_code == 201
        deleted = client.request("DELETE", "/api/v1/matches/1/canonical-events/last", json={"reason": "retry kickoff"}, headers=analyst)
        assert deleted.status_code == 200 and deleted.json()["active"] is False
        assert client.post("/api/v1/matches/1/canonical-events", json=pending, headers=analyst).status_code == 201
        assert client.post("/api/v1/matches/1/canonical-events", json={"kind": "other", "period": 1, "team_id": 1, "outcome": "kickoff", "evidence_state": "confirmed", "evidence": [{"kind": "video", "reference": "https://youtu.be/abcdefghijk", "video_source_id": 4, "video_anchor_seconds": 20, "uncertainty": []}]}, headers=other).status_code == 409
    finally:
        app.dependency_overrides.clear(); engine.dispose()


def test_reset_is_atomic_and_retains_historic_video_sources(tmp_path):
    client, engine, factory = canonical_client(tmp_path)
    analyst = {"Authorization": f"Bearer {create_access_token({'sub': '1'})}"}
    other = {"Authorization": f"Bearer {create_access_token({'sub': '2'})}"}
    try:
        db = factory()
        session = AnalysisSession(match_id=1, analyst_id=1, video_source_id=4, mode="video", video_position_seconds=21, clock_start_video_seconds=17, angle="wide", filters={"team": 1}, draft={"kind": "shot"}, queue=[{"id": 1}])
        session.anchors.append(TimeAnchor(analyst_id=1, period=1, video_seconds=17, regulation_seconds=0))
        session.time_segments.append(TimeSegment(analyst_id=1, period=1, video_start_seconds=17, video_end_seconds=27, regulation_start_seconds=0, regulation_end_seconds=10, coverage="playable", clock_unverified=False))
        db.add(session); db.commit(); db.close()
        reset = client.post("/api/v1/matches/1/canonical-analysis/reset", json={"reason": "restart my review"}, headers=analyst)
        assert reset.status_code == 200 and reset.json() == {"deactivated_events": 1, "session_reset": True}
        db = factory(); saved = db.query(AnalysisSession).filter_by(match_id=1, analyst_id=1).one()
        assert saved.video_source_id is None and saved.video_position_seconds is None and saved.clock_start_video_seconds is None
        assert saved.angle is None and saved.filters == saved.draft == {} and saved.queue == [] and saved.anchors == [] and saved.time_segments == []
        assert db.query(VideoSource).filter_by(id=4).one().original_url == "https://youtu.be/abcdefghijk"
        assert db.query(CanonicalEventRevision).filter_by(event_id=1).count() == 2
        db.close()

        assert client.post("/api/v1/matches/1/canonical-events", json={"kind": "shot", "period": 1, "team_id": 1, "player_id": 10, "outcome": "goal", "evidence_state": "confirmed"}, headers=other).status_code == 422
        db = factory(); kickoff = db.get(CanonicalEvent, 1); latest = max(kickoff.revisions, key=lambda revision: revision.revision); latest.payload = {**latest.payload, "active": True}; saved = db.query(AnalysisSession).filter_by(match_id=1, analyst_id=1).one(); saved.video_source_id = 4; saved.video_position_seconds = 30; saved.filters = {"kept": True}; db.commit(); db.close()
        assert client.post("/api/v1/matches/1/canonical-events", json={"kind": "shot", "period": 1, "team_id": 1, "player_id": 10, "outcome": "goal", "evidence_state": "confirmed"}, headers=other).status_code == 201
        blocked = client.post("/api/v1/matches/1/canonical-analysis/reset", json={"reason": "must stay atomic"}, headers=analyst)
        assert blocked.status_code == 422
        db = factory(); saved = db.query(AnalysisSession).filter_by(match_id=1, analyst_id=1).one(); assert saved.video_source_id == 4 and saved.video_position_seconds == 30 and saved.filters == {"kept": True}; assert max(db.get(CanonicalEvent, 1).revisions, key=lambda revision: revision.revision).payload["active"] is True; db.close()
    finally:
        app.dependency_overrides.clear(); engine.dispose()


def test_warnings_summary_is_authenticated_cutover_gated_and_traceable(tmp_path):
    client, engine, factory = canonical_client(tmp_path)
    headers = {"Authorization": f"Bearer {create_access_token({'sub': '1'})}"}
    try:
        assert client.get("/api/v1/matches/1/warnings-summary").status_code == 403
        db = factory()
        snapshot = db.get(OfficialSnapshot, "pdf-1")
        db.add_all([
            OfficialSnapshotPlayer(snapshot_id=snapshot.id, side="home", player_id=10, name="Shooter", jersey_number=10,
                                   official_goals=2, official_yellow=1, official_2min=1, official_red=0, official_blue=0),
            OfficialSnapshotPlayer(snapshot_id=snapshot.id, side="away", player_id=None, name="Official only", jersey_number=7,
                                   official_goals=0, official_yellow=0, official_2min=0, official_red=0, official_blue=0),
        ])
        before = (snapshot.home_score, snapshot.away_score)
        db.commit()
        db.close()
        eligible_goal = client.post("/api/v1/matches/1/canonical-events", headers=headers, json={
            "kind": "shot", "period": 1, "team_id": 1, "player_id": 10, "outcome": "goal", "evidence_state": "confirmed",
            "evidence": [{"kind": "pdf", "reference": "sheet.pdf#goal", "official_snapshot_id": "pdf-1"}],
        }).json()
        commands = [
            {"kind": "shot", "period": 1, "team_id": 1, "outcome": "goal", "evidence_state": "confirmed"},
            {"kind": "foul_sanction", "period": 1, "team_id": 1, "player_id": 10, "outcome": "yellow_card", "evidence_state": "confirmed"},
            {"kind": "foul_sanction", "period": 1, "team_id": 1, "player_id": 10, "outcome": "blue_card", "evidence_state": "confirmed"},
            {"kind": "shot", "period": 1, "team_id": 1, "player_id": 10, "outcome": "goal", "evidence_state": "confirmed", "fact_kind": "inference"},
            {"kind": "shot", "period": 1, "team_id": 1, "player_id": 10, "outcome": "goal", "evidence_state": "ambiguous"},
        ]
        for command in commands:
            assert client.post("/api/v1/matches/1/canonical-events", headers=headers, json=command).status_code == 201
        inactive = client.post("/api/v1/matches/1/canonical-events", headers=headers, json={
            "kind": "shot", "period": 1, "team_id": 1, "player_id": 10, "outcome": "goal", "evidence_state": "confirmed",
        }).json()
        assert client.delete(f"/api/v1/canonical-events/{inactive['id']}?reason=duplicate", headers=headers).status_code == 200

        response = client.get("/api/v1/matches/1/warnings-summary", headers=headers)
        assert response.status_code == 200
        summary = response.json()
        player = next(row for row in summary["players"] if row["player"]["id"] == 10)
        assert player["metrics"]["goals"]["status"] == "missing_in_canonical"
        assert player["metrics"]["yellow"]["status"] == "exact"
        assert player["metrics"]["two_minute"]["status"] == "missing_in_canonical"
        assert player["metrics"]["blue"]["status"] == "missing_in_official"
        assert player["metrics"]["goals"]["canonical_event_ids"] == [eligible_goal["id"]]
        assert player["metrics"]["goals"]["evidence_ids"] == [eligible_goal["evidence"][0]["id"]]
        assert next(row for row in summary["players"] if row["player"]["id"] is None)["metrics"]["goals"]["status"] == "missing_in_canonical"
        assert summary["match_totals"]["metrics"]["goals"]["status"] == "exact"
        assert {item["check"] for item in summary["limitations"]} == {"goal_timestamps", "card_timestamps", "goalkeeper_substitutions"}
        assert all(item["status"] == "not_comparable" and item["reason"] for item in summary["limitations"])
        db = factory()
        assert (db.get(OfficialSnapshot, "pdf-1").home_score, db.get(OfficialSnapshot, "pdf-1").away_score) == before
        db.close()

        db = factory()
        db.get(Match, 1).canonical_analysis_enabled = False
        db.commit()
        db.close()
        assert client.get("/api/v1/matches/1/warnings-summary", headers=headers).status_code == 409
    finally:
        app.dependency_overrides.clear()
        engine.dispose()
