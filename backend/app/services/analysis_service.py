from sqlalchemy.orm import Session

from .canonical_analysis_service import read_metrics, read_reconciliation


class AnalysisService:
    """Compatibility read facade; analytical metrics are canonical-only."""

    @staticmethod
    def reviewed_metrics(db: Session, match_id: int):
        metrics = read_metrics(db, match_id)
        reconciliation = read_reconciliation(db, match_id)
        return {
            "metrics": metrics["metrics"],
            "eligibility": metrics["eligibility"],
            "evidence": metrics["evidence"],
            "official": reconciliation["official"],
            "reconciliation": reconciliation["discrepancies"],
        }
