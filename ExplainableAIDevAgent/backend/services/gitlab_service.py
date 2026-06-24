import os
import time
import logging
from datetime import datetime
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from sqlalchemy.orm import Session

from backend.database.database import SessionLocal
from backend.models.project import Project
from backend.models.contributor import Contributor
from backend.models.commit import Commit
from backend.models.merge_request import MergeRequest
from backend.models.issue import Issue
from backend.models.file import File
from backend.models.documentation import Documentation

logger = logging.getLogger(__name__)

SUPPORTED_SOURCE_EXTENSIONS = {
    ".py", ".js", ".ts", ".jsx", ".tsx", ".html", ".css", ".md", ".txt",
    ".json", ".yml", ".yaml", ".toml", ".sql", ".java", ".go", ".rb",
}
MAX_SYNC_FILE_CHARS = 250_000

class GitLabService:
    def __init__(self, db_session: Session = None):
        """
        Initializes the GitLab Service with automatic rate-limit retries
        and connection pooling.
        """
        self.gitlab_url = os.getenv("GITLAB_URL", "https://gitlab.com").rstrip("/")
        self.token = os.getenv("GITLAB_TOKEN")
        self.headers = {"PRIVATE-TOKEN": self.token} if self.token and self.token != "your_gitlab_personal_access_token" else {}
        self.session = self._get_session()
        self.db = db_session or SessionLocal()

    def _get_session(self):
        session = requests.Session()
        session.headers.update(self.headers)
        
        # Configure robust retry strategy for production readiness
        retries = Retry(
            total=5,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"]
        )
        adapter = HTTPAdapter(max_retries=retries)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        return session

    def _paginate(self, url, params=None):
        """
        Handles GitLab's keyset and offset pagination automatically.
        """
        if params is None:
            params = {}
        params['per_page'] = 100
        params['page'] = 1
        results = []
        
        while True:
            try:
                response = self.session.get(url, params=params, timeout=15)
                response.raise_for_status()
                data = response.json()
                
                if not data:
                    break
                if isinstance(data, dict):
                    return [data] # Single item return
                    
                results.extend(data)
                
                # Check for pagination headers
                if 'x-next-page' in response.headers and response.headers['x-next-page']:
                    params['page'] = int(response.headers['x-next-page'])
                else:
                    break
            except requests.exceptions.Timeout:
                logger.error(f"Timeout while requesting {url}. Retrying...")
                time.sleep(2)
            except requests.exceptions.RequestException as e:
                logger.error(f"API Error fetching {url}: {e}")
                break
        return results

    # --- API Retrieval Methods ---

    def get_project(self, project_id):
        url = f"{self.gitlab_url}/api/v4/projects/{project_id}"
        response = self.session.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        return {
            "Project ID": data.get("id"),
            "Name": data.get("name"),
            "Description": data.get("description"),
            "Visibility": data.get("visibility"),
            "Created Date": data.get("created_at")
        }

    def get_commits(self, project_id):
        url = f"{self.gitlab_url}/api/v4/projects/{project_id}/repository/commits"
        data = self._paginate(url)
        return [{
            "Commit ID": c.get("id"),
            "Commit SHA": c.get("id"),
            "Author Name": c.get("author_name"),
            "Author Email": c.get("author_email"),
            "Commit Message": c.get("message"),
            "Commit Date": c.get("created_at")
        } for c in data]

    def get_merge_requests(self, project_id):
        url = f"{self.gitlab_url}/api/v4/projects/{project_id}/merge_requests"
        data = self._paginate(url)
        return [{
            "MR ID": mr.get("id"),
            "Title": mr.get("title"),
            "Description": mr.get("description"),
            "State": mr.get("state"),
            "Author": mr.get("author", {}).get("name") if mr.get("author") else None,
            "Created Date": mr.get("created_at"),
            "Updated Date": mr.get("updated_at")
        } for mr in data]

    def get_issues(self, project_id):
        url = f"{self.gitlab_url}/api/v4/projects/{project_id}/issues"
        data = self._paginate(url)
        return [{
            "Issue ID": issue.get("id"),
            "Title": issue.get("title"),
            "Description": issue.get("description"),
            "Labels": issue.get("labels"),
            "State": issue.get("state"),
            "Assignee": issue.get("assignee", {}).get("name") if issue.get("assignee") else None,
            "Created Date": issue.get("created_at")
        } for issue in data]

    def get_contributors(self, project_id):
        url = f"{self.gitlab_url}/api/v4/projects/{project_id}/repository/contributors"
        data = self._paginate(url)
        return [{
            "Contributor Name": c.get("name"),
            "Email": c.get("email"),
            "Total Commits": c.get("commits")
        } for c in data]

    def get_repository_tree(self, project_id, ref=None):
        url = f"{self.gitlab_url}/api/v4/projects/{project_id}/repository/tree"
        params = {"recursive": True}
        if ref:
            params["ref"] = ref
        data = self._paginate(url, params)
        return {
            "Files": [f["path"] for f in data if f["type"] == "blob"],
            "Directories": [f["path"] for f in data if f["type"] == "tree"],
            "Paths": [f["path"] for f in data]
        }

    def get_file_content(self, project_id, file_path):
        import urllib.parse
        encoded_path = urllib.parse.quote_plus(file_path)
        url = f"{self.gitlab_url}/api/v4/projects/{project_id}/repository/files/{encoded_path}/raw"
        params = {"ref": "main"}
        try:
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            return response.text
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching content for file {file_path}: {e}")
            return None

    def get_file_content_at_ref(self, project_id, file_path, ref="main"):
        import urllib.parse

        encoded_path = urllib.parse.quote_plus(file_path)
        url = f"{self.gitlab_url}/api/v4/projects/{project_id}/repository/files/{encoded_path}/raw"
        params = {"ref": ref}
        try:
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            return response.text
        except requests.exceptions.RequestException as e:
            logger.warning("Error fetching %s at %s: %s", file_path, ref, e)
            return None

    # --- Database Sync Methods ---

    def _get_or_create_contributor(self, name, email):
        if not email:
            email = f"{str(name).replace(' ', '_').lower()}@noreply.gitlab.com"
        if not name:
            name = "Unknown"
            
        contributor = self.db.query(Contributor).filter_by(email=email).first()
        if not contributor:
            contributor = Contributor(name=name, email=email)
            self.db.add(contributor)
            self.db.commit()
            self.db.refresh(contributor)
        return contributor

    def _parse_date(self, date_str):
        if not date_str:
            return datetime.utcnow()
        try:
            return datetime.strptime(date_str[:19], "%Y-%m-%dT%H:%M:%S")
        except ValueError:
            return datetime.utcnow()

    def sync_projects(self, project_id):
        logger.info(f"Syncing Project {project_id}...")
        p_data = self.get_project(project_id)
        
        project = self.db.query(Project).filter_by(gitlab_id=p_data["Project ID"]).first()
        if not project:
            project = Project(
                gitlab_id=p_data["Project ID"],
                name=p_data["Name"],
                description=p_data["Description"],
                visibility=p_data["Visibility"],
                created_at=self._parse_date(p_data["Created Date"])
            )
            self.db.add(project)
        else:
            project.name = p_data["Name"]
            project.description = p_data["Description"]
            project.visibility = p_data["Visibility"]
        self.db.commit()
        self.db.refresh(project)
        return project

    def sync_commits(self, project_id):
        logger.info(f"Syncing Commits for Project {project_id}...")
        project = self.sync_projects(project_id)
        commits_data = self.get_commits(project_id)
        
        for c in commits_data:
            contributor = self._get_or_create_contributor(c["Author Name"], c["Author Email"])
            
            if not self.db.query(Commit).filter_by(hash=c["Commit SHA"]).first():
                new_commit = Commit(
                    project_id=project.id,
                    hash=c["Commit SHA"],
                    message=c["Commit Message"],
                    commit_date=self._parse_date(c["Commit Date"]),
                    contributor_id=contributor.id
                )
                self.db.add(new_commit)
        self.db.commit()

    def sync_contributors(self, project_id):
        logger.info(f"Syncing Contributors for Project {project_id}...")
        contributors_data = self.get_contributors(project_id)
        for c in contributors_data:
            contributor = self._get_or_create_contributor(c["Contributor Name"], c["Email"])
            contributor.total_commits = c["Total Commits"]
        self.db.commit()

    def sync_merge_requests(self, project_id):
        logger.info(f"Syncing Merge Requests for Project {project_id}...")
        project = self.sync_projects(project_id)
        mr_data = self.get_merge_requests(project_id)
        
        for mr in mr_data:
            contributor = self._get_or_create_contributor(mr["Author"], None)
            
            existing_mr = self.db.query(MergeRequest).filter_by(gitlab_mr_id=mr["MR ID"]).first()
            if not existing_mr:
                new_mr = MergeRequest(
                    project_id=project.id,
                    gitlab_mr_id=mr["MR ID"],
                    title=mr["Title"],
                    description=mr["Description"],
                    state=mr["State"],
                    author_id=contributor.id,
                    gitlab_created_at=self._parse_date(mr["Created Date"]),
                    gitlab_updated_at=self._parse_date(mr["Updated Date"])
                )
                self.db.add(new_mr)
            else:
                existing_mr.state = mr["State"]
                existing_mr.gitlab_updated_at = self._parse_date(mr["Updated Date"])
        self.db.commit()

    def sync_issues(self, project_id):
        logger.info(f"Syncing Issues for Project {project_id}...")
        project = self.sync_projects(project_id)
        issues_data = self.get_issues(project_id)
        
        for issue in issues_data:
            assignee_id = None
            if issue["Assignee"]:
                contributor = self._get_or_create_contributor(issue["Assignee"], None)
                assignee_id = contributor.id

            existing_issue = self.db.query(Issue).filter_by(gitlab_issue_id=issue["Issue ID"]).first()
            labels_str = ",".join(issue["Labels"]) if issue["Labels"] else ""
            
            if not existing_issue:
                new_issue = Issue(
                    project_id=project.id,
                    gitlab_issue_id=issue["Issue ID"],
                    title=issue["Title"],
                    description=issue["Description"],
                    state=issue["State"],
                    labels=labels_str,
                    assignee_id=assignee_id,
                    gitlab_created_at=self._parse_date(issue["Created Date"])
                )
                self.db.add(new_issue)
            else:
                existing_issue.state = issue["State"]
                existing_issue.labels = labels_str
                existing_issue.assignee_id = assignee_id
        self.db.commit()

    def sync_repository_files(self, gitlab_project_id, internal_project_id, ref="main", max_files=150):
        logger.info("Syncing repository files for Project %s...", gitlab_project_id)
        tree = self.get_repository_tree(gitlab_project_id, ref=ref)
        files = tree.get("Files", [])[:max_files]
        file_count = 0
        doc_count = 0

        for path in files:
            ext = Path(path).suffix.lower()
            if ext not in SUPPORTED_SOURCE_EXTENSIONS:
                continue

            content = self.get_file_content_at_ref(gitlab_project_id, path, ref=ref)
            if content is None:
                continue
            content = content[:MAX_SYNC_FILE_CHARS]

            file_obj = (
                self.db.query(File)
                .filter(File.project_id == internal_project_id, File.path == path)
                .first()
            )
            if not file_obj:
                file_obj = File(project_id=internal_project_id, path=path, content=content)
                self.db.add(file_obj)
                self.db.flush()
            else:
                file_obj.content = content

            if ext == ".md":
                doc = self.db.query(Documentation).filter(Documentation.file_id == file_obj.id).first()
                if not doc:
                    self.db.add(Documentation(title=path, content=content, file_id=file_obj.id))
                else:
                    doc.title = path
                    doc.content = content
                doc_count += 1

            file_count += 1

        self.db.commit()
        return file_count, doc_count
