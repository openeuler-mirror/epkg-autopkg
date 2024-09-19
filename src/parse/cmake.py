# SPDX-License-Identifier: MIT
# Copyright (c) 2017 Shintaro Kaneko. All rights reserved.

import os
from src.parse.basic_parse import BasicParse
from src.utils.cmd_util import check_makefile_exist
from src.builder import scripts_path
from src.config.config import configuration


class CMakeParse(BasicParse):
    def __init__(self, name):
        super().__init__(name)
        self.language = "C/C++"
        self.compile_path = ""
        self.compile_type = "cmake"
        self.cmakeFlags = None

    def check_configure_file(self, path):
        if "CMakeLists.txt" not in os.listdir(path):
            self.compile_path = check_makefile_exist(path)

    def parse_metadata(self):
        self.init_metadata()
        self.init_scripts()

    def init_scripts(self):
        # TODO(self.scripts中增加编译函数)
        pass

    def write_cmake_flags(self, obj):
        if self.cmakeFlags is not None:
            obj.write("export cmakeFlags=\"" + self.cmakeFlags + "\"")
