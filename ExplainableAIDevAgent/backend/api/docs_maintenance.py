from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.database.database import SessionLocal
from backend.models.file import File
from backend.services.documentation_checker import DocumentationChecker
from backend.services.gemini_llm_service import GeminiLLMService

router = APIRouter(prefix="/api/v1/docs", tags=["Documentation Maintenance"])


class DocGenerateRequest(BaseModel):
    file_path: str


@router.get("/health")
async def get_docs_health():
    db = SessionLocal()
    try:
        health = DocumentationChecker(db).health()
        return {
            **health,
            "orphan_modules_count": health["missing_count"],
            "orphan_modules": health["missing_documentation"],
        }
    finally:
        db.close()


@router.post("/generate")
async def generate_new_docs(request: DocGenerateRequest):
    db = SessionLocal()
    try:
        file_obj = (
            db.query(File).filter(File.path == request.file_path).first()
            or db.query(File).filter(File.path.ilike(f"%{request.file_path}%")).first()
        )
        if not file_obj:
            raise HTTPException(status_code=404, detail="File not found in project database.")

        llm_service = GeminiLLMService()
        prompt = f"""
You are ProjectMind AI.
Create concise Markdown documentation for this source file.
Include purpose, key functions/classes, related setup notes, and maintenance reminders.

File Path: {file_obj.path}
Source Code:
{(file_obj.content or "")[:6000]}
"""
        new_doc_content = None
        if llm_service.client:
            new_doc_content = llm_service.generate_explanation(prompt)
        if not new_doc_content or new_doc_content.startswith("Mock Explanation") or new_doc_content.startswith("Error"):
            new_doc_content = f"""# {file_obj.path}

## Purpose
This file supports the project behavior suggested by its module name and source code.

## Key Responsibilities
- Keep the implementation readable for new contributors.
- Update this document whenever public behavior, endpoints, or dependencies change.
- Link related issues and files during future maintenance.

## Source Notes
The current source has {len((file_obj.content or '').splitlines())} lines and should be reviewed alongside nearby files in the same folder.
"""

        return {
            "file_path": file_obj.path,
            "new_documentation": new_doc_content,
        }
    finally:
        db.close()
