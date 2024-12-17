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
from src.log import logger
from src.config.config import configuration


class RubyParse(BasicParse):
    def __init__(self, source, version=""):
        super().__init__(source)
        if version != "":
            self.version = version
        self.__url_v1 = f"https://rubygems.org/api/v1/gems/{self.pacakge_name}.json"
        self.__url_v2 = f"https://rubygems.org/api/v2/rubygems/{self.pacakge_name}/versions/{self.version}.json"
        self.build_system = "ruby"
        with open(os.path.join(configuration.yaml_path, f"{self.build_system}.yaml"), "r") as f:
            yaml_text = f.read()
        self.metadata = yaml.safe_load(yaml_text)
        self.source = source

    def parse_api_info(self):
        response = requests.get(self.__url_v1)
        if response.status_code != 200:
            logger.error("can't requests the info of " + self.pacakge_name)
            sys.exit(5)
        else:
            data = response.json()
            name = data['name'] if data.get("name") else self.pacakge_name
            version = data['version'] if data.get("version") else self.version
            self.metadata = {
                "name": name,
                "version": version,
                "meta": {
                    "summary": data['info'],
                    "description": data['info']
                },
                "license": data['licenses'][0],
                "release": 1,
                "homepage": data['project_uri'],
                "sources": {0: f"https://rubygems.org/downloads/{name}-{version}.gem"},
                "buildSystem": "ruby"
            }
            requires = []
            if "dependencies" in data and data["dependencies"]:
                if "development" in data["dependencies"] and isinstance(data["dependencies"]["development"], list):
                    for require in data["dependencies"]["development"]:
                        requires.append(require["name"] + " " + require["requirements"])
            self.metadata.setdefault("requires", requires)

    def check_compilation_file(self):
        for file in self.source.files:
            if file.endswith(".gemspec"):
                return True
        return False

    def check_compilation(self):
        return self.check_compilation_file()
