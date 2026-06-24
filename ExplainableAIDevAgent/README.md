# ProjectMind AI

ProjectMind AI is an AI-powered project knowledge assistant for software teams. It connects to GitLab, a local/internal repository, or built-in demo data; learns from source code, issues, merge requests, contributors, commits, and documentation; then turns that project knowledge into an interactive developer dashboard.

## What It Does

| Capability | Product value |
|---|---|
| Code Understanding | Explains files, related modules, contributors, issues, and docs |
| Smart Task Assignment | Recommends the best contributor for an issue with clear reasoning |
| Contributor Onboarding | Generates first tasks, mentor suggestions, and learning paths |
| Documentation Maintenance | Detects missing or outdated docs and drafts updates |
| Dashboard | Gives managers and developers a single project intelligence view |

## Run Locally

```bash
pip install -r requirements.txt
copy .env.example .env
python demo_seed.py
python run_projectmind.py
```

Open the URL printed in the terminal. The Windows-friendly launcher avoids the common Uvicorn socket error by choosing an available local port.

If the server is already running, stop it with `Ctrl+C`, then run `python run_projectmind.py` again.

## Verify The Product

After the server starts, run:

```bash
python smoke_test.py
```

This checks the health endpoint, dashboard data, code explanation, task assignment, and documentation health scan.

## Demo Flow

1. Open the dashboard.
2. Connect Project: import a local repository or sync a GitLab project.
3. Code Understanding: explain `backend/auth.py`.
4. Task Assignment: recommend a contributor for issue `24`.
5. Onboarding: generate a plan for a new contributor such as `Jordan Lee`.
6. Documentation Health: scan docs, then generate documentation for `backend/auth.py`.

## API Routes

| Method | Route | Description |
|---|---|---|
| GET | `/` | Dashboard UI |
| GET | `/health` | Simple runtime status |
| GET | `/api/v1/health` | Database and demo-data health |
| GET | `/api/v1/dashboard/stats` | Project metrics and activity |
| POST | `/api/v1/code/explain` | Explain a file |
| GET | `/api/v1/tasks/assign/{issue_id}` | Recommend contributor |
| POST | `/api/v1/tasks/issues` | Create a demo issue and recommend assignee |
| GET | `/api/v1/onboarding/{contributor_id}` | Onboarding plan for existing contributor |
| POST | `/api/v1/onboarding/new` | Onboarding plan for a new contributor |
| GET | `/api/v1/docs/health` | Documentation health scan |
| POST | `/api/v1/docs/generate` | Draft documentation for a file |
| POST | `/api/v1/projects/import_local` | Import a local/internal repository |
| POST | `/api/v1/projects/import_gitlab` | Sync a GitLab project using environment credentials |

Interactive API docs are available at `/docs`.

## Environment Variables

```env
DATABASE_URL=sqlite:///./projectmind_ai.db
GITLAB_URL=https://gitlab.com
GITLAB_TOKEN=your_gitlab_personal_access_token
GITLAB_PROJECT_ID=123456
GEMINI_API_KEY=your_gemini_api_key
PROJECTMIND_AUTO_SEED=true
PROJECTMIND_HOST=127.0.0.1
PROJECTMIND_CORS_ORIGINS=
```

`GEMINI_API_KEY` is optional for demos. Without it, ProjectMind AI uses deterministic fallback explanations so the product still works live.

For production, set `PROJECTMIND_AUTO_SEED=false` and use PostgreSQL.

## Docker

```bash
docker-compose up --build
```

The app runs on `http://localhost:8000`, with PostgreSQL included.

## Architecture

```text
GitLab / local repository
  -> Data Collector
  -> PostgreSQL / SQLite
  -> Knowledge Engine
  -> AI Services
  -> FastAPI API
  -> Bootstrap Dashboard
```

## Project Structure

```text
backend/
  api/
  connectors/
  database/
  models/
  services/
frontend/
  static/
  templates/
demo_seed.py
run_projectmind.py
smoke_test.py
docker-compose.yml
Dockerfile
```

## Release Notes

This version is optimized for a hackathon demo and a future SaaS path:

- Demo data auto-seeds when the database is empty.
- The server picks a safe local port on Windows.
- `/api/v1/health` verifies runtime readiness.
- The dashboard works without a paid AI key.
- Sensitive `.env` files and generated databases are ignored.
