from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class PullRequestInfo:
    number: int
    draft: bool
    title: str
    body: str
    created_at: datetime
    merged_at: Optional[datetime]
    merge_commit_sha: str
    user_login: str
    html_url: str
    branch: str = ""
    closed_at: Optional[datetime] = None
    additions: Optional[int] = None
    deletions: Optional[int] = None
    changed_files: Optional[int] = None
