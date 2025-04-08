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
import yaml
from src.parse.basic_parse import BasicParse
from src.config.config import configuration


class AutogenParse(BasicParse):
    def __init__(self, source, version=""):
        super().__init__(source)
        self.shell_compile_files = ["autogen.sh", "build.sh", "compile.sh"]
        self.build_system = "autogen"
        self.version = version if version != "" else source.version
        self.source = source
        with open(os.path.join(configuration.yaml_path, f"{self.build_system}.yaml"), "r") as f:
            yaml_text = f.read()
        self.metadata = yaml.safe_load(yaml_text)

    def check_compilation_file(self):
        for shell_compile_file in self.shell_compile_files:
            if shell_compile_file in self.source.files:
                return True
        return False

    def check_compilation(self):
        return self.check_compilation_file()
