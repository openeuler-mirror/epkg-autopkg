import os
import requests
from src.parse.basic_parse import BasicParse
from src.builder import scripts_path
from src.log import logger


class AutotoolsParse(BasicParse):
    def __init__(self, source):
        super().__init__(source)
        self.language = "C/C++"
        self.configure_file = "configure"

    def parse_metadata(self):
        self.init_metadata()
        self.init_scripts()

    def init_scripts(self):
        # TODO(self.scripts中增加编译函数)
        pass

    def detect_build_system(self):
        url = "https://api.pkgs.org/v1/search"
        params = {"query": self.pacakge_name}
        info = requests.get(url, params=params).json()
        self.metadata.setdefault("name", self.pacakge_name)
        self.metadata.setdefault("version", self.version)

    def make_generic_build(self):
        with open(os.path.join(scripts_path, self.run_script)) as f:
            f.write("#!/usr/bin/env bash" + os.linesep*2)
            f.write("source ./autotools.sh")
            f.write("prep")
            f.write("configure")
            f.write("build")
            f.write("install")
            f.write("echo \"build success\"")
