# Copyright (c) [2023] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#       http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

import os
import re
import yaml
from src.parse.basic_parse import BasicParse
from src.utils.cmd_util import check_makefile_exist
from src.config.config import configuration


class CMakeParse(BasicParse):
    def __init__(self, source, version=""):
        super().__init__(source)
        self.language = "C/C++"
        self.cmake_path = ""
        self.build_system = "cmake"
        self.version = version if version != "" else source.version
        self.source = source
        with open(os.path.join(configuration.yaml_path, f"{self.build_system}.yaml"), "r") as f:
            yaml_text = f.read()
        self.metadata = yaml.safe_load(yaml_text)

    def check_compilation_file(self):
        if "autopkg" in self.metadata and "buildSystemFiles" in self.metadata["autopkg"]:
            build_system_file = self.metadata["autopkg"]["buildSystemFiles"]
            if build_system_file not in self.source.files:
                self.cmake_path = check_makefile_exist(self.source.files)
                if self.cmake_path != "":
                    self.metadata["cmakePath"] = self.cmake_path
                return self.cmake_path != ""
            return True
        return False

    def check_compilation(self):
        return self.check_compilation_file()

    def fix_name_version(self, path):
        if "autopkg" in self.metadata and "buildSystemFiles" in self.metadata["autopkg"]:
            build_system_file = self.metadata["autopkg"]["buildSystemFiles"]
            if self.source.name == "" and self.source.version == "":
                if build_system_file not in self.source.files:
                    return
                with open(os.path.join(path, build_system_file), "r") as f:
                    content = f.read()
                search_pattern = re.compile("project\((.*) VERSION (\s+) (.*)\)")
                if search_pattern.search(content):
                    self.source.name, self.source.version, self.source.url = search_pattern.findall(content)[0]
