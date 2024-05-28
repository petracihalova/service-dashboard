import os
from pathlib import Path

DATA_PATH_FOLDER = "./data"
SERVICES_LINKS_PATH = Path(f"{DATA_PATH_FOLDER}/services_links.yml")

GITHUB_PR_LIST = Path(f"{DATA_PATH_FOLDER}/github_pr_list.json")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
GITHUB_PATTERN = (
    r"(?:https?://)?(?:www\.)?github\.com/(?P<owner>[\w-]+)/(?P<name>[\w-]+)/?"
)
GITHUB_MERGED_PR_LIST = Path(f"{DATA_PATH_FOLDER}/github_merged_pr_list.json")

GITLAB_PR_LIST = Path(f"{DATA_PATH_FOLDER}/gitlab_pr_list.json")
GITLAB_TOKEN = os.environ.get("GITLAB_TOKEN")
# all https://gitlab.cee.redhat.com repos exl "app-interface"
GITLAB_PATTERN = r"(?:https?://)?(?:www\.)?gitlab\.cee\.redhat\.com/(?P<owner>[\w-]+)/(?!app-interface)(?P<name>[\w-]+)/?"
