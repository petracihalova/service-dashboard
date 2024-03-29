import os
from pathlib import Path

SERVICES_LINKS_EXAMPLE_PATH = Path("data/services_links_example.yml")
SERVICES_LINKS_PATH = Path("data/services_links.yml")

GITHUB_PR_LIST = Path("data/github_pr_list.json")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
GITHUB_PATTERN = (
    r"(?:https?://)?(?:www\.)?github\.com/(?P<owner>[\w-]+)/(?P<name>[\w-]+)/?"
)
GITHUB_MERGED_PR_LIST = Path("data/github_merged_pr_list.json")

GITLAB_PR_LIST = Path("data/gitlab_pr_list.json")
GITLAB_TOKEN = os.environ.get("GITLAB_TOKEN")
# all https://gitlab.cee.redhat.com repos exl "app-interface"
GITLAB_PATTERN = r"(?:https?://)?(?:www\.)?gitlab\.cee\.redhat\.com/(?P<owner>[\w-]+)/(?!app-interface)(?P<name>[\w-]+)/?"
