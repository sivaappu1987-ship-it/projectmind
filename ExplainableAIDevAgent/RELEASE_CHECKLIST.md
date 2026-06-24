# ProjectMind AI Release Checklist

Use this before a demo, deployment, or submission.

## Local Demo

- Run `pip install -r requirements.txt`
- Run `python demo_seed.py`
- Run `python run_projectmind.py`
- Open the URL printed in the terminal
- Run `python smoke_test.py`

## Demo Script

- Code Understanding: explain `backend/auth.py`
- Task Assignment: recommend contributor for issue `24`
- Onboarding: create a plan for `Jordan Lee`
- Documentation Health: run the health scan, then generate docs for `backend/auth.py`

## Production Readiness

- Set `DATABASE_URL` to PostgreSQL
- Set `PROJECTMIND_AUTO_SEED=false` outside demo environments
- Add `GITLAB_TOKEN`, `GITLAB_PROJECT_ID`, and `GITLAB_URL`
- Add `GEMINI_API_KEY` only in trusted environments
- Set `PROJECTMIND_CORS_ORIGINS` to the deployed frontend origin
- Confirm `/api/v1/health` returns `status: ok`
- Confirm `/docs` loads the FastAPI API documentation

## Security Notes

- Do not commit `.env`
- Treat imported repository source code as confidential
- Only enable Gemini for codebases you are allowed to send to the Gemini API
- Rotate GitLab tokens after public demos
