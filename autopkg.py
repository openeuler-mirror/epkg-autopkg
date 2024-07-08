#!/usr/bin/python
# SPDX-License-Identifier: MulanPSL-2.0+
# Copyright (c) 2022 Huawei Technologies Co., Ltd. All rights reserved.

import os
import sys
import argparse
from src.log import logger
from src.config.config import configuration
from src.yaml_maker import YamlMaker

sys.path.append(os.path.dirname(__file__))


def check_arg_mode(**kwargs):
    _name = kwargs.get("name")
    _url = kwargs.get("url")
    _dir = kwargs.get("directory")
    _version = kwargs.get("version")
    _language = kwargs.get("language")
    count = 0
    for value in [_name, _url, _dir]:
        if value != "":
            count += 1
    if count != 1:
        logger.error("Must input only one arg by -n/-u/-d")
        sys.exit(1)
    if _name != "" and (_version == "" or _language == ""):
        logger.error("When you input -n, you need to input -v and -l at the same time")
        sys.exit(1)


def set_output_dir(path):
    if os.path.exists(path):
        os.system("rm -rf " + path)
    os.makedirs(path, exist_ok=True)


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("-u", "--url", dest="url", default="",
                        help="http URL of downloading package")
    parser.add_argument("-d", "--dir", dest="directory", default="",
                        help="cloned repository of package")
    parser.add_argument("-n", "--name", dest="name", default="",
                        help="pacakge name")
    parser.add_argument("-v", "--version", dest="version", default="",
                        help="version with pacakge name")
    parser.add_argument("-l", "--language", dest="language", default="",
                        help="language with pacakge name")
    parser.add_argument("-o", "--output", dest="output", default="/tmp/autopkg/output",
                        help="Target location to create or reuse")
    parser.add_argument("-b", "--build", dest="build", default="true", choices=["true", "false"],
                        help="Target location to create or reuse")
    parser.add_argument("-c", "--config", dest="config", action="store", default="",
                        help="Set configuration file to use")
    args = parser.parse_args()
    name = args.name
    language = args.language
    version = args.version
    url = args.url
    build_param = args.build
    need_build = build_param == "true"
    directory = args.directory
    output = args.output
    os.makedirs(output, exist_ok=True)
    check_arg_mode(name=name, url=url, directory=directory, version=version, language=language)
    config_file = args.config
    configuration.download_path = output
    set_output_dir(output)
    yaml_maker = YamlMaker(name=name, url=url, directory=directory, need_build=need_build)
    yaml_maker.create_yaml()
