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
import requests
from src.parse.basic_parse import BasicParse
from src.builder import scripts_path
from src.log import logger
from src.config.config import configuration


class PerlParse(BasicParse):
    def __init__(self, source, version=""):
        super().__init__(source)
        self.language = "perl"
        self.build_requires.add("perl")
        self.version = version if version != "" else source.version
        self.__url = f"https://fastapi.metacpan.org/v1/pod/{self.pacakge_name}"  # Moose
        self.compile_type = "perl"

    def parse_metadata(self):
        self.init_metadata()
        self.metadata.setdefault("buildSystem", "make")
        self.init_scripts()

    def init_scripts(self):
        # TODO(self.scripts中增加编译函数)
        pass

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

    def get_summary_from_content(self, text):
        return ""

    def get_description_from_content(self, text):
        return ""
