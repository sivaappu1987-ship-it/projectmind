from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.database.database import SessionLocal
from backend.services.onboarding import OnboardingService
from backend.services.analysis_logger import log_analysis

router = APIRouter(prefix="/api/v1/onboarding", tags=["Contributor Onboarding"])


class NewContributorRequest(BaseModel):
    name: str


@router.get("/{contributor_id}")
async def get_onboarding_plan(contributor_id: int):
    db = SessionLocal()
    try:
        plan = OnboardingService(db).build_plan(contributor_id=contributor_id)
        if not plan:
            raise HTTPException(status_code=404, detail="Contributor not found.")
        log_analysis(db, "onboarding", str(contributor_id), {
            "contributor": plan["contributor_name"],
            "mentor": plan["suggested_mentor"],
            "tasks": len(plan["recommended_first_tasks"]),
        })
        return plan
    finally:
        db.close()


@router.post("/new")
async def get_new_contributor_plan(request: NewContributorRequest):
    db = SessionLocal()
    try:
        plan = OnboardingService(db).build_plan(contributor_name=request.name)
        log_analysis(db, "onboarding_new", request.name, {
            "contributor": plan["contributor_name"],
            "mentor": plan["suggested_mentor"],
        })
        return plan
    finally:
        db.close()
