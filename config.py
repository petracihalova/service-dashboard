import os
from pathlib import Path


MOCK_DATA = os.environ.get("MOCK_DATA", "False").lower() in ("true", "1")
data_folder = "data" if not MOCK_DATA else "data_mock"

SERVICES_LINKS_EXAMPLE_PATH = Path(f"{data_folder}/services_links_example.yml")
SERVICES_LINKS_PATH = Path(f"{data_folder}/services_links.yml")

# GitHub
GITHUB_PR_LIST = Path(f"{data_folder}/github_pr_list.json")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
GITHUB_PATTERN = (
    r"(?:https?://)?(?:www\.)?github\.com/(?P<owner>[\w-]+)/(?P<name>[\w-]+)/?"
)
GITHUB_MERGED_PR_LIST = Path(f"{data_folder}/github_merged_pr_list.json")

# GitLab https://gitlab.cee.redhat.com
GITLAB_PR_LIST = Path(f"{data_folder}/gitlab_pr_list.json")
GITLAB_TOKEN = os.environ.get("GITLAB_TOKEN")
# all repos exl "app-interface"
GITLAB_PATTERN = r"(?:https?://)?(?:www\.)?gitlab\.cee\.redhat\.com/(?P<owner>[\w-]+)/(?!app-interface)(?P<name>[\w-]+)/?"
