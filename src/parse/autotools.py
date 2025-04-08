# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; specifically version 3 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
#
# See LICENSE for more details.

import os
import re
import yaml
from src.parse.basic_parse import BasicParse
from src.utils.cmd_util import check_makefile_exist
from src.config.config import configuration


class AutotoolsParse(BasicParse):
    def __init__(self, source, version=""):
        super().__init__(source)
        self.build_system = "autotools" # use buildSystem?
        self.version = version if version != "" else source.version
        with open(os.path.join(configuration.yaml_path, f"{self.build_system}.yaml"), "r") as f:
            yaml_text = f.read()
        self.configure_path = ""
        self.metadata = yaml.safe_load(yaml_text)
        self.source = source

    def check_compilation_file(self):
        if "autopkg" in self.metadata and "buildSystemFiles" in self.metadata["autopkg"]:
            build_system_file = self.metadata["autopkg"]["buildSystemFiles"]
            if build_system_file in self.source.files:
                return True
            if "configure" not in self.source.files:
                self.configure_path = check_makefile_exist(self.source.files, file_name="configure")
                if self.configure_path != "":
                    self.metadata["configurePath"] = self.configure_path
                return self.configure_path != ""
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
                search_pattern = re.compile("AC_INIT\(\[(.*)], \[(.*)], \[(.*)]")
                if search_pattern.search(content):
                    self.source.name, self.source.version, self.source.url = search_pattern.findall(content)[0]
