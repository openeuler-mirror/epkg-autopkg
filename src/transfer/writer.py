# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; specifically version 3 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
#
# See LICENSE for more details.


import os
import re
import yaml
from src.config.config import configuration


def repr_str(dumper, data):
    if '\n' in data:
        return dumper.represent_scalar(u'tag:yaml.org,2002:str', data, style='|')
    return dumper.org_represent_str(data)


class YamlWriter(object):
    def __init__(self, name, path):
        self.name = name
        self.path = path
        self.main_yaml = "package.yaml"
        self.file_yaml = "files.yaml"
        self.compile_script = "phase.sh"

    def create_yaml(self, metadata):
        with open(os.path.join(configuration.download_path, self.main_yaml), "w") as f:
            yaml.SafeDumper.org_represent_str = yaml.SafeDumper.represent_str
            yaml.add_representer(str, repr_str, Dumper=yaml.SafeDumper)
            f.write(yaml.safe_dump(metadata, sort_keys=False))

    def create_phase_script(self, metadata: dict):
        functions = {}
        # change spec-mode to dict-mode
        for _key, value in metadata.items():
            for phase in configuration.phase_member:
                if _key == phase or re.match(f"{phase}_\w+", _key):
                    functions[_key] = value
        # write function dict into shell file
        with open(os.path.join(configuration.download_path, self.compile_script), "w") as ph:
            if "phase_content" in metadata and isinstance(metadata["phase_content"], str):
                ph.write(metadata["phase_content"])
            for function, text in functions.items():
                ph.write(f"function {function}() " + "{" + os.linesep)
                ph.write(text.strip())
                ph.write("}" + os.linesep * 3)

    def create_files(self, metadata):
        files_data = {}
        for package, file in metadata.items():
            if package == "files":
                files_data.setdefault("files", os.linesep.join(list(file)))
            elif package.startswith("subpackage.") and package.endswith(".files"):
                files_data.setdefault(f"subpackage.{package}.files", os.linesep.join(list(file)))
        with open(os.path.join(configuration.download_path, self.file_yaml), "w") as f:
            yaml.SafeDumper.org_represent_str = yaml.SafeDumper.represent_str
            yaml.add_representer(str, repr_str, Dumper=yaml.SafeDumper)
            f.write(yaml.safe_dump(files_data, sort_keys=False))

    def create_yaml_package(self, metadata):
        self.create_yaml(metadata)
        self.create_files(metadata)
        self.create_phase_script(metadata)
