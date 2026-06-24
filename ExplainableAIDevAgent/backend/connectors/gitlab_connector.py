from backend.services.gitlab_service import GitLabService


class GitLabConnector(GitLabService):
    """
    GitLab data collector used by ProjectMind AI.

    Kept as a connector wrapper so the SaaS-facing architecture reads:
    connectors -> database -> knowledge engine -> AI services -> dashboard.
    """

