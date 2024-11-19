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
import re
import yaml
from src.parse.basic_parse import BasicParse
from src.utils.cmd_util import check_makefile_exist
from src.config.yamls import yaml_path


class MesonParse(BasicParse):
    def __init__(self, source, version=""):
        super().__init__(source)
        self.language = "C/C++"
        self.meson_path = ""
        self.build_system = "meson"
        self.version = version if version != "" else source.version
        with open(os.path.join(yaml_path, f"{self.build_system}.yaml"), "r") as f:
            yaml_text = f.read()
        self.source = source
        self.metadata = yaml.safe_load(yaml_text)

    def check_compilation_file(self):
        if "autopkg" in self.metadata and "buildSystemFiles" in self.metadata["autopkg"]:
            build_system_file = self.metadata["autopkg"]["buildSystemFiles"]
            if build_system_file not in self.source.files:
                self.meson_path = check_makefile_exist(self.source.files, build_system_file)
                return self.meson_path != ""
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
                search_pattern = re.compile("project\('(\s+)'")
                if search_pattern.search(content):
                    self.source.name = search_pattern.findall(content)[0][0]
                if os.path.exists(os.path.join(path, "VERSION")):
                    with open(os.path.join(path, "VERSION"), "r") as f:
                        self.source.version = f.read()
