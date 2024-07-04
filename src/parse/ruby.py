import os
import sys

import requests
from src.parse.basic_parse import BasicParse
from src.builder import scripts_path
from src.log import logger


class AutotoolsParse(BasicParse):
    def __init__(self, source):
        super().__init__(source)
        self.language = "ruby"
        self.build_requires.add("ruby")
        self.build_requires.add("rubygems-devel")
        self.build_requires.add("ruby-devel")

    def parse_metadata(self):
        self.init_metadata()
        self.init_scripts()

    def init_scripts(self):
        # TODO(self.scripts中增加编译函数)
        pass

    def parse_info_from_upstream(self):
        url = f"https://rubygems.org/api/v1/gems/{self.pacakge_name}.json"
        response = requests.get(url)
        if response.status_code != 200:
            logger.error("can't requests the info of " + self.pacakge_name)
            sys.exit(5)
        else:
            data = response.json()
            self.metadata.setdefault("name", data['name'])
            self.metadata.setdefault("version", data['version'])
            self.metadata.setdefault("meta", {}).setdefault("summary", data['summary'])
            self.metadata.setdefault("meta", {}).setdefault("description", data['description'])


    def make_generic_build(self):
        with open(os.path.join(scripts_path, self.run_script)) as f:
            f.write("#!/usr/bin/env bash" + os.linesep*2)
            f.write("source ./ruby.sh")
            f.write("prep")
            f.write("build")
            f.write("install")
