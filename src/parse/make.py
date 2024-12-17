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
from src.config.config import configuration


class MakeParse(BasicParse):
    def __init__(self, source, version=""):
        super().__init__(source)
        self.build_system = "make"  # use buildSystem?
        self.version = version if version != "" else source.version
        with open(os.path.join(configuration.yaml_path, f"{self.build_system}.yaml"), "r") as f:
            yaml_text = f.read()
        self.make_path = ""
        self.metadata = yaml.safe_load(yaml_text)
        self.source = source

    def check_compilation_file(self,):
        if "autopkg" in self.metadata and "buildSystemFiles" in self.metadata["autopkg"]:
            build_system_file = self.metadata["autopkg"]["buildSystemFiles"]
            if build_system_file not in self.source.files:
                self.make_path = check_makefile_exist(self.source.files)
                if self.make_path != "":
                    self.metadata["makePath"] = self.make_path
                return self.make_path != ""
            return True
        return False

    def check_compilation(self):
        return self.check_compilation_file()
