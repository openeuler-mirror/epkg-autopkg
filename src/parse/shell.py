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
from src.parse.basic_parse import BasicParse
from src.builder import scripts_path
from src.config.config import configuration


class ShellParse(BasicParse):
    def __init__(self, name):
        super().__init__(name)
        self.language = "shell"
        self.shell_compile_files = ["autogen.sh", "build.sh", "compile.sh"]
        self.compile_type = "autogen"

    def check_compile_file(self, file):
        return file in self.shell_compile_files

    def parse_metadata(self):
        self.init_metadata()
        self.init_scripts()

    def init_scripts(self):
        # TODO(self.scripts中增加编译函数)
        pass
