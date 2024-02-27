import os
from pathlib import Path

SERVICES_LINKS_EXAMPLE_PATH = Path("data/services_links_example.yml")
SERVICES_LINKS_PATH = Path("data/services_links.yml")

GITHUB_PR_LIST = Path("data/github_pr_list.json")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")

GITLAB_PR_LIST = Path("data/gitlab_pr_list.json")
GITLAB_TOKEN = os.environ.get("GITLAB_TOKEN")
