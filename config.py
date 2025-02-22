import os
from pathlib import Path

# TOKENS, SECRETS
SECRET_KEY = os.environ.get("SECRET_KEY")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
GITLAB_TOKEN = os.environ.get("GITLAB_TOKEN")

# DATA FILES
base_dir = Path(__file__).resolve().parent
data_folder = "data"

SERVICES_LINKS_PATH = base_dir / data_folder / "services_links.yml"

GH_OPEN_PR_FILE = base_dir / data_folder / "github_pr_list.json"
GH_MERGED_PR_FILE = base_dir / data_folder / "github_merged_pr_list.json"

GL_OPEN_PR_FILE = base_dir / data_folder / "gitlab_pr_list.json"
GL_MERGED_PR_FILE = base_dir / data_folder / "gitlab_merged_pr_list.json"

# PATTERNS
GH_REPO_PATTERN = (
    r"(?:https?://)?(?:www\.)?github\.com/(?P<owner>[\w-]+)/(?P<name>[\w-]+)/?"
)
# all https://gitlab.cee.redhat.com repos exl "app-interface"
GL_REPO_PATTERN = r"(?:https?://)?(?:www\.)?gitlab\.cee\.redhat\.com/(?P<owner>[\w-]+)/(?!app-interface)(?P<name>[\w-]+)/?"
