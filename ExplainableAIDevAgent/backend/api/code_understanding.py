from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.database.database import SessionLocal
from backend.services.code_understanding import CodeUnderstandingService
from backend.services.analysis_logger import log_analysis

router = APIRouter(prefix="/api/v1/code", tags=["Code Understanding"])


class CodeExplainRequest(BaseModel):
    file_path: str


@router.post("/explain")
async def explain_code(request: CodeExplainRequest):
    result = CodeUnderstandingService().explain_file(request.file_path)
    if not result:
        raise HTTPException(status_code=404, detail="File not found in project database.")

    db = SessionLocal()
    try:
        log_analysis(db, "code_understanding", request.file_path, {
            "related_files": result.get("related_files", []),
            "related_issues": [i["id"] for i in result.get("related_issues", [])],
            "contributors": [c["name"] for c in result.get("active_contributors", [])],
        })
    finally:
        db.close()

    return result
