import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import Match, User, VideoSource
from app.schemas import AnalysisSession as AnalysisSessionRead, AnalysisSessionUpdate, TimeAnchorInput, TimeSegmentInput, VideoSourceInput
from app.services.analysis_session_service import AnalysisSessionService


def test_session_recovers_source_position_and_period_anchors_without_touching_events():
    engine = create_engine("sqlite://")
    session = sessionmaker(bind=engine)()
    Base.metadata.create_all(engine)
    analyst = User(id=1, email="analyst@example.com", hashed_password="x", full_name="Analyst")
    session.add_all([analyst, Match(id=1)])
    session.commit()

    saved = AnalysisSessionService.save(session, 1, AnalysisSessionUpdate(mode="video", source=VideoSourceInput(url="https://youtu.be/abcdefghijk", availability_state="unavailable"), video_position_seconds=94.5, angle="broadcast", filters={"period": 2}, draft={"note": "review later"}, queue=[{"event_id": 7}], anchors=[TimeAnchorInput(period=1, video_seconds=12, regulation_seconds=4, uncertainty_seconds=1), TimeAnchorInput(period=2, video_seconds=1900, regulation_seconds=3)], time_segments=[TimeSegmentInput(period=1, video_start_seconds=12, video_end_seconds=70, regulation_start_seconds=4, regulation_end_seconds=62, uncertainty_seconds=1, coverage="playable"), TimeSegmentInput(period=1, video_start_seconds=70, video_end_seconds=80, coverage="cut", clock_unverified=True), TimeSegmentInput(period=1, video_start_seconds=80, video_end_seconds=90, coverage="offset", clock_unverified=True), TimeSegmentInput(period=1, video_start_seconds=90, video_end_seconds=105, coverage="replay", clock_unverified=True), TimeSegmentInput(period=1, video_start_seconds=105, video_end_seconds=115, coverage="pause", clock_unverified=True), TimeSegmentInput(period=1, video_start_seconds=115, video_end_seconds=175, regulation_start_seconds=62, regulation_end_seconds=122, uncertainty_seconds=3, coverage="playable"), TimeSegmentInput(period=2, video_start_seconds=1900, video_end_seconds=1920, coverage="halftime", clock_unverified=True), TimeSegmentInput(period=3, video_start_seconds=1920, video_end_seconds=1980, regulation_start_seconds=0, regulation_end_seconds=60, uncertainty_seconds=1, coverage="playable")]), analyst)
    recovered = AnalysisSessionService.get(session, 1, analyst)

    assert recovered.id == saved.id
    assert recovered.video_source.provider_video_id == "abcdefghijk"
    assert recovered.video_source.availability_state == "unavailable"
    assert recovered.video_position_seconds == 94.5
    assert recovered.profile == "complete"
    assert recovered.clock_start_video_seconds is None
    assert [(anchor.period, anchor.regulation_seconds) for anchor in recovered.anchors] == [(1, 4), (2, 3)]
    assert [(segment.period, segment.coverage, segment.clock_unverified) for segment in recovered.time_segments] == [(1, "playable", False), (1, "cut", True), (1, "offset", True), (1, "replay", True), (1, "pause", True), (1, "playable", False), (2, "halftime", True), (3, "playable", False)]
    assert AnalysisSessionRead.model_validate(recovered, from_attributes=True).source.provider_video_id == "abcdefghijk"
    assert session.get(Match, 1).analysis_events == []
    engine.dispose()


def test_session_rejects_unsupported_video_source():
    with pytest.raises(ValueError, match="supported YouTube"):
        AnalysisSessionService._source_identity("https://example.com/video")


def test_direct_stale_replacement_payload_cannot_persist_cross_source_calibration():
    engine = create_engine("sqlite://")
    session = sessionmaker(bind=engine)()
    Base.metadata.create_all(engine)
    analyst = User(id=1, email="analyst@example.com", hashed_password="x", full_name="Analyst")
    session.add_all([analyst, Match(id=1)])
    session.commit()

    saved = AnalysisSessionService.save(session, 1, AnalysisSessionUpdate(source=VideoSourceInput(url="https://youtu.be/abcdefghijk"), video_position_seconds=94.5, clock_start_video_seconds=12, anchors=[TimeAnchorInput(period=1, video_seconds=12, regulation_seconds=0)], time_segments=[TimeSegmentInput(period=1, video_start_seconds=12, video_end_seconds=72, regulation_start_seconds=0, regulation_end_seconds=60, coverage="playable")]), analyst)
    saved_source_id = saved.video_source.id
    replaced = AnalysisSessionService.save(session, 1, AnalysisSessionUpdate(source=VideoSourceInput(url="https://www.youtube-nocookie.com/embed/zyxwvutsrq"), video_position_seconds=999, clock_start_video_seconds=999, anchors=[TimeAnchorInput(period=1, video_seconds=999, regulation_seconds=0)], time_segments=[TimeSegmentInput(period=1, video_start_seconds=999, video_end_seconds=1059, regulation_start_seconds=0, regulation_end_seconds=60, coverage="playable")]), analyst)

    assert replaced.video_source.id != saved_source_id
    assert replaced.video_source.provider == "youtube"
    assert replaced.video_source.provider_video_id == "zyxwvutsrq"
    assert replaced.video_position_seconds is None
    assert replaced.clock_start_video_seconds is None
    assert replaced.anchors == []
    assert replaced.time_segments == []
    engine.dispose()


def test_same_source_checkpoint_preserves_video_source_identity_and_calibration():
    engine = create_engine("sqlite://")
    session = sessionmaker(bind=engine)()
    Base.metadata.create_all(engine)
    analyst = User(id=1, email="analyst@example.com", hashed_password="x", full_name="Analyst")
    session.add_all([analyst, Match(id=1)])
    session.commit()

    saved = AnalysisSessionService.save(session, 1, AnalysisSessionUpdate(source=VideoSourceInput(url="https://youtu.be/abcdefghijk"), video_position_seconds=12, clock_start_video_seconds=10, anchors=[TimeAnchorInput(period=1, video_seconds=10, regulation_seconds=0)], time_segments=[TimeSegmentInput(period=1, video_start_seconds=10, video_end_seconds=70, regulation_start_seconds=0, regulation_end_seconds=60, coverage="playable")]), analyst)
    checkpointed = AnalysisSessionService.save(session, 1, AnalysisSessionUpdate(source=VideoSourceInput(url="https://www.youtube.com/watch?v=abcdefghijk", availability_state="ready"), video_position_seconds=42, clock_start_video_seconds=10, anchors=[TimeAnchorInput(period=1, video_seconds=10, regulation_seconds=0)], time_segments=[TimeSegmentInput(period=1, video_start_seconds=10, video_end_seconds=70, regulation_start_seconds=0, regulation_end_seconds=60, coverage="playable")]), analyst)

    assert checkpointed.video_source.id == saved.video_source.id
    assert checkpointed.video_source.availability_state == "ready"
    assert checkpointed.video_position_seconds == 42
    assert checkpointed.clock_start_video_seconds == 10
    assert len(checkpointed.anchors) == len(checkpointed.time_segments) == 1
    assert session.query(VideoSource).count() == 1
    engine.dispose()


def test_session_reuses_an_existing_logical_source_from_another_session():
    engine = create_engine("sqlite://")
    session = sessionmaker(bind=engine)()
    Base.metadata.create_all(engine)
    analyst = User(id=1, email="analyst@example.com", hashed_password="x", full_name="Analyst")
    existing = VideoSource(id=4, match_id=1, original_url="https://youtu.be/abcdefghijk", provider="youtube", provider_video_id="abcdefghijk", availability_state="ready")
    session.add_all([analyst, Match(id=1), existing])
    session.commit()

    saved = AnalysisSessionService.save(session, 1, AnalysisSessionUpdate(
        source=VideoSourceInput(url="https://www.youtube.com/watch?v=abcdefghijk"),
        clock_start_video_seconds=10,
        anchors=[TimeAnchorInput(period=1, video_seconds=10, regulation_seconds=0)],
    ), analyst)

    assert saved.video_source_id == 4
    assert saved.clock_start_video_seconds == 10
    assert session.query(VideoSource).count() == 1
    engine.dispose()


def test_invalid_source_replacement_preserves_the_authenticated_session_and_evidence():
    engine = create_engine("sqlite://")
    session = sessionmaker(bind=engine)()
    Base.metadata.create_all(engine)
    analyst = User(id=1, email="analyst@example.com", hashed_password="x", full_name="Analyst")
    session.add_all([analyst, Match(id=1)])
    session.commit()

    saved = AnalysisSessionService.save(session, 1, AnalysisSessionUpdate(mode="video", source=VideoSourceInput(url="https://youtu.be/abcdefghijk"), video_position_seconds=94.5, draft={"evidence_state": "no_visible"}), analyst)

    with pytest.raises(ValueError, match="supported YouTube"):
        AnalysisSessionService.save(session, 1, AnalysisSessionUpdate(mode="live", source=VideoSourceInput(url="https://example.com/video"), video_position_seconds=0, draft={"evidence_state": "ambiguous"}), analyst)

    recovered = AnalysisSessionService.get(session, 1, analyst)
    assert recovered.id == saved.id
    assert recovered.video_source.provider_video_id == "abcdefghijk"
    assert recovered.video_position_seconds == 94.5
    assert recovered.draft == {"evidence_state": "no_visible"}
    engine.dispose()


def test_non_playable_segments_cannot_supply_or_invent_match_time():
    with pytest.raises(ValueError, match="clock-unverified"):
        TimeSegmentInput(period=1, video_start_seconds=40, video_end_seconds=50, regulation_start_seconds=30, regulation_end_seconds=40, coverage="cut")
    with pytest.raises(ValueError, match="increasing regulation range"):
        TimeSegmentInput(period=1, video_start_seconds=40, video_end_seconds=50, coverage="playable")
