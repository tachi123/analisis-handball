from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models import AnalysisRun, CanonicalEvent, Match, OfficialSnapshot, User
from app.services.match_service import MatchService


class AnalysisRunError(ValueError):
    pass


def active_run(db: Session, match_id: int) -> AnalysisRun | None:
    return db.query(AnalysisRun).filter_by(match_id=match_id, status="active").one_or_none()


def resolve_run(db: Session, match_id: int, run_id: int | None = None) -> AnalysisRun:
    run = db.get(AnalysisRun, run_id) if run_id is not None else active_run(db, match_id)
    if run is None and run_id is None:
        # Metadata-only test databases predate the migration and may contain the
        # temporary draft created by require_writable_run.
        run = db.query(AnalysisRun).filter_by(match_id=match_id, status="draft").one_or_none()
    if run is None or run.match_id != match_id:
        raise AnalysisRunError("analysis run not found")
    return run


def require_writable_run(db: Session, match: Match, run_id: int | None, user: User) -> AnalysisRun:
    if run_id is None:
        # This is only for metadata-created test fixtures that did not run Alembic.
        # A migrated database always has an explicit active or legacy run.
        if db.query(AnalysisRun).filter_by(match_id=match.id).count() == 0:
            run = AnalysisRun(match_id=match.id, mode="legacy", status="draft", created_by_user_id=user.id)
            db.add(run)
            db.flush()
            # Metadata-only fixtures can include canonical events created before
            # analysis runs existed; keep their projection with the implicit run.
            db.query(CanonicalEvent).filter_by(match_id=match.id, run_id=None).update({"run_id": run.id})
            return run
        drafts = db.query(AnalysisRun).filter_by(match_id=match.id, status="draft").all()
        if len(drafts) == 1:
            run = drafts[0]
            if run.created_by_user_id != user.id and user.role not in {"superadmin", "admin"}:
                raise PermissionError("only the run creator or an admin can write to this analysis run")
            return run
        raise AnalysisRunError("a draft analysis run is required for writes")
    run = resolve_run(db, match.id, run_id)
    if run.status not in ("draft", "active"):
        raise AnalysisRunError("only draft and active analysis runs are writable")
    if run.created_by_user_id != user.id and user.role not in {"superadmin", "admin"}:
        raise PermissionError("only the run creator or an admin can write to this analysis run")
    return run


def _require_official_sheet(db: Session, match_id: int) -> None:
    if not db.query(OfficialSnapshot).filter_by(match_id=match_id, is_confirmed=True).first():
        raise AnalysisRunError("a confirmed official sheet is required before creating an analysis run")


def create_draft(db: Session, match_id: int, mode: str, user: User) -> AnalysisRun:
    match = db.query(Match).filter_by(id=match_id).with_for_update().one_or_none()
    if match is None:
        raise AnalysisRunError("match not found")
    if match.origin == "manual":
        MatchService.require_manual_owner(db, match_id, user)
    if user.role not in {"superadmin", "admin"}:
        _require_official_sheet(db, match_id)
    run = AnalysisRun(match_id=match_id, mode=mode, status="draft", created_by_user_id=user.id)
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


def list_runs(db: Session, match_id: int) -> list[AnalysisRun]:
    if db.get(Match, match_id) is None:
        raise AnalysisRunError("match not found")
    return db.query(AnalysisRun).filter_by(match_id=match_id).order_by(AnalysisRun.id.desc()).all()


def promote(db: Session, match_id: int, run_id: int, user: User) -> AnalysisRun:
    match = db.query(Match).filter_by(id=match_id).with_for_update().one_or_none()
    if match is None:
        raise AnalysisRunError("match not found")
    run = db.get(AnalysisRun, run_id)
    if run is None or run.match_id != match_id:
        raise AnalysisRunError("analysis run not found")
    if run.status != "draft":
        raise AnalysisRunError("only draft analysis runs can be promoted")
    if run.created_by_user_id != user.id and user.role not in {"superadmin", "admin"}:
        raise AnalysisRunError("only the run creator or an admin can promote this analysis run")
    now = datetime.now(timezone.utc)
    db.query(AnalysisRun).filter_by(match_id=match_id, status="active").update(
        {"status": "superseded", "superseded_at": now}, synchronize_session=False
    )
    run.status = "active"
    run.promoted_at = now
    match.canonical_analysis_enabled = True
    db.commit()
    db.refresh(run)
    return run
