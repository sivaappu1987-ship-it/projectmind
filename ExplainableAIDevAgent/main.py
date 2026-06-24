import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
from dotenv import load_dotenv

from backend.database.database import Base, SessionLocal, engine
import backend.models  # noqa: F401 - register SQLAlchemy models before creating tables
from backend.api.code_understanding import router as code_router
from backend.api.task_assignment import router as task_router
from backend.api.onboarding import router as onboarding_router
from backend.api.docs_maintenance import router as docs_router
from backend.api.dashboard import router as dashboard_router
from backend.api.project_import import router as import_router
from backend.api.logs import router as logs_router
from backend.api.health import router as health_router
from backend.models.project import Project

load_dotenv()

app = FastAPI(
    title="ProjectMind AI",
    description="AI-powered project knowledge assistant for software teams.",
    version="1.0.0",
)

cors_origins = [
    origin.strip()
    for origin in os.getenv("PROJECTMIND_CORS_ORIGINS", "").split(",")
    if origin.strip()
]
if cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

Base.metadata.create_all(bind=engine)


def ensure_demo_data():
    db = SessionLocal()
    try:
        has_project = db.query(Project).first() is not None
    finally:
        db.close()

    if not has_project and os.getenv("PROJECTMIND_AUTO_SEED", "true").lower() == "true":
        from demo_seed import run_demo_seed

        run_demo_seed()


def render_dashboard(request: Request):
    try:
        return templates.TemplateResponse("master_dashboard.html", {"request": request})
    except TypeError:
        return templates.TemplateResponse(request, "master_dashboard.html")


ensure_demo_data()

app.mount("/static", StaticFiles(directory="frontend/static"), name="static")
templates = Jinja2Templates(directory="frontend/templates")

app.include_router(code_router)
app.include_router(task_router)
app.include_router(onboarding_router)
app.include_router(docs_router)
app.include_router(dashboard_router)
app.include_router(import_router)
app.include_router(logs_router)
app.include_router(health_router)

@app.get("/")
async def root(request: Request):
    return render_dashboard(request)

@app.get("/dashboard")
async def dashboard(request: Request):
    return render_dashboard(request)


@app.get("/health", include_in_schema=False)
async def health_alias():
    return {
        "status": "ok",
        "message": "ProjectMind AI is running. Full health details are at /api/v1/health.",
    }

if __name__ == "__main__":
    from run_projectmind import main as run_server

    raise SystemExit(run_server())
