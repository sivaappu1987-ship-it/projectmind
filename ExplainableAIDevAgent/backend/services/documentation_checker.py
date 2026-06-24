from sqlalchemy.orm import Session

from backend.models.documentation import Documentation
from backend.models.file import File
from backend.services.knowledge_engine import KnowledgeEngine


class DocumentationChecker:
    def __init__(self, db: Session):
        self.db = db
        self.engine = KnowledgeEngine(db)

    def health(self):
        missing = []
        outdated = []

        for file_obj in self.db.query(File).all():
            docs = self.db.query(Documentation).filter(Documentation.file_id == file_obj.id).all()
            if not docs:
                missing.append(
                    {
                        "file_path": file_obj.path,
                        "reason": "No documentation is linked to this source file.",
                    }
                )
                continue

            file_terms = self.engine._file_tokens(file_obj)
            for doc in docs:
                doc_terms = self.engine._tokens(doc.title, doc.content)
                overlap = file_terms.intersection(doc_terms)
                changed_after_doc = file_obj.updated_at and doc.updated_at and file_obj.updated_at > doc.updated_at
                if len(overlap) < 2 or changed_after_doc:
                    outdated.append(
                        {
                            "file_path": file_obj.path,
                            "documentation": doc.title,
                            "reason": "Documentation appears stale or does not mention the current module behavior.",
                        }
                    )

        status = "healthy"
        if missing or outdated:
            status = "attention_needed"

        return {
            "status": status,
            "missing_count": len(missing),
            "outdated_count": len(outdated),
            "missing_documentation": missing,
            "outdated_documentation": outdated,
            "action": "Create or refresh documentation for the flagged files.",
        }
