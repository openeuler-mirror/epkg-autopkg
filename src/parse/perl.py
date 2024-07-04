import os
import sys
import requests
from src.parse.basic_parse import BasicParse
from src.builder import scripts_path
from src.log import logger


class PerlParse(BasicParse):
    def __init__(self, source):
        super().__init__(source)
        self.language = "perl"
        self.build_requires.add("perl")
        self.__url = f"https://fastapi.metacpan.org/v1/pod/{self.pacakge_name}"  # Moose

    def parse_metadata(self):
        self.init_metadata()
        self.init_scripts()

    def init_scripts(self):
        # TODO(self.scripts中增加编译函数)
        pass

    def detect_build_system(self):
        params = {
            "content-type": "text/plain"
        }
        response = requests.get(self.__url, params=params)
        if response.status_code != 200:
            logger.error("can't requests the info of " + self.pacakge_name)
            sys.exit(5)
        else:
            data = response.json()

    def make_generic_build(self):
        with open(os.path.join(scripts_path, self.run_script)) as f:
            f.write("#!/usr/bin/env bash" + os.linesep*2)
            f.write("source ./ruby.sh")
            f.write("prep")
            f.write("build")
            f.write("install")
            f.write("echo \"build success\"")
