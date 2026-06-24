from backend.services.gemini_llm_service import GeminiLLMService
from backend.services.knowledge_engine import KnowledgeEngine


class CodeUnderstandingService:
    def __init__(self):
        self.llm = GeminiLLMService()

    def explain_file(self, file_path: str):
        engine = KnowledgeEngine()
        try:
            context = engine.get_file_context(file_path)
        finally:
            engine.close()

        if not context:
            return None

        prompt = f"""
You are ProjectMind AI, a practical project knowledge assistant.
Explain this file for a developer joining the team.

File: {context["file"]}
Related files: {context["related_files"]}
Related issues: {context["related_issues"]}
Related documentation: {context["related_docs"]}
Main contributors: {context["active_contributors"]}

Source:
{context["content"][:6000]}

Return:
- Purpose
- Main responsibilities
- Related files
- Related issues
- Related documentation
- Main contributors
"""
        if self.llm.client:
            explanation = self.llm.generate_explanation(prompt)
        else:
            explanation = "Mock Explanation"
        if explanation.startswith("Mock Explanation") or explanation.startswith("Error"):
            explanation = self._fallback_explanation(context)

        return {**context, "explanation": explanation}

    def _fallback_explanation(self, context: dict) -> str:
        file_name = context["file"].split("/")[-1].split("\\")[-1]
        purpose = self._infer_purpose(file_name, context["content"])
        related_files = "\n".join(f"- {path}" for path in context["related_files"]) or "- None found yet"
        issues = "\n".join(
            f"- #{issue['id']} {issue['title']}" for issue in context["related_issues"]
        ) or "- None found yet"
        docs = "\n".join(f"- {doc['title']}" for doc in context["related_docs"]) or "- Missing"
        contributors = "\n".join(
            f"- {person['name']}" for person in context["active_contributors"]
        ) or "- No commit history found"

        return f"""Purpose:
{purpose}

Main Responsibilities:
- Owns the behavior suggested by `{file_name}` and its surrounding module.
- Connects to nearby files through imports, shared terms, and commit history.
- Gives new developers a compact starting point before they read the full source.

Related Files:
{related_files}

Related Issues:
{issues}

Related Documentation:
{docs}

Main Contributors:
{contributors}"""

    def _infer_purpose(self, file_name: str, content: str) -> str:
        text = f"{file_name} {content}".lower()
        if "auth" in text or "login" in text or "token" in text:
            return "Handles authentication, login/session behavior, and access-token validation."
        if "issue" in text:
            return "Manages issue records and project task metadata."
        if "doc" in text or "readme" in text:
            return "Maintains documentation content or documentation checks."
        if "api" in text or "fastapi" in text or "route" in text:
            return "Exposes backend API endpoints used by the dashboard and integrations."
        return "Provides project-specific application logic used by nearby modules."
