from collections import Counter

from sqlalchemy.orm import Session

from backend.models.commit import Commit
from backend.models.contributor import Contributor
from backend.models.issue import Issue
from backend.services.gemini_llm_service import GeminiLLMService
from backend.services.knowledge_engine import KnowledgeEngine


class TaskAssignmentService:
    def __init__(self, db: Session):
        self.db = db
        self.engine = KnowledgeEngine(db)
        self.llm = GeminiLLMService()

    def recommend(self, issue: Issue):
        issue_terms = self.engine._tokens(issue.title, issue.description, issue.labels)
        scores: Counter[int] = Counter()
        reasons: dict[int, list[str]] = {}

        # Score by commit volume
        for contributor in self.db.query(Contributor).all():
            base = min(contributor.total_commits or 0, 200) / 25
            scores[contributor.id] += base
            reasons.setdefault(contributor.id, []).append(
                f"{contributor.name} has {contributor.total_commits or 0} commits in this project."
            )

        # Score by commit message overlap with issue terms
        for commit in self.db.query(Commit).all():
            overlap = issue_terms.intersection(self.engine._tokens(commit.message))
            if overlap:
                points = len(overlap) * 12
                scores[commit.contributor_id] += points
                reasons.setdefault(commit.contributor_id, []).append(
                    f"Past commit matches issue terms: {', '.join(sorted(overlap)[:4])}."
                )

        # Score by similar past issues
        for past_issue in self.db.query(Issue).filter(Issue.assignee_id.isnot(None)).all():
            overlap = issue_terms.intersection(
                self.engine._tokens(past_issue.title, past_issue.description, past_issue.labels)
            )
            if overlap:
                scores[past_issue.assignee_id] += len(overlap) * 10
                reasons.setdefault(past_issue.assignee_id, []).append(
                    f"Previously handled similar issue #{past_issue.gitlab_issue_id or past_issue.id}."
                )

        if not scores:
            return {
                "recommended_contributor": "Unassigned",
                "confidence_score": 0,
                "explanation": "No contributor history is available yet.",
            }

        # Top 3 candidates for context
        top3 = scores.most_common(3)
        top_contributor_id, top_score = top3[0]
        top_contributor = self.db.query(Contributor).filter(Contributor.id == top_contributor_id).first()
        confidence = max(55, min(92, int(55 + top_score)))

        # Build candidate summaries for the prompt
        candidate_lines = []
        for cid, cscore in top3:
            c = self.db.query(Contributor).filter(Contributor.id == cid).first()
            if c:
                why = " ".join(reasons.get(cid, [])[:2])
                candidate_lines.append(f"- {c.name} (score {int(cscore)}): {why}")

        # Try AI-generated explanation
        explanation = self._ai_explanation(issue, top_contributor, candidate_lines, confidence)

        return {
            "recommended_contributor": top_contributor.name,
            "confidence_score": confidence,
            "explanation": explanation,
        }

    def _ai_explanation(self, issue: Issue, contributor: Contributor,
                        candidate_lines: list[str], confidence: int) -> str:
        if not self.llm.client:
            return self._fallback_explanation(issue, contributor, candidate_lines)

        prompt = f"""You are ProjectMind AI, a smart task assignment assistant.
Explain in 2-3 clear sentences why {contributor.name} is the best person for this issue.
Be specific about their relevant history and skills. Be direct, not flowery.

Issue: #{issue.gitlab_issue_id or issue.id} - {issue.title}
Description: {(issue.description or '')[:300]}
Labels: {issue.labels or 'none'}

Top candidates considered:
{chr(10).join(candidate_lines)}

Recommended: {contributor.name} with {confidence}% confidence.

Write only the explanation - no headings, no bullet points, just 2-3 sentences.
"""
        result = self.llm.generate_explanation(prompt)
        if result.startswith("Mock") or result.startswith("Error") or not result.strip():
            return self._fallback_explanation(issue, contributor, candidate_lines)
        return result

    def _fallback_explanation(self, issue: Issue, contributor: Contributor,
                               candidate_lines: list[str]) -> str:
        lines = "\n".join(candidate_lines) if candidate_lines else f"- {contributor.name}: top scorer"
        return f"**{contributor.name}** is the strongest match for this issue based on commit history and past issue overlap.\n\n**Scoring signals:**\n{lines}"
