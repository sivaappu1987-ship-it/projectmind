from fastapi import APIRouter
from backend.database.database import SessionLocal
from backend.models.project import Project
from backend.models.contributor import Contributor
from backend.models.commit import Commit
from backend.models.issue import Issue
from backend.models.merge_request import MergeRequest
from backend.models.file import File
from backend.models.documentation import Documentation

router = APIRouter(prefix="/api/v1/dashboard", tags=["Dashboard"])


@router.get("/stats")
async def get_stats():
    db = SessionLocal()
    try:
        contributors = db.query(Contributor).order_by(Contributor.total_commits.desc()).all()
        recent_issues = (
            db.query(Issue)
            .filter(Issue.state.ilike("%open%"))
            .order_by(Issue.id.desc())
            .limit(6)
            .all()
        )
        recent_commits = (
            db.query(Commit)
            .order_by(Commit.id.desc())
            .limit(8)
            .all()
        )
        files = db.query(File).all()
        current_project = db.query(Project).order_by(Project.updated_at.desc(), Project.id.desc()).first()
        open_mrs = db.query(MergeRequest).filter(MergeRequest.state == "open").count()
        merged_mrs = db.query(MergeRequest).filter(MergeRequest.state == "merged").count()

        return {
            "current_project": {
                "id": current_project.id,
                "name": current_project.name,
                "description": current_project.description,
                "visibility": current_project.visibility,
            } if current_project else None,
            "projects": db.query(Project).count(),
            "contributors": len(contributors),
            "commits": db.query(Commit).count(),
            "issues": db.query(Issue).filter(Issue.state.ilike("%open%")).count(),
            "merge_requests": db.query(MergeRequest).count(),
            "open_merge_requests": open_mrs,
            "merged_merge_requests": merged_mrs,
            "files": len(files),
            "documentation": db.query(Documentation).count(),
            "top_contributors": [
                {"name": c.name, "commits": c.total_commits, "email": c.email}
                for c in contributors[:5]
            ],
            "recent_issues": [
                {
                    "id": issue.gitlab_issue_id or issue.id,
                    "title": issue.title,
                    "labels": issue.labels or "",
                    "state": issue.state,
                }
                for issue in recent_issues
            ],
            "recent_commits": [
                {
                    "message": commit.message,
                    "contributor_id": commit.contributor_id,
                }
                for commit in recent_commits
            ],
            "file_list": [
                {"path": f.path}
                for f in files[:12]
            ],
        }
    finally:
        db.close()
