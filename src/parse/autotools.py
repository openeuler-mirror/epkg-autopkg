# SPDX-License-Identifier: MIT
# Copyright (c) 2017 Shintaro Kaneko. All rights reserved.

import os
import requests
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
        self.init_scripts()

    def init_scripts(self):
        # TODO(self.scripts中增加编译函数)
        pass

    def write_configure_flags(self, obj):
        if self.configureFlags is not None:
            obj.write("export configureFlags=\"" + self.configureFlags + "\"")
