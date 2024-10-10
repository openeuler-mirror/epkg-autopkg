# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; specifically version 2 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
#
# See LICENSE for more details.
#
# Copyright: Red Hat (c) 2023 and Avocado contributors

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
