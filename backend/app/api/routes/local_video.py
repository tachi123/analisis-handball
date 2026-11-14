from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from ...database import get_db
from ...deps import get_current_user
from ...models import User, VideoSource
from ...schemas import LocalVideoPlayback
from ...security import create_local_video_token, decode_access_token
from ...services.local_video_service import LocalVideoError, LocalVideoService

router = APIRouter(tags=["local-video"])
CHUNK_SIZE = 1024 * 1024


def _source(db: Session, source_id: int) -> VideoSource:
    source = db.get(VideoSource, source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="video source not found")
    try:
        LocalVideoService.source_asset(db, source)
    except LocalVideoError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    return source


@router.get("/video-sources/{source_id}/playback", response_model=LocalVideoPlayback)
def playback_url(source_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _source(db, source_id)
    token = create_local_video_token(user.id, source_id)
    return {"url": f"/api/v1/video-sources/{source_id}/stream?token={token}"}


@router.get("/video-sources/{source_id}/stream")
def stream(source_id: int, request: Request, token: str, db: Session = Depends(get_db)):
    payload = decode_access_token(token)
    if payload is None or payload.get("scope") != "local_video" or payload.get("video_source_id") != source_id:
        raise HTTPException(status_code=401, detail="invalid local video token")
    user = db.get(User, int(payload.get("sub", 0)))
    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="invalid local video token")
    source = _source(db, source_id)
    try:
        asset, path = LocalVideoService.source_path(db, source)
    except LocalVideoError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    size = path.stat().st_size
    range_header = request.headers.get("range")
    start, end = 0, size - 1
    if range_header:
        try:
            unit, value = range_header.split("=", 1)
            first, last = value.split("-", 1)
            if unit != "bytes": raise ValueError
            start = int(first) if first else max(0, size - int(last))
            end = int(last) if last else size - 1
            if start < 0 or end < start or start >= size: raise ValueError
            end = min(end, size - 1)
        except ValueError:
            raise HTTPException(status_code=416, detail="invalid byte range")

    def chunks():
        with path.open("rb") as video:
            video.seek(start)
            remaining = end - start + 1
            while remaining:
                chunk = video.read(min(CHUNK_SIZE, remaining))
                if not chunk: break
                remaining -= len(chunk)
                yield chunk

    headers = {"Accept-Ranges": "bytes", "Content-Length": str(end - start + 1), "Cache-Control": "private, no-store"}
    status_code = 206 if range_header else 200
    if range_header: headers["Content-Range"] = f"bytes {start}-{end}/{size}"
    return StreamingResponse(chunks(), status_code=status_code, media_type=asset.content_type, headers=headers)
