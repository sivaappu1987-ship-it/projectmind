"""Lightweight helper to write AI decision records to analysis_logs."""
from sqlalchemy.orm import Session
from backend.models.analysis_log import AnalysisLog


def log_analysis(db: Session, analysis_type: str, entity_id: str, result: dict) -> None:
    """Fire-and-forget helper that writes one analysis log row. Never raises."""
    try:
        entry = AnalysisLog(
            analysis_type=analysis_type,
            entity_id=str(entity_id),
            result=result,
        )
        db.add(entry)
        db.commit()
    except Exception:
        db.rollback()
