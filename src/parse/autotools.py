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


class AutotoolsParse(BasicParse):
    def __init__(self, source, version=""):
        super().__init__(source)
        self.build_system = "autotools" # use buildSystem?
        self.version = version if version != "" else source.version
        with open(os.path.join(yaml_path, f"{self.build_system}.yaml"), "r") as f:
            yaml_text = f.read()
        self.configure_path = ""
        self.metadata = yaml.safe_load(yaml_text)
        self.source = source

    def check_compile_file(self, path):
        if "configure" not in os.listdir(path):
            self.configure_path = check_makefile_exist(path, file_name="configure")
