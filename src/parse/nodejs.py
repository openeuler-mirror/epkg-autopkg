import os
import json
import sys
import requests
from src.parse.basic_parse import BasicParse
from src.log import logger
from src.builder import scripts_path
from src.config.config import configuration


class NodejsParse(BasicParse):
    def __init__(self, source, version=""):
        super().__init__(source)
        self.language = "javascript"
        self.build_requires.add("npm")
        self.version = version if version != "" else source.version
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
            "buildRequires": ["npm"]
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
