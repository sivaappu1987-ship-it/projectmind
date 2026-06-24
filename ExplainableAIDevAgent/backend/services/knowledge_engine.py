import re
from collections import Counter

from sqlalchemy.orm import Session

from backend.database.database import SessionLocal
from backend.models.commit import Commit
from backend.models.contributor import Contributor
from backend.models.documentation import Documentation
from backend.models.file import File
from backend.models.issue import Issue


STOP_WORDS = {
    "a", "an", "and", "api", "bug", "code", "for", "from", "in", "is", "it",
    "new", "of", "on", "or", "the", "to", "with", "fix", "add", "update",
}


class KnowledgeEngine:
    """
    Lightweight relationship engine for the ProjectMind AI demo.

    It keeps the hackathon version practical: use relational project data,
    filename/module signals, issue labels, commit messages, and documentation
    links instead of heavy graph analytics or prediction models.
    """

    def __init__(self, db: Session | None = None):
        self.db = db or SessionLocal()
        self._owns_session = db is None

    def close(self):
        if self._owns_session:
            self.db.close()

    def _tokens(self, *values: str | None) -> set[str]:
        text = " ".join(v or "" for v in values).lower()
        return {
            token
            for token in re.findall(r"[a-zA-Z][a-zA-Z0-9_]{2,}", text)
            if token not in STOP_WORDS
        }

    def _file_tokens(self, file_obj: File) -> set[str]:
        path_bits = file_obj.path.replace("\\", "/").replace(".", " ")
        return self._tokens(path_bits, file_obj.content[:2500] if file_obj.content else "")

    def _find_file(self, file_path: str) -> File | None:
        normalized = file_path.replace("\\", "/").strip()
        return (
            self.db.query(File)
            .filter(File.path == normalized)
            .first()
            or self.db.query(File).filter(File.path.ilike(f"%{normalized}%")).first()
        )

    def related_files(self, file_obj: File, limit: int = 5) -> list[str]:
        target_tokens = self._file_tokens(file_obj)
        candidates = []
        for candidate in self.db.query(File).filter(File.id != file_obj.id).all():
            score = len(target_tokens.intersection(self._file_tokens(candidate)))
            if score:
                candidates.append((score, candidate.path))
        results = [path for _, path in sorted(candidates, key=lambda x: x[0], reverse=True)[:limit]]
        # Fallback: return top files by id when no overlap found
        if not results:
            results = [f.path for f in self.db.query(File).filter(File.id != file_obj.id).limit(limit).all()]
        return results

    def related_issues(self, file_obj: File, limit: int = 5) -> list[dict]:
        file_tokens = self._file_tokens(file_obj)
        matches = []
        for issue in self.db.query(Issue).all():
            issue_tokens = self._tokens(issue.title, issue.description, issue.labels)
            score = len(file_tokens.intersection(issue_tokens))
            if score:
                matches.append((score, issue))
        results = [
            {
                "id": issue.gitlab_issue_id or issue.id,
                "title": issue.title,
                "state": issue.state,
                "labels": issue.labels or "",
            }
            for _, issue in sorted(matches, key=lambda x: x[0], reverse=True)[:limit]
        ]
        # Fallback: return most recent open issues
        if not results:
            for issue in self.db.query(Issue).filter(Issue.state.ilike("%open%")).limit(limit).all():
                results.append({"id": issue.gitlab_issue_id or issue.id, "title": issue.title, "state": issue.state, "labels": issue.labels or ""})
        return results

    def related_docs(self, file_obj: File, limit: int = 5) -> list[dict]:
        docs = self.db.query(Documentation).filter(Documentation.file_id == file_obj.id).all()
        file_tokens = self._file_tokens(file_obj)

        if len(docs) < limit:
            scored_docs = []
            for doc in self.db.query(Documentation).filter(Documentation.file_id != file_obj.id).all():
                doc_tokens = self._tokens(doc.title, doc.content)
                score = len(file_tokens.intersection(doc_tokens))
                if score:
                    scored_docs.append((score, doc))
            docs.extend(doc for _, doc in sorted(scored_docs, key=lambda x: x[0], reverse=True)[: limit - len(docs)])

        return [{"id": doc.id, "title": doc.title} for doc in docs[:limit]]

    def active_contributors(self, file_obj: File, limit: int = 5) -> list[dict]:
        path = file_obj.path.replace("\\", "/")
        file_terms = self._file_tokens(file_obj)
        scores: Counter[int] = Counter()

        for commit in self.db.query(Commit).all():
            commit_terms = self._tokens(commit.message)
            if path.lower() in (commit.message or "").lower():
                scores[commit.contributor_id] += 5
            scores[commit.contributor_id] += len(file_terms.intersection(commit_terms))

        contributors = []
        for contributor_id, score in scores.most_common(limit):
            contributor = self.db.query(Contributor).filter(Contributor.id == contributor_id).first()
            if contributor:
                contributors.append(
                    {
                        "id": contributor.id,
                        "name": contributor.name,
                        "score": score,
                    }
                )
        return contributors

    def get_file_context(self, file_path: str):
        file_obj = self._find_file(file_path)
        if not file_obj:
            return None

        return {
            "file": file_obj.path,
            "content": file_obj.content or "",
            "related_files": self.related_files(file_obj),
            "related_issues": self.related_issues(file_obj),
            "related_docs": self.related_docs(file_obj),
            "active_contributors": self.active_contributors(file_obj),
        }

    def get_issue_context(self, issue_id: int):
        issue = (
            self.db.query(Issue).filter(Issue.gitlab_issue_id == issue_id).first()
            or self.db.query(Issue).filter(Issue.id == issue_id).first()
        )
        if not issue:
            return None
        return {
            "id": issue.gitlab_issue_id or issue.id,
            "title": issue.title,
            "description": issue.description or "",
            "labels": issue.labels or "",
            "assignee": issue.assignee.name if issue.assignee else None,
        }

    def get_contributor_history(self, contributor_id: int):
        contributor = self.db.query(Contributor).filter(Contributor.id == contributor_id).first()
        if not contributor:
            return None
        return {
            "id": contributor.id,
            "name": contributor.name,
            "total_commits": contributor.total_commits,
            "commits": [commit.message for commit in contributor.commits[:8]],
            "issues": [issue.title for issue in contributor.issues[:8]],
        }
