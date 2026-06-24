from fastapi import APIRouter
from backend.database.database import SessionLocal
from backend.models.analysis_log import AnalysisLog

router = APIRouter(prefix="/api/v1/logs", tags=["Analysis Logs"])


@router.get("")
async def get_logs(limit: int = 20):
    db = SessionLocal()
    try:
        logs = (
            db.query(AnalysisLog)
            .order_by(AnalysisLog.created_at.desc())
            .limit(limit)
            .all()
        )
        return [
            {
                "id": log.id,
                "analysis_type": log.analysis_type,
                "entity_id": log.entity_id,
                "result": log.result,
                "created_at": log.created_at.isoformat() if log.created_at else None,
            }
            for log in logs
        ]
    finally:
        db.close()
