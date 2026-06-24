from datetime import datetime, timezone

from fastapi import APIRouter

from backend.database.database import SessionLocal
from backend.models.commit import Commit
from backend.models.contributor import Contributor
from backend.models.documentation import Documentation
from backend.models.file import File
from backend.models.issue import Issue
from backend.models.project import Project

router = APIRouter(prefix="/api/v1", tags=["Health"])


@router.get("/health")
async def health_check():
    db = SessionLocal()
    try:
        counts = {
            "projects": db.query(Project).count(),
            "contributors": db.query(Contributor).count(),
            "files": db.query(File).count(),
            "issues": db.query(Issue).count(),
            "commits": db.query(Commit).count(),
            "documentation": db.query(Documentation).count(),
        }
        demo_ready = counts["projects"] > 0 and counts["contributors"] > 0 and counts["files"] > 0
        return {
            "status": "ok" if demo_ready else "degraded",
            "service": "ProjectMind AI",
            "database": "ok",
            "demo_data_ready": demo_ready,
            "counts": counts,
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as exc:
        return {
            "status": "error",
            "service": "ProjectMind AI",
            "database": "error",
            "detail": str(exc),
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }
    finally:
        db.close()
