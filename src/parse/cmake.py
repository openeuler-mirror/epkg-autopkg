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
from src.parse.basic_parse import BasicParse
from src.utils.cmd_util import check_makefile_exist
from src.builder import scripts_path
from src.config.yamls import yaml_path


class CMakeParse(BasicParse):
    def __init__(self, name):
        super().__init__(name)
        self.language = "C/C++"
        self.cmake_path = ""
        self.build_system = "cmake"
        with open(os.path.join(yaml_path, f"{self.build_system}.yaml"), "r") as f:
            yaml_text = f.read()
        self.metadata = yaml.safe_load(yaml_text)

    def check_compile_file(self, path):
        if "CMakeLists.txt" not in os.listdir(path):
            self.build_system = check_makefile_exist(path)

    def parse_metadata(self):
        self.init_metadata()
