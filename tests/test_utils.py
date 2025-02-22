import config
import utils


def test_get_repos_info_success():
    links = {
        "categories": [
            {
                "category_name": "Github",
                "category_repos": [
                    {
                        "id": "rbac",
                        "name": "RBAC",
                        "links": [
                            {
                                "link_name": "GH repo",
                                "link_value": "https://github.com/redhatinsights/insights-rbac",
                            }
                        ],
                    },
                    {
                        "id": "abc",
                        "name": "ABC",
                        "links": [
                            {
                                "link_name": "Documentation",
                                "link_value": "https://not-existing-documentation.abc",
                            }
                        ],
                    },
                ],
            }
        ]
    }
    expected_owner = "redhatinsights"
    expected_repo_name = "insights-rbac"

    result = utils.get_repos_info(links, config.GH_REPO_PATTERN)

    assert len(result) == 1
    assert result[0].owner == expected_owner
    assert result[0].repo_name == expected_repo_name


def test_get_repost_info_empty():
    links = {}
    result = utils.get_repos_info(links, config.GH_REPO_PATTERN)

    assert len(result) == 0
