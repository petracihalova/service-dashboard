from routes.utils import file_exists, load_yml_from_file


import config


def get_services_links():
    if file_exists(config.SERVICES_LINKS_PATH):
        return load_yml_from_file(config.SERVICES_LINKS_PATH)
    else:
        return load_yml_from_file(config.SERVICES_LINKS_EXAMPLE_PATH)