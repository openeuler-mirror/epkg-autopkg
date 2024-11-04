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
import sys
import yaml
import requests
from src.parse.basic_parse import BasicParse
from src.utils.cmd_util import check_makefile_exist
from src.log import logger
from src.config.yamls import yaml_path


class PerlParse(BasicParse):
    def __init__(self, source, version=""):
        super().__init__(source)
        self.language = "perl"
        self.build_requires.add("perl")
        self.version = version if version != "" else source.version
        self.__url = f"https://fastapi.metacpan.org/v1/pod/{self.pacakge_name}"  # Moose
        self.build_system = "perl"
        with open(os.path.join(yaml_path, f"{self.build_system}"), "r") as f:
            yaml_text = f.read()
        self.metadata = yaml.safe_load(yaml_text)
        self.perl_path = ""

    def parse_api_info(self):
        params = {
            "content-type": "application/json"
        }
        response = requests.get(self.__url, params=params)
        if response.status_code != 200:
            logger.error("can't requests the info of " + self.pacakge_name)
            sys.exit(5)
        else:
            content = response.text  # perl接口请求只有纯文本数据类型
        self.metadata = {
            "name": self.pacakge_name,
            "version": self.version,
            "meta": {
                "summary": self.get_summary_from_content(content),
                "description": self.get_description_from_content(content)
            },
            "buildSystem": "perl"
        }

    def check_compile_file(self, path):
        if "meson.build" not in os.listdir(path):
            self.perl_path = check_makefile_exist(path, "*.pl")

    def get_summary_from_content(self, text):
        return ""

    def get_description_from_content(self, text):
        return ""
