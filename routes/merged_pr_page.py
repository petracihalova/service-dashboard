import json

import config
import github_api


def get_github_merged_pr(reload_data):
    """
    Get GitHub merged pull requests from a file or download new data.
    """
    if config.GITHUB_MERGED_PR_LIST.is_file() and not reload_data:
        with open(config.GITHUB_MERGED_PR_LIST, mode="r", encoding="utf-8") as file:
            return json.load(file)

    return github_api.get_merged_pull_request()
