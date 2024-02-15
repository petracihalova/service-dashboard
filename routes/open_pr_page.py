import json

import config
import github_api


def get_github_open_pr(reload_data):
    if config.GITHUB_PR_LIST.is_file() and not reload_data:
        with open(config.GITHUB_PR_LIST, mode="r", encoding="utf-8") as file:
            return json.load(file)
    
    return github_api.get_open_pull_request()
