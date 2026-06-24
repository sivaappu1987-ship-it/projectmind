from sqlalchemy.orm import Session

from backend.models.contributor import Contributor
from backend.models.documentation import Documentation
from backend.models.file import File
from backend.models.issue import Issue
from backend.services.gemini_llm_service import GeminiLLMService


class OnboardingService:
    def __init__(self, db: Session):
        self.db = db
        self.llm = GeminiLLMService()

    def build_plan(self, contributor_id: int | None = None, contributor_name: str | None = None):
        contributor = None
        if contributor_id:
            contributor = self.db.query(Contributor).filter(Contributor.id == contributor_id).first()
        if not contributor and contributor_name:
            contributor = Contributor(name=contributor_name, email=f"{contributor_name.lower().replace(' ', '.')}@new.dev")

        if not contributor:
            return None

        mentor = (
            self.db.query(Contributor)
            .filter(Contributor.id != getattr(contributor, "id", 0))
            .order_by(Contributor.total_commits.desc())
            .first()
        )
        beginner_tasks = (
            self.db.query(Issue)
            .filter(Issue.state.ilike("%open%"))
            .filter(Issue.labels.ilike("%good first%") | Issue.labels.ilike("%beginner%"))
            .limit(3)
            .all()
        )
        if len(beginner_tasks) < 3:
            beginner_tasks.extend(
                self.db.query(Issue)
                .filter(Issue.state.ilike("%open%"))
                .filter(~Issue.id.in_([issue.id for issue in beginner_tasks]))
                .limit(3 - len(beginner_tasks))
                .all()
            )

        docs = self.db.query(Documentation).limit(4).all()
        files = self.db.query(File).limit(4).all()

        learning_path = []
        learning_path.extend(f"Read {doc.title}" for doc in docs)
        learning_path.extend(f"Explore {file.path}" for file in files)
        learning_path = learning_path[:6] or ["Review the README", "Pick a small open issue", "Ask for a review from a senior contributor"]

        base_plan = {
            "contributor_name": contributor.name,
            "suggested_mentor": mentor.name if mentor else "First senior contributor to join",
            "mentor_commits": mentor.total_commits if mentor else 0,
            "recommended_first_tasks": [
                {
                    "id": issue.gitlab_issue_id or issue.id,
                    "title": issue.title,
                    "labels": issue.labels,
                }
                for issue in beginner_tasks
            ],
            "learning_path": learning_path,
        }

        # Build AI-enhanced roadmap narrative
        tasks_text = "\n".join(
            f"- Issue #{t['id']}: {t['title']} [{t['labels']}]"
            for t in base_plan["recommended_first_tasks"]
        )
        path_text = "\n".join(f"{i+1}. {step}" for i, step in enumerate(learning_path))

        prompt = f"""You are ProjectMind AI, an engineering mentor assistant.
Write a warm, encouraging, and practical onboarding plan for a new developer joining this project.

New Contributor: {contributor.name}
Suggested Mentor: {base_plan['suggested_mentor']} ({base_plan['mentor_commits']} commits)

Recommended First Tasks:
{tasks_text}

Learning Path:
{path_text}

Write the plan with these clearly labeled sections:
- Welcome Message (2-3 sentences, personalized and warm)
- Suggested Mentor
- Recommended First Tasks (list with brief context for each)
- Learning Path (numbered, with a short explanation for each step)
- Tips for Success (3 bullet points)
"""
        roadmap = None
        if self.llm.client:
            roadmap = self.llm.generate_explanation(prompt)
        if not roadmap or roadmap.startswith("Mock Explanation") or roadmap.startswith("Error"):
            roadmap = self._fallback_roadmap(base_plan)

        return {**base_plan, "roadmap": roadmap}

    def _fallback_roadmap(self, plan: dict) -> str:
        tasks = "\n".join(
            f"  - Issue #{t['id']}: {t['title']}" for t in plan["recommended_first_tasks"]
        ) or "  - No beginner issues open yet"
        path = "\n".join(f"  {i+1}. {step}" for i, step in enumerate(plan["learning_path"]))
        return f"""Welcome to the team, {plan['contributor_name']}!
We're excited to have you on board. This plan will help you get productive quickly.

Suggested Mentor:
  {plan['suggested_mentor']} - your go-to person for code reviews and questions.

Recommended First Tasks:
{tasks}

Learning Path:
{path}

Tips for Success:
  - Read through the linked documentation before diving into code.
  - Ask your mentor for a 30-minute walkthrough of the codebase on day one.
  - Make your first contribution small - a test, a doc fix, or a minor bug goes a long way."""
