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

    def detect_build_system(self):
        url = "https://api.pkgs.org/v1/search"  # 收费API
        params = {"query": self.pacakge_name}
        info = requests.get(url, params=params)
        print(info.json())
        self.metadata.setdefault("name", self.pacakge_name)
        self.metadata.setdefault("version", self.version)

    def make_generic_build(self):
        with open(os.path.join(scripts_path, self.run_script), "w") as f:
            f.write("#!/usr/bin/env bash" + os.linesep*3)
            f.write("source /root/autotools.sh" + os.linesep)
            self.write_build_requires(f)
            self.write_configure_flags(f)
            f.write("prep" + os.linesep)
            f.write("configure" + os.linesep)
            f.write("build" + os.linesep)
            f.write("install" + os.linesep)
            f.write("if [ $? -eq 0 ]; then" + os.linesep)
            f.write(f"  echo \"{configuration.build_success_echo}\"{os.linesep}")
            f.write("fi" + os.linesep)

    def write_configure_flags(self, obj):
        if self.configureFlags is not None:
            obj.write("export configureFlags=\"" + self.configureFlags + "\"")
