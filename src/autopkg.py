#!/usr/bin/python
# SPDX-License-Identifier: MulanPSL-2.0+
# Copyright (c) 2022 Huawei Technologies Co., Ltd. All rights reserved.

import os
import sys
import argparse

from src.log import logger
from src.source import Source
from src.config.config import BuildConfig
from src.transfer.writer import SpecWriter, YamlWriter


def check_only_one_arg(**kwargs):
    count = 0
    for arg, value in kwargs.items():
        if value is not None:
            count += 1
    return count


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("-u", "--url", dest="url", default="",
                        help="http URL of downloading package")
    parser.add_argument("-d", "--dir", dest="directory", default="",
                        help="cloned repository of package")
    parser.add_argument("-n", "--pkg_name", dest="name", default="",
                        help="pacakge name")
    parser.add_argument("-o", "--output", dest="output", default="/tmp/autopkg/output",
                        help="Target location to create or reuse")
    parser.add_argument("-p", "--parse", dest="parse", default="true", choices=["true", "false"],
                        help="Target location to create or reuse")
    parser.add_argument("-b", "--build", dest="build", default="true", choices=["true", "false"],
                        help="Target location to create or reuse")
    args = parser.parse_args()
    name = args.get("name")
    url = args.get("url")
    parse_param = args.get("parse")
    need_parse = parse_param == "true"
    build_param = args.get("build")
    need_build = build_param == "true"
    directory = args.get("directory")
    output = args.get("output")
    os.makedirs(output, exist_ok=True)
    arg_result = check_only_one_arg(name=name, url=url, directory=directory)
    if arg_result != 1:
        logger.error("args error, choose one from '-U/-D/-n'")
        sys.exit(0)
    BuildConfig.download_path = output
    content = Source(url, name, directory)
    metadata = content.process(need_parse, need_build)
    spec_writer = SpecWriter(name, BuildConfig.download_path)
    yaml_writer = YamlWriter(name, BuildConfig.download_path)
    spec_writer.trans_data_to_spec(metadata)
    yaml_writer.create_yaml_package(metadata)
