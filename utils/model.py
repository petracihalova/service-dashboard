from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class PullRequestInfo:
    number: int
    draft: bool
    title: str
    created_at: datetime
    merged_at: Optional[datetime]
    user_login: str
    html_url: str
