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
import sys
import requests
from src.parse.basic_parse import BasicParse
from src.log import logger
from src.utils.cmd_util import check_makefile_exist
from src.config.yamls import yaml_path


class NodejsParse(BasicParse):
    def __init__(self, source, version=""):
        super().__init__(source)
        self.version = version if version != "" else source.version
        self.__url = f"https://registry.npmjs.org/{self.pacakge_name}/{self.version}"
        self.build_system = "nodejs"
        self.npm_path = ""
        with open(os.path.join(yaml_path, f"{self.build_system}.yaml"), "r") as f:
            yaml_text = f.read()
        self.metadata = yaml.safe_load(yaml_text)

    def parse_api_info(self):
        response = requests.get(self.__url)
        if response.status_code != 200:
            logger.error("can't requests the info of " + self.pacakge_name)
            sys.exit(5)
        else:
            data = response.json()
        if data is None:
            logger.error("can't get info from upstream")
            sys.exit(5)
        name = data["name"] if "name" in data else self.pacakge_name
        self.metadata = {
            "name": name,
            "version": data["version"],
            "meta": {
                "summary": data["description"],
                "description": data["description"]
            },
            "license": self.get_license(data),
            "release": 1,
            "homepage": f"https://www.npmjs.com/package/{name}",
            "source": {0: data["repository"]["url"]},
            "buildRequires": ["npm"],
            "buildSystem": "nodejs"
        }
        requires = []
        if "dependencies" in data and isinstance(data["dependencies"], dict):
            for k, v in data["dependencies"].items():
                if v.startswith("^"):
                    requires.append(k + " >= " + v.lstrip("^"))
                else:
                    requires.append(k + " = " + v)
        self.metadata.setdefault("requires", requires)

    def get_license(self, data):
        if "license" in data:
            self.metadata.setdefault("license", data["license"])
        elif "licenses" in data:
            self.metadata.setdefault("license", data["licenses"][0]["type"])
        else:
            logger.error("can't get license from upstream")
            sys.exit(5)

    def check_compile_file(self, path):
        if "meson.build" not in os.listdir(path):
            self.npm_path = check_makefile_exist(path, "meson.build")
