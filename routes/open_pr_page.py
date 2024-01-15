import json

import config
import github_api


def get_github_open_pr(reload_data):
    if not config.GITHUB_PR_LIST.is_file() or reload_data:
        github_api.get_open_pull_request()

    with open(config.GITHUB_PR_LIST, mode="r", encoding="utf-8") as file:
        github_open_pr = json.load(file)

    return github_open_pr
