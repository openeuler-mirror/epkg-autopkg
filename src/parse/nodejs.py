import os
import json
import sys
from urllib import request
from src.parse.basic_parse import BasicParse
from src.log import logger
from src.builder import scripts_path
from src.config.config import configuration


class NodejsParse(BasicParse):
    def __init__(self, name):
        super().__init__(name)
        self.language = "javascript"
        self.build_requires.add("npm")
        self.__url = f"https://registry.npmjs.org/{self.pacakge_name}/{self.version}"
        self.compile_type = "nodejs"

    def update_metadata(self):
        self.metadata.setdefault("buildRequires", self.build_requires)

    def parse_metadata(self):
        self.init_metadata()
        self.init_scripts()

    def init_scripts(self):
        # TODO(self.scripts中增加编译函数)
        pass

    def detect_build_system(self):
        with request.urlopen(self.__url) as u:
            data = json.loads(u.read().decode('utf-8'))
        if data is None:
            logger.error("can't get info from upstream")
            sys.exit(5)
        self.metadata.setdefault("name", self.pacakge_name)
        self.metadata.setdefault("version", self.version)
        self.metadata.setdefault("meta", {}).setdefault("summary", data["description"])
        self.metadata.setdefault("meta", {}).setdefault("description", data["description"])
        self.get_homepage(data)
        self.get_license(data)

    def get_homepage(self, data):
        if "homepage" in data:
            self.metadata.setdefault("homepage", data["homepage"])
        elif "repository" in data:
            self.metadata.setdefault("homepage", data["repository"]["homepage"])
        else:
            self.metadata.setdefault("homepage", "homepage")

    def get_license(self, data):
        if "license" in data:
            self.metadata.setdefault("license", data["license"])
        elif "licenses" in data:
            self.metadata.setdefault("license", data["licenses"][0]["type"])
        else:
            logger.error("can't get license from upstream")
            sys.exit(5)

    def make_generic_build(self):
        with open(os.path.join(scripts_path, self.run_script), "w") as f:
            f.write("#!/usr/bin/env bash" + os.linesep*3)
            f.write("source /root/nodejs.sh" + os.linesep)
            self.write_build_requires(f)
            f.write("prep" + os.linesep)
            f.write("build" + os.linesep)
            f.write("install" + os.linesep)
            f.write("if [ $? -eq 0 ]; then" + os.linesep)
            f.write(f"  echo \"{configuration.build_success_echo}\"{os.linesep}")
            f.write("fi" + os.linesep)
