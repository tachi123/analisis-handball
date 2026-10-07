import re
from urllib.parse import parse_qs, urlparse

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from ..models import AnalysisSession, TimeAnchor, TimeSegment, User, VideoSource
from ..schemas import AnalysisSessionUpdate


class AnalysisSessionService:
    @staticmethod
    def _source_identity(url):
        parsed = urlparse(url)
        host = parsed.netloc.lower().removeprefix("www.")
        if parsed.scheme not in {"http", "https"} or host not in {"youtube.com", "youtu.be", "youtube-nocookie.com"}:
            raise ValueError("A supported YouTube URL is required")
        video_id = parse_qs(parsed.query).get("v", [None])[0] if host == "youtube.com" else None
        if host == "youtu.be":
            video_id = parsed.path.strip("/").split("/")[0]
        elif video_id is None:
            parts = parsed.path.strip("/").split("/")
            video_id = parts[1] if len(parts) == 2 and parts[0] in {"embed", "shorts"} else None
        if not video_id or not re.fullmatch(r"[A-Za-z0-9_-]{6,}", video_id):
            raise ValueError("The YouTube URL does not contain a valid video ID")
        return "youtube", video_id

    @staticmethod
    def _get(db: Session, match_id: int, analyst_id: int):
        return db.query(AnalysisSession).options(joinedload(AnalysisSession.video_source), joinedload(AnalysisSession.anchors), joinedload(AnalysisSession.time_segments)).filter_by(match_id=match_id, analyst_id=analyst_id).one_or_none()

    @classmethod
    def get(cls, db: Session, match_id: int, analyst: User):
        return cls._get(db, match_id, analyst.id)

    @staticmethod
    def _find_or_create_source(db: Session, match_id: int, provider: str, video_id: str, url: str, availability_state: str) -> VideoSource:
        source = db.query(VideoSource).filter_by(
            match_id=match_id, provider=provider, provider_video_id=video_id,
        ).one_or_none()
        if source is not None:
            source.original_url = url
            source.availability_state = availability_state
            return source

        source = VideoSource(match_id=match_id, original_url=url, provider=provider,
                             provider_video_id=video_id, availability_state=availability_state)
        try:
            # The unique constraint serializes concurrent creation of one logical video.
            with db.begin_nested():
                db.add(source)
                db.flush()
        except IntegrityError:
            source = db.query(VideoSource).filter_by(
                match_id=match_id, provider=provider, provider_video_id=video_id,
            ).one()
            source.original_url = url
            source.availability_state = availability_state
        return source

    @classmethod
    def save(cls, db: Session, match_id: int, data: AnalysisSessionUpdate, analyst: User):
        source_identity = cls._source_identity(data.source.url) if data.source else None
        session = cls._get(db, match_id, analyst.id)
        if session is None:
            session = AnalysisSession(match_id=match_id, analyst_id=analyst.id)
            db.add(session)
        values = data.model_dump(exclude={"source", "anchors", "time_segments"})
        for field, value in values.items():
            setattr(session, field, value)
        source_changed = False
        if data.source:
            provider, video_id = source_identity
            previous_source = session.video_source
            source_changed = previous_source is not None and (
                previous_source.provider, previous_source.provider_video_id
            ) != (provider, video_id)
            session.video_source = cls._find_or_create_source(
                db, match_id, provider, video_id, data.source.url, data.source.availability_state,
            )
        if source_changed:
            # A timestamp or clock mapping has no meaning across different videos.
            session.video_position_seconds = None
            session.clock_start_video_seconds = None
            session.anchors[:] = []
            session.time_segments[:] = []
        elif data.anchors is not None:
            session.anchors[:] = [TimeAnchor(analyst_id=analyst.id, **anchor.model_dump()) for anchor in data.anchors]
        if not source_changed and data.time_segments is not None:
            session.time_segments[:] = [TimeSegment(analyst_id=analyst.id, **segment.model_dump()) for segment in data.time_segments]
        db.commit()
        return cls._get(db, match_id, analyst.id)
