import os
import re
import yaml
from src.config.config import configuration


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
