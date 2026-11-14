import hashlib
import mimetypes
import os
from pathlib import Path

from sqlalchemy.orm import Session

from ..models import LocalVideoAsset, Match, VideoSource


class LocalVideoError(ValueError):
    pass


class LocalVideoService:
    @staticmethod
    def root() -> Path:
        return Path(os.getenv("LOCAL_VIDEO_ROOT", "/app/resources/videos")).resolve()

    @classmethod
    def _path(cls, storage_name: str) -> Path:
        # Only files directly inside the configured root are eligible. This
        # prevents traversal and keeps host paths out of API responses.
        if not storage_name or Path(storage_name).name != storage_name:
            raise LocalVideoError("invalid local video name")
        path = (cls.root() / storage_name).resolve()
        if path.parent != cls.root() or not path.is_file():
            raise LocalVideoError("local video file not found")
        return path

    @staticmethod
    def _sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as video:
            for chunk in iter(lambda: video.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    @classmethod
    def register(cls, db: Session, match_id: int, storage_name: str) -> LocalVideoAsset:
        if db.get(Match, match_id) is None:
            raise LocalVideoError("match not found")
        path = cls._path(storage_name)
        content_type = mimetypes.guess_type(path.name)[0]
        if content_type not in {"video/mp4", "video/webm", "video/ogg"}:
            raise LocalVideoError("local video must be MP4, WebM, or Ogg")
        digest = cls._sha256(path)
        asset = db.query(LocalVideoAsset).filter_by(match_id=match_id, sha256=digest).one_or_none()
        if asset is None:
            asset = LocalVideoAsset(match_id=match_id, storage_name=path.name, display_name=path.name,
                                    content_type=content_type, size_bytes=path.stat().st_size, sha256=digest)
            db.add(asset)
            db.flush()
        return asset

    @classmethod
    def source_asset(cls, db: Session, source: VideoSource) -> LocalVideoAsset:
        if source.provider != "local_private":
            raise LocalVideoError("video source is not private local footage")
        asset = db.get(LocalVideoAsset, source.provider_video_id)
        if asset is None or asset.match_id != source.match_id:
            raise LocalVideoError("local video asset not found")
        return asset

    @classmethod
    def source_path(cls, db: Session, source: VideoSource) -> tuple[LocalVideoAsset, Path]:
        asset = cls.source_asset(db, source)
        path = cls._path(asset.storage_name)
        if path.stat().st_size != asset.size_bytes or cls._sha256(path) != asset.sha256:
            raise LocalVideoError("local video file changed; register it again before reviewing")
        return asset, path
