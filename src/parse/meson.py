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
        if "meson.build" not in self.source.files:
            self.meson_path = check_makefile_exist(self.source.files, "meson.build")
            return self.meson_path != ""
        return False

    def check_compilation(self):
        return self.check_compilation_file()
