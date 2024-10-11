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


class AutotoolsParse(BasicParse):
    def __init__(self, source, version=""):
        super().__init__(source)
        self.language = "C/C++"
        self.compile_type = "autotools"
        self.configureFlags = None
        self.version = version if version != "" else source.version
        self.source = source

    def parse_metadata(self):
        self.init_metadata()
        self.metadata.setdefault("buildSystem", "make")
        self.init_scripts()

    def init_scripts(self):
        # TODO(self.scripts中增加编译函数)
        pass

    def write_configure_flags(self, obj):
        if self.configureFlags is not None:
            obj.write("export configureFlags=\"" + self.configureFlags + "\"")
