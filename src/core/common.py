# SPDX-License-Identifier: MIT
# Copyright (c) 2017 Shintaro Kaneko. All rights reserved.

import os
import requests
from src.log import logger
from src.config.config import configuration
from src.utils.cmd_util import check_makefile_exist


def verify_metadata(data):
    if "phase.build" in data:
        data["phase.build"] = merge_build_pattern(data["phase.build"])
    # TODO(列举需要合并的字段)


def merge_build_pattern(data):
    # TODO(合并多编译类型)
    return data
