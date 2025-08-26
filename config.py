import os
from pathlib import Path

# TOKENS, SECRETS
SECRET_KEY = os.environ.get("SECRET_KEY")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
GITLAB_TOKEN = os.environ.get("GITLAB_TOKEN")

# USERNAMES
GITHUB_USERNAME = os.environ.get("GITHUB_USERNAME", "")
GITLAB_USERNAME = os.environ.get("GITLAB_USERNAME", "")

# GITLAB HOST
GITLAB_HOST = "https://gitlab.cee.redhat.com"

# DATA FILES
base_dir = Path(__file__).resolve().parent
data_folder = "data"
DATA_PATH_FOLDER = base_dir / data_folder

SERVICES_LINKS_PATH = DATA_PATH_FOLDER / "services_links.yml"

GH_OPEN_PR_FILE = DATA_PATH_FOLDER / "github_pr_list.json"
GH_MERGED_PR_FILE = DATA_PATH_FOLDER / "github_merged_pr_list.json"

GL_OPEN_PR_FILE = DATA_PATH_FOLDER / "gitlab_pr_list.json"
GL_MERGED_PR_FILE = DATA_PATH_FOLDER / "gitlab_merged_pr_list.json"

DEPLOYMENTS_FILE = DATA_PATH_FOLDER / "deployments_list.json"

APP_INTERFACE_OPEN_MR_FILE = DATA_PATH_FOLDER / "app_interface_open_mr_list.json"
APP_INTERFACE_MERGED_MR_FILE = DATA_PATH_FOLDER / "app_interface_merged_mr_list.json"

# PATTERNS
GH_REPO_PATTERN = (
    r"(?:https?://)?(?:www\.)?github\.com/(?P<owner>[\w-]+)/(?P<name>[\w-]+)/?"
)
# all https://gitlab.cee.redhat.com repos exl "app-interface"
GL_REPO_PATTERN = r"(?:https?://)?(?:www\.)?gitlab\.cee\.redhat\.com/(?P<owner>[\w-]+)/(?!app-interface)(?P<name>[\w-]+)/?"

# PULL REQUESTS
DEFAULT_MERGED_IN_LAST_X_DAYS = 7

# DEPLOYMENTS
VALID_DEPLOY_CONFIG_FILES = ["deploy.yml", "deploy-clowder.yml"]
deploy_ignore_list = os.environ.get("DEPLOY_TEMPLATE_IGNORE_LIST", "")
DEPLOY_TEMPLATE_IGNORE_LIST = (
    [item.strip() for item in deploy_ignore_list.split(",")]
    if deploy_ignore_list
    else []
)
deployment_rename_list = os.environ.get("DEPLOYMENT_RENAME_LIST", "")

rename_list_dict = {}
if deployment_rename_list:
    for item in deployment_rename_list.split(","):
        key, value = item.strip().split(":")
        rename_list_dict[key.strip()] = value.strip()
DEPLOYMENT_RENAME_LIST = rename_list_dict

JIRA_PROJECT = os.environ.get("JIRA_PROJECT", "")
JIRA_PERSONAL_ACCESS_TOKEN = os.environ.get("JIRA_PERSONAL_ACCESS_TOKEN", "")
JIRA_SERVER = "https://issues.redhat.com"

# APP-INTERFACE CONFIG
app_interface_users_env = os.environ.get("APP_INTERFACE_USERS", "")
APP_INTERFACE_USERS = (
    [user.strip() for user in app_interface_users_env.split(",")]
    if app_interface_users_env
    else []
)
APP_INTERFACE_PATTERN = r"(?:https?://)?(?:www\.)?gitlab\.cee\.redhat\.com/service/app-interface/-/tree/master/data/services/insights/(?P<folder>[\w-]+)/?"
