import os
import shutil

import yaml

import config


def get_services_links():
    """
    Get services links from a file.
    """
    if not config.SERVICES_LINKS_PATH.is_file():
        try:
            source = config.DATA_PATH_FOLDER / "test_data"
            dest = config.DATA_PATH_FOLDER
            for filename in os.listdir(source):
                source_file = os.path.join(source, filename)
                dest_file = os.path.join(dest, filename)
                if os.path.isfile(source_file):
                    shutil.copy2(source_file, dest_file)

        except (FileNotFoundError, PermissionError) as e:
            print(f"Error copying directory: {e}")

    return yaml.safe_load(config.SERVICES_LINKS_PATH.read_text())
