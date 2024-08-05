# SPDX-License-Identifier: MIT
# Copyright (c) 2017 Shintaro Kaneko. All rights reserved.

import os
import sys
import requests
from src.parse.basic_parse import BasicParse
from src.builder import scripts_path
from src.log import logger
from src.config.config import configuration


class RubyParse(BasicParse):
    def __init__(self, source, version=""):
        super().__init__(source)
        self.language = "ruby"
        self.build_requires.add("ruby")
        self.build_requires.add("rubygems-devel")
        self.build_requires.add("ruby-devel")
        if version != "":
            self.version = version
        self.__url_v1 = f"https://rubygems.org/api/v1/gems/{self.pacakge_name}.json"
        self.__url_v2 = f"https://rubygems.org/api/v2/rubygems/{self.pacakge_name}/versions/{self.version}.json"
        self.compile_type = "ruby"

    def parse_metadata(self):
        self.init_metadata()
        self.init_scripts()

    def init_scripts(self):
        # TODO(self.scripts中增加编译函数)
        pass

    def detect_build_system(self):
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
                "source": {0: f"https://rubygems.org/downloads/{name}-{version}.gem"}
            }
            requires = []
            if "dependencies" in data and data["dependencies"]:
                if "development" in data["dependencies"] and isinstance(data["dependencies"]["development"], list):
                    for require in data["dependencies"]["development"]:
                        requires.append(require["name"] + " " + require["requirements"])
            self.metadata.setdefault("requires", requires)

    def make_generic_build(self):
        with open(os.path.join(scripts_path, self.run_script), "w") as f:
            f.write("#!/usr/bin/env bash" + os.linesep*3)
            f.write("source /root/ruby.sh" + os.linesep)
            self.write_build_requires(f)
            f.write("prep" + os.linesep)
            self.basic_general_build(f)
