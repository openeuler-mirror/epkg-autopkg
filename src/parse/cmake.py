import os
import requests
from src.parse.basic_parse import BasicParse
from src.utils.cmd_util import check_makefile_exist
from src.builder import scripts_path


class CMakeParse(BasicParse):
    def __init__(self, name):
        super().__init__(name)
        self.language = "C/C++"
        self.compile_path = ""
        self.compile_type = "cmake"

    def check_configure_file(self, path):
        if "CMakeLists.txt" not in os.listdir(path):
            self.compile_path = check_makefile_exist(path)

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
        with open(os.path.join(scripts_path, self.run_script), "w") as f:
            f.write("#!/usr/bin/env bash" + os.linesep*3)
            f.write("source /root/autotools.sh" + os.linesep)
            self.write_build_requires(f)
            f.write("prep" + os.linesep)
            f.write("cmake" + os.linesep)
            f.write("build" + os.linesep)
            f.write("install" + os.linesep)
            f.write("echo \"build success\"" + os.linesep)
