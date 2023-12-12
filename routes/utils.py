import os
import yaml


def file_exists(file):
    return os.path.exists(file)


def load_yml_from_file(file):
    with open(file, "r", encoding="utf-8") as file:
        return yaml.safe_load(file)
