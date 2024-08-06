# SPDX-License-Identifier: MIT
# Copyright (c) 2017 Shintaro Kaneko. All rights reserved.

import os
import re
import yaml
from src.log import logger
from src.utils.scanner import scan_for_meta, scan_for_license
from src.config.config import configuration


class BasicParse:
    def __init__(self, source):
        self.language = ""
        self.compilation = ""
        self.url = source.url
        self.dirn = source.path
        self.version = source.version
        self.license = ""
        self.release = source.release
        self.build_commands = []
        self.install_commands = []
        self.build_requires = set()
        self.pacakge_name = source.name
        self.metadata = {}
        self.files = {}
        self.files_blacklist = set()
        self.scripts = {}
        self.run_script = "generic-build.sh"

    def init_metadata(self):
        if self.url == "" and self.pacakge_name:
            self.url = f"https://localhost:8080/{self.pacakge_name}-0.0.1.tar.gz"
        self.metadata.setdefault("rpmGlobal", {}).setdefault("debug_package", "%{nil}")
        self.metadata["rpmGlobal"]["__strip"] = "/bin/true"
        self.metadata.setdefault("meta", scan_for_meta(self.dirn))
        self.metadata.setdefault("name", self.pacakge_name)
        self.metadata.setdefault("version", self.version)
        self.metadata.setdefault("homepage", self.url)
        self.metadata.setdefault("license", scan_for_license(self.dirn))
        self.metadata.setdefault("source", {}).setdefault("0", self.url)
        self.metadata.setdefault("release", self.release)
        self.files.setdefault("files", set())

    def clean_directories(self, sub_name):
        """Remove directories from file list."""
        removed = False
        del_sub = ""
        for pkg in self.metadata:
            if sub_name in pkg and ".files" in pkg:
                removed = True
                del_sub = pkg
                break
        if removed:
            del self.metadata[del_sub]
        return removed

    def merge_files(self):
        self.metadata.update(self.files)

    def write_config(self, yaml_file="package.yaml"):
        # 输入：字典数据self.metadata,self.scripts。输出：package.yaml,phase.sh
        content = yaml.safe_dump(self.metadata)
        with open(yaml_file, "w") as f:
            f.write(content)
        # TODO(write phase.sh from self.scripts)

    def write_build_requires(self, obj):
        buildreqs = self.metadata.get("buildRequires")
        if buildreqs:
            line = "yum install -y " + " ".join(list(buildreqs))
            obj.write(line)
