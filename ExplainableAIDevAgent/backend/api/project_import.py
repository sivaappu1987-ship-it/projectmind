import os
import random
import subprocess
import traceback
from datetime import datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.database.database import SessionLocal
from backend.models.commit import Commit
from backend.models.contributor import Contributor
from backend.models.documentation import Documentation
from backend.models.file import File
from backend.models.project import Project
from backend.services.gitlab_service import GitLabService

router = APIRouter(prefix="/api/v1/projects", tags=["Project Import"])


SUPPORTED_EXTENSIONS = {
    ".py", ".js", ".html", ".css", ".md", ".txt", ".json", ".java", ".cpp",
    ".ts", ".jsx", ".tsx", ".yml", ".yaml", ".toml", ".sql", ".go", ".rb",
}
SKIP_DIR_NAMES = {
    ".git", ".hg", ".svn", "node_modules", "venv", ".venv", "__pycache__",
    ".next", "dist", "build", ".pytest_cache", ".mypy_cache", ".idea",
}
MAX_FILE_BYTES = 350_000


class LocalImportRequest(BaseModel):
    directory_path: str
    project_name: str


class GitLabImportRequest(BaseModel):
    project_id: int | None = None
    ref: str = "main"
    max_files: int = 150


def _normalize_path(path: str) -> str:
    return path.replace("\\", "/")


def _get_or_create_contributor(db, name: str | None, email: str | None):
    name = name or "Unknown"
    email = email or f"{name.lower().replace(' ', '.')}@local.project"
    contributor = db.query(Contributor).filter(Contributor.email == email).first()
    if contributor:
        contributor.name = name
        return contributor
    contributor = Contributor(name=name, email=email, total_commits=0)
    db.add(contributor)
    db.flush()
    return contributor


def _read_text_file(path: str) -> str | None:
    if os.path.getsize(path) > MAX_FILE_BYTES:
        return None
    for encoding in ("utf-8", "utf-8-sig", "latin-1"):
        try:
            with open(path, "r", encoding=encoding) as handle:
                return handle.read()
        except UnicodeDecodeError:
            continue
    return None


def _import_git_history(db, project: Project, directory_path: str) -> int:
    if not os.path.isdir(os.path.join(directory_path, ".git")):
        return 0

    try:
        result = subprocess.run(
            [
                "git", "-C", directory_path, "log", "-n", "200",
                "--pretty=format:%H%x1f%an%x1f%ae%x1f%aI%x1f%s",
            ],
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return 0

    if result.returncode != 0:
        return 0

    commit_count = 0
    contributor_counts: dict[int, int] = {}
    for line in result.stdout.splitlines():
        parts = line.split("\x1f", 4)
        if len(parts) != 5:
            continue
        sha, author, email, commit_date, message = parts
        if db.query(Commit).filter(Commit.hash == sha).first():
            continue

        contributor = _get_or_create_contributor(db, author, email)
        parsed_date = None
        try:
            parsed_date = datetime.fromisoformat(commit_date.replace("Z", "+00:00")).replace(tzinfo=None)
        except ValueError:
            parsed_date = datetime.utcnow()

        db.add(
            Commit(
                project_id=project.id,
                hash=sha,
                message=message,
                commit_date=parsed_date,
                contributor_id=contributor.id,
            )
        )
        contributor_counts[contributor.id] = contributor_counts.get(contributor.id, 0) + 1
        commit_count += 1

    for contributor_id, count in contributor_counts.items():
        contributor = db.query(Contributor).filter(Contributor.id == contributor_id).first()
        if contributor:
            contributor.total_commits = (contributor.total_commits or 0) + count

    return commit_count


@router.post("/import_local")
async def import_local_project(request: LocalImportRequest):
    try:
        directory_path = os.path.abspath(os.path.expanduser(request.directory_path))
        if not os.path.isdir(directory_path):
            raise HTTPException(status_code=400, detail="Directory does not exist. Check the path.")

        db = SessionLocal()
        try:
            existing = db.query(Project).filter(Project.description == f"Local Import: {directory_path}").first()
            if existing:
                project = existing
                db.query(Documentation).filter(
                    Documentation.file_id.in_(
                        db.query(File.id).filter(File.project_id == project.id)
                    )
                ).delete(synchronize_session=False)
                db.query(File).filter(File.project_id == project.id).delete(synchronize_session=False)
            else:
                project = Project(
                    gitlab_id=random.randint(10000, 999999999),
                    name=request.project_name,
                    description=f"Local Import: {directory_path}",
                    visibility="private",
                    created_at=datetime.utcnow(),
                )
                db.add(project)
                db.flush()

            file_count = 0
            doc_count = 0

            for root, dirs, files in os.walk(directory_path):
                dirs[:] = [directory for directory in dirs if directory not in SKIP_DIR_NAMES]

                if any(part in SKIP_DIR_NAMES for part in root.split(os.sep)):
                    continue

                for file_name in files:
                    ext = os.path.splitext(file_name)[1].lower()
                    if ext not in SUPPORTED_EXTENSIONS:
                        continue

                    full_path = os.path.join(root, file_name)
                    content = _read_text_file(full_path)
                    if content is None:
                        continue

                    rel_path = _normalize_path(os.path.relpath(full_path, directory_path))
                    file_obj = File(project_id=project.id, path=rel_path, content=content)
                    db.add(file_obj)
                    db.flush()

                    if ext == ".md":
                        db.add(Documentation(title=rel_path, content=content, file_id=file_obj.id))
                        doc_count += 1
                    file_count += 1

            commit_count = _import_git_history(db, project, directory_path)
            db.commit()
            final_project_id = project.id
        finally:
            db.close()

        return {
            "message": "Project successfully loaded.",
            "project_id": final_project_id,
            "project_name": request.project_name,
            "files_processed": file_count,
            "documentation_processed": doc_count,
            "commits_processed": commit_count,
        }
    except HTTPException:
        raise
    except Exception as e:
        trace = traceback.format_exc()
        raise HTTPException(status_code=500, detail=f"Exception: {str(e)}\n\nTraceback:\n{trace}")


@router.post("/import_gitlab")
async def import_gitlab_project(request: GitLabImportRequest):
    project_id = request.project_id or os.getenv("GITLAB_PROJECT_ID")
    if not project_id:
        raise HTTPException(status_code=400, detail="Provide project_id or set GITLAB_PROJECT_ID.")

    db = SessionLocal()
    try:
        service = GitLabService(db)
        project = service.sync_projects(project_id)
        service.sync_contributors(project_id)
        service.sync_commits(project_id)
        service.sync_issues(project_id)
        service.sync_merge_requests(project_id)
        file_count, doc_count = service.sync_repository_files(
            project_id,
            project.id,
            ref=request.ref,
            max_files=request.max_files,
        )
        return {
            "message": "GitLab project successfully synced.",
            "project_id": project.id,
            "project_name": project.name,
            "files_processed": file_count,
            "documentation_processed": doc_count,
        }
    except Exception as e:
        trace = traceback.format_exc()
        raise HTTPException(status_code=500, detail=f"Exception: {str(e)}\n\nTraceback:\n{trace}")
    finally:
        db.close()
