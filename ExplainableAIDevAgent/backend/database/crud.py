from sqlalchemy.orm import Session
from backend.models.models import Contributor, Commit, MergeRequest, Issue, File, Documentation, AnalysisLog

# --- Contributor CRUD ---
def create_contributor(db: Session, username: str, email: str, name: str = None):
    db_contributor = Contributor(username=username, email=email, name=name)
    db.add(db_contributor)
    db.commit()
    db.refresh(db_contributor)
    return db_contributor

def get_contributor(db: Session, contributor_id: int):
    return db.query(Contributor).filter(Contributor.id == contributor_id).first()

def get_contributors(db: Session, skip: int = 0, limit: int = 100):
    return db.query(Contributor).offset(skip).limit(limit).all()

# --- Commit CRUD ---
def create_commit(db: Session, hash: str, message: str, contributor_id: int):
    db_commit = Commit(hash=hash, message=message, contributor_id=contributor_id)
    db.add(db_commit)
    db.commit()
    db.refresh(db_commit)
    return db_commit

def get_commits(db: Session, skip: int = 0, limit: int = 100):
    return db.query(Commit).offset(skip).limit(limit).all()

# --- MergeRequest CRUD ---
def create_merge_request(db: Session, title: str, description: str, status: str, author_id: int):
    db_mr = MergeRequest(title=title, description=description, status=status, author_id=author_id)
    db.add(db_mr)
    db.commit()
    db.refresh(db_mr)
    return db_mr

def get_merge_requests(db: Session, skip: int = 0, limit: int = 100):
    return db.query(MergeRequest).offset(skip).limit(limit).all()

# --- Issue CRUD ---
def create_issue(db: Session, title: str, description: str, status: str, author_id: int):
    db_issue = Issue(title=title, description=description, status=status, author_id=author_id)
    db.add(db_issue)
    db.commit()
    db.refresh(db_issue)
    return db_issue

def get_issues(db: Session, skip: int = 0, limit: int = 100):
    return db.query(Issue).offset(skip).limit(limit).all()

# --- File CRUD ---
def create_file(db: Session, path: str, content: str):
    db_file = File(path=path, content=content)
    db.add(db_file)
    db.commit()
    db.refresh(db_file)
    return db_file

def get_files(db: Session, skip: int = 0, limit: int = 100):
    return db.query(File).offset(skip).limit(limit).all()

# --- Documentation CRUD ---
def create_documentation(db: Session, title: str, content: str, file_id: int = None):
    db_doc = Documentation(title=title, content=content, file_id=file_id)
    db.add(db_doc)
    db.commit()
    db.refresh(db_doc)
    return db_doc

# --- AnalysisLog CRUD ---
def create_analysis_log(db: Session, entity_type: str, entity_id: int, analysis_result: str):
    db_log = AnalysisLog(entity_type=entity_type, entity_id=entity_id, analysis_result=analysis_result)
    db.add(db_log)
    db.commit()
    db.refresh(db_log)
    return db_log
