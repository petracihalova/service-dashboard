import json
from datetime import datetime

from utils.model import PullRequestInfo


class PullRequestEncoder(json.JSONEncoder):
    def default(self, obj):
        """JSON serializer for the PullRequestInfo class."""
        if isinstance(obj.created_at, datetime):
            created_at = obj.created_at.isoformat() if obj.created_at else None
        else:
            created_at = obj.created_at

        if isinstance(obj.merged_at, datetime):
            merged_at = obj.merged_at.isoformat() if obj.merged_at else None
        else:
            merged_at = obj.merged_at

        if isinstance(obj.closed_at, datetime):
            closed_at = obj.closed_at.isoformat() if obj.closed_at else None
        else:
            closed_at = obj.closed_at

        if isinstance(obj, PullRequestInfo):
            return {
                "number": obj.number,
                "draft": obj.draft,
                "title": obj.title,
                "description": obj.body,
                "created_at": created_at,
                "merged_at": merged_at,
                "merge_commit_sha": obj.merge_commit_sha,
                "user_login": obj.user_login,
                "html_url": obj.html_url,
                "branch": obj.branch,
                "closed_at": closed_at,
            }
        return super().default(obj)
