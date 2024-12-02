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
import re
import yaml
from src.log import logger
from src.builder import scripts_path
from src.utils.scanner import scan_for_meta, scan_for_license
from src.config.config import configuration
from src.config.yamls import yaml_path


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
            self.url = f"https://localhost:8000/{self.pacakge_name}-{self.version}.tar.gz"
        self.metadata.setdefault("meta", scan_for_meta(self.dirn))
        self.metadata.setdefault("name", self.pacakge_name)
        self.metadata.setdefault("version", self.version)
        self.metadata.setdefault("homepage", self.url)
        self.metadata.setdefault("license", scan_for_license(self.dirn))
        self.metadata.setdefault("source", {}).setdefault("0", self.url)
        self.metadata.setdefault("release", self.release)
        self.files.setdefault("files", set())
        self.parse_mapping_result()

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

    def merge_phase_items(self, compilation=""):
        if compilation != "" and self.compilation == "":
            self.compilation = compilation
        with open(os.path.join(scripts_path, self.compilation + ".sh")) as f:
            content = f.read()
        self.metadata.setdefault("phase_content", content)

    def parse_mapping_result(self):
        requires = []
        mapping_result_path = os.path.join(configuration.download_path, "package-mapping-result.yaml")
        if os.path.exists(mapping_result_path):
            with open(mapping_result_path, "r") as f:
                mapping_result_content = f.read()
            mapping_result = yaml.safe_load(mapping_result_content)
            for k, reqs in mapping_result.items():
                if "buildRequires" in k:
                    for dependency in reqs:
                        if dependency not in requires:
                            requires.append(dependency)
        if requires:
            self.metadata.setdefault("buildRequires", requires)

    def get_basic_info(self, build_system):
        with open(os.path.join(yaml_path, f"{build_system}.yaml"), "r") as f:
            content = f.read()
        self.metadata.update(yaml.safe_load(content))
        self.init_metadata()

    def generate_metadata(self):
        metadata = self.metadata.copy()
        if "phase_content" in metadata:
            del metadata["phase_content"]
        return metadata

