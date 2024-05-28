import json

import config
import github_api
import gitlab_api


def get_github_open_pr(reload_data):
    """
    Get GitHub open pull requests from a file or download new data.
    """
    if config.GITHUB_TOKEN:
        if not config.GITHUB_PR_LIST.is_file() or reload_data:
            return github_api.get_open_pull_request()
    else:
        if not config.GITHUB_PR_LIST.is_file():
            return {}

    with open(config.GITHUB_PR_LIST, mode="r", encoding="utf-8") as file:
        return json.load(file)


def get_gitlab_open_pr(reload_data):
    """
    Get GitLub open pull requests from a file or download new data.
    """
    if config.GITLAB_TOKEN:
        if not config.GITLAB_PR_LIST.is_file() or reload_data:
            return gitlab_api.get_open_pull_request()
    else:
        if not config.GITLAB_PR_LIST.is_file():
            return {}

    with open(config.GITLAB_PR_LIST, mode="r", encoding="utf-8") as file:
        return json.load(file)
