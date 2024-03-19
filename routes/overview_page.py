import yaml

import config


def get_services_links():
    """
    Get services links from a file.
    """
    if config.SERVICES_LINKS_PATH.is_file():
        return yaml.safe_load(config.SERVICES_LINKS_PATH.read_text())
    return yaml.safe_load(config.SERVICES_LINKS_EXAMPLE_PATH.read_text())
