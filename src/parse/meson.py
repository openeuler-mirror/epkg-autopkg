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
from src.utils.cmd_util import check_makefile_exist
from src.builder import scripts_path
from src.config.config import configuration


class MesonParse(BasicParse):
    def __init__(self, name):
        super().__init__(name)
        self.language = "C/C++"
        self.compile_path = ""
        self.compile_type = "meson"

    def check_configure_file(self, path):
        if "meson.build" not in os.listdir(path):
            self.compile_path = check_makefile_exist(path)

    def parse_metadata(self):
        self.init_metadata()
        self.metadata.setdefault("buildSystem", "meson")
        self.init_scripts()

    def init_scripts(self):
        # TODO(self.scripts中增加编译函数)
        pass
