from dataclasses import dataclass
from datetime import datetime


@dataclass
class PullRequestInfo:
    number: int
    draft: bool
    title: str
    body: str
    created_at: datetime
    merged_at: datetime | None
    merge_commit_sha: str
    user_login: str
    html_url: str
    branch: str = ""
    closed_at: datetime | None = None
    additions: int | None = None
    deletions: int | None = None
    changed_files: int | None = None
    days_open: int | None = None
