
import os
import yaml
from src.log import logger


def read_config_file(path):
    if not os.path.exists(path):
        logger.error("no such file: " + path)
        return
    with open(path, "r") as f:
        data = yaml.safe_load(f.read())
    return parse_params(data)


def parse_params(args):
    return args
