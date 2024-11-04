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
from src.config.yamls import yaml_path


class Autogen(BasicParse):
    def __init__(self, name):
        super().__init__(name)
        self.shell_compile_files = ["autogen.sh", "build.sh", "compile.sh"]
        self.build_system = "autogen"
        with open(os.path.join(yaml_path, f"{self.build_system}"), "r") as f:
            yaml_text = f.read()
        self.metadata = yaml.safe_load(yaml_text)

    def check_compile_file(self, path):
        for shell_compile_file in self.shell_compile_files:
            return shell_compile_file in os.listdir(path)
