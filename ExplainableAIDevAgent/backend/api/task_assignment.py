from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.database.database import SessionLocal
from backend.models.issue import Issue
from backend.services.task_assignment import TaskAssignmentService
from backend.services.analysis_logger import log_analysis

router = APIRouter(prefix="/api/v1/tasks", tags=["Smart Task Assignment"])


class IssueCreateRequest(BaseModel):
    title: str
    description: str = ""
    labels: str = "bug"
    project_id: int = 1


def _find_issue(db, issue_id: int):
    return (
        db.query(Issue).filter(Issue.gitlab_issue_id == issue_id).first()
        or db.query(Issue).filter(Issue.id == issue_id).first()
    )


@router.post("/issues")
async def create_demo_issue(request: IssueCreateRequest):
    db = SessionLocal()
    try:
        next_gitlab_id = (db.query(Issue).count() or 0) + 40
        issue = Issue(
            project_id=request.project_id,
            gitlab_issue_id=next_gitlab_id,
            title=request.title,
            description=request.description,
            state="opened",
            labels=request.labels,
        )
        db.add(issue)
        db.commit()
        db.refresh(issue)
        recommendation = TaskAssignmentService(db).recommend(issue)
        log_analysis(db, "task_assignment", str(issue.gitlab_issue_id), {
            "issue_title": issue.title,
            "recommended": recommendation["recommended_contributor"],
            "confidence": recommendation["confidence_score"],
        })
        return {"issue_id": issue.gitlab_issue_id, "title": issue.title, **recommendation}
    finally:
        db.close()


@router.get("/assign/{issue_id}")
async def assign_task(issue_id: int):
    db = SessionLocal()
    try:
        issue = _find_issue(db, issue_id)
        if not issue:
            raise HTTPException(status_code=404, detail="Issue not found.")

        recommendation = TaskAssignmentService(db).recommend(issue)
        log_analysis(db, "task_assignment", str(issue_id), {
            "issue_title": issue.title,
            "recommended": recommendation["recommended_contributor"],
            "confidence": recommendation["confidence_score"],
        })
        return {
            "issue_id": issue.gitlab_issue_id or issue.id,
            "issue_title": issue.title,
            **recommendation,
        }
    finally:
        db.close()
