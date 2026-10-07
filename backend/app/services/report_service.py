from datetime import datetime, timezone

from ..models import Match, RecoveryArtifact, ReportPackage, ReportPackageEvidence, ReportPublication
from .canonical_analysis_service import read_metrics, read_reconciliation


PUBLIC_REPORT_SCHEMA_VERSION = "public-report-v1"
REQUIRED_RECOVERY_ARTIFACTS = {"postgres_dump", "imported_pdf_export"}
PUBLIC_METRIC_FIELDS = ("count", "numerator", "denominator", "excluded", "unknown", "clock_unverified")
PUBLIC_METRIC_NAMES = {
    "shot_conversion", "seven_meter_conversion", "observed_goalkeeper_save_rate",
    "confirmed_assist", "recovery", "defensive_action", "foul_sanction",
    "transition_outcome", "goalkeeper_outcome",
}


def is_public_metric(name):
    return name in PUBLIC_METRIC_NAMES or name.startswith(("turnover:", "team:", "player:", "goalkeeper:")) or name in {"shots", "turnovers", "recoveries", "discipline", "possessions"}


class ReportService:
    @staticmethod
    def missing_recovery_artifacts(package: ReportPackage):
        completed = {
            artifact.artifact_type
            for artifact in package.recovery_artifacts
            if artifact.attested_at is not None
        }
        return sorted(REQUIRED_RECOVERY_ARTIFACTS - completed)

    @classmethod
    def publication_readiness(cls, package: ReportPackage):
        missing = cls.missing_recovery_artifacts(package)
        return {
            "approved": package.approved_at is not None,
            "missing_recovery_artifacts": missing,
            "ready": package.approved_at is not None and not missing,
        }

    @staticmethod
    def attest_recovery_artifact(db, package: ReportPackage, artifact_type, location, user):
        artifact = db.query(RecoveryArtifact).filter_by(
            package_id=package.id, artifact_type=artifact_type
        ).one_or_none()
        if artifact is None:
            artifact = RecoveryArtifact(package_id=package.id, artifact_type=artifact_type)
            db.add(artifact)
        artifact.location = location
        artifact.attested_at = datetime.now(timezone.utc)
        artifact.attested_by_user_id = user.id
        db.commit()
        db.refresh(artifact)
        return artifact

    @staticmethod
    def get(db, package_id: int):
        return db.get(ReportPackage, package_id)

    @staticmethod
    def create(db, match_id, data, user):
        match = db.get(Match, match_id)
        if match is None:
            raise ValueError("Match not found")
        values = data.model_dump(exclude={"evidence", "canonical_event_ids"})
        cutover = bool(match.canonical_analysis_enabled)
        canonical_requested = data.source_status == "canonical" or bool(data.canonical_event_ids)
        if cutover or canonical_requested:
            # Server-derived only: client metrics/reconciliation/evidence are never trusted.
            derived = read_metrics(db, match_id)
            eligible_ids = {event["id"] for event in derived["events"]}
            selected_ids = set(data.canonical_event_ids)
            if not selected_ids:
                raise ValueError("A report for a canonically-enabled match requires selected eligible event evidence")
            if not selected_ids <= eligible_ids:
                raise ValueError("A report cannot claim unsupported or ineligible canonical evidence")
            if derived["eligibility"]["eligible"] == 0:
                raise ValueError("A report cannot claim tactics without eligible canonical facts")
            values["metrics"] = derived["metrics"]
            values["reconciliation"] = read_reconciliation(db, match_id)["discrepancies"]
            values["source_label"] = "Canonical eligible event ledger"
            values["source_status"] = "canonical-eligible"
            events_by_id = {event["id"]: event for event in derived["events"]}
            evidence_rows = []
            for event_id in sorted(selected_ids):
                event = events_by_id[event_id]
                payload = event["payload"]
                evidence_rows.append(ReportPackageEvidence(
                    reference=f"canonical:{event['id']}:rev:{event['revision']}",
                    period=payload.get("period", 1),
                    regulation_seconds=payload.get("regulation_seconds"),
                    clock_unverified=bool(payload.get("clock_unverified")),
                ))
            package = ReportPackage(match_id=match_id, analyst_id=user.id, **values)
            package.evidence = evidence_rows
        else:
            package = ReportPackage(match_id=match_id, analyst_id=user.id, **values)
            package.evidence = [ReportPackageEvidence(**item.model_dump()) for item in data.evidence]
        db.add(package)
        db.commit()
        db.refresh(package)
        return package

    @staticmethod
    def update(db, package: ReportPackage, data):
        if package.approved_at is not None:
            raise ValueError("Approved report packages cannot be edited")
        if package.source_status == "canonical-eligible":
            raise ValueError("Canonical report packages must be recreated from current eligible evidence")
        values = data.model_dump(exclude={"evidence", "canonical_event_ids"})
        for field, value in values.items():
            setattr(package, field, value)
        package.evidence[:] = [ReportPackageEvidence(**item.model_dump()) for item in data.evidence]
        db.commit()
        db.refresh(package)
        return package

    @staticmethod
    def approve(db, package: ReportPackage):
        approved_evidence = [item for item in package.evidence if item.public_approved]
        if not 3 <= len(approved_evidence) <= 8:
            raise ValueError("Approval requires 3 to 8 approved evidence references")
        if package.action_kind not in {"keep", "do", "change"} or not package.action_text.strip():
            raise ValueError("Approval requires exactly one keep, do, or change action")
        package.approved_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(package)
        return package

    @staticmethod
    def public_projection(package: ReportPackage):
        if package.schema_version != PUBLIC_REPORT_SCHEMA_VERSION:
            raise ValueError("Unsupported public report schema version")
        evidence = []
        for item in package.evidence:
            if not item.public_approved:
                continue
            public_item = {
                "reference": item.reference,
                "period": item.period,
                "regulation_seconds": item.regulation_seconds,
                "clock_unverified": item.clock_unverified,
                "observation": item.public_observation,
                "media_available": bool(item.media_public_approved and item.public_media_url),
            }
            if public_item["media_available"]:
                public_item["media_url"] = item.public_media_url
            evidence.append(public_item)
        metrics = {
            name: {field: value.get(field) for field in PUBLIC_METRIC_FIELDS if field in value}
            for name, value in package.metrics.items()
            if is_public_metric(name) and isinstance(value, dict)
        }
        # Derive coverage from evidence periods; optional fields for partial coverage reports
        all_periods = sorted({item.period for item in package.evidence if item.public_approved and item.period is not None})
        coverage: dict | None = None
        if all_periods:
            # A report is "partial" when it does not cover both halves (periods 1 and 2)
            has_half1 = 1 in all_periods
            has_half2 = 2 in all_periods
            if has_half1 and has_half2:
                status = "complete"
                label = None
            else:
                status = "partial"
                analyzed = [p for p in all_periods if p is not None]
                label = f"Analysis covering periods {', '.join(str(p) for p in analyzed)}"
            coverage = {
                "analyzed_periods": all_periods,
                "status": status,
                "label": label,
            }
        return {
            "schema_version": package.schema_version,
            "report_version": package.report_version,
            "match": {
                "date": package.match.date.isoformat() if package.match.date else None,
                "home_team": package.match.home_team.name if package.match.home_team else None,
                "away_team": package.match.away_team.name if package.match.away_team else None,
            },
            "source": {"label": package.source_label, "status": package.source_status},
            "coaching": {
                "question": package.coaching_question,
                "pattern_statement": package.pattern_statement,
                "action": {"kind": package.action_kind, "text": package.action_text},
            },
            "metrics": metrics,
            "reconciliation": package.reconciliation,
            "uncertainty_disclosure": package.uncertainty_disclosure,
            "players": getattr(package, 'players', None),
            "evidence": evidence,
            "coverage": coverage,
        }

    @classmethod
    def publish(cls, db, package: ReportPackage, adapter_factory=None):
        readiness = cls.publication_readiness(package)
        if not readiness["ready"]:
            missing = ", ".join(readiness["missing_recovery_artifacts"])
            raise ValueError(f"Report package is not ready for publication: {missing or 'approval required'}")
        projection = cls.public_projection(package)
        publication = db.query(ReportPublication).filter_by(
            package_id=package.id, report_version=package.report_version
        ).one_or_none()
        if publication is None:
            publication = ReportPublication(
                package_id=package.id,
                report_version=package.report_version,
                schema_version=package.schema_version,
                status="pending",
            )
            db.add(publication)
            db.flush()
        publication.status = "publishing"
        db.commit()
        try:
            if adapter_factory is None:
                from .sheets_service import get_report_adapter
                adapter_factory = get_report_adapter
            adapter_factory().upsert(projection)
        except Exception:
            publication.status = "failed"
            db.commit()
            raise
        publication.status = "published"
        publication.published_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(publication)
        return publication
