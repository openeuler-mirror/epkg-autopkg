# This file contains code derived from autospec (©openeuler) under the GNU General Public License v3.0 (GPL-3.0).
# Original source: https://gitee.com/openeuler/perlporter
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

import os
import sys
import yaml
import requests
from src.parse.basic_parse import BasicParse
from src.log import logger
from src.config.config import configuration


class PerlParse(BasicParse):
    def __init__(self, source, version=""):
        super().__init__(source)
        self.language = "perl"
        self.build_requires.add("perl")
        self.version = version if version != "" else source.version
        self.__url = f"https://fastapi.metacpan.org/v1/pod/{self.pacakge_name}"  # Moose
        self.build_system = "perl"
        with open(os.path.join(configuration.yaml_path, f"{self.build_system}.yaml"), "r") as f:
            yaml_text = f.read()
        self.metadata = yaml.safe_load(yaml_text)
        self.perl_path = ""
        self.source = source

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

    def check_compilation_file(self):
        count = 0
        for file in self.source.files:
            if file.endswith(".pl"):
                count += 1
            if count > 10:
                return True
        return False


    def get_summary_from_content(self, text):
        return ""

    def get_description_from_content(self, text):
        return ""

    def check_compilation(self):
        return self.check_compilation_file()
