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
import requests
from src.parse.basic_parse import BasicParse
from src.builder import scripts_path
from src.config.config import configuration


class MakeParse(BasicParse):
    def __init__(self, name):
        super().__init__(name)
        self.language = "C/C++"
        self.build_requires.add("gcc")
        self.build_requires.add("make")
        self.compile_type = "make"
        self.makeFlags = None

    def parse_metadata(self):
        self.init_metadata()
        self.metadata.setdefault("buildSystem", "make")
        self.init_scripts()

    def init_scripts(self):
        # TODO(self.scripts中增加编译函数)
        pass

    def write_make_flags(self, obj):
        if self.makeFlags is not None:
            obj.write("export makeFlags=\"" + self.makeFlags + "\"")
