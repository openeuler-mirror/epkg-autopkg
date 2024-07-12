import os
from src.parse.basic_parse import BasicParse
from src.builder import scripts_path


class MavenParse(BasicParse):
    def __init__(self, name):
        super().__init__(name)
        self.language = "java"
        self.build_requires.add("maven")
        self.compile_type = "maven"

    def update_metadata(self):
        self.metadata.setdefault("buildRequires", self.build_requires)

    def parse_metadata(self):
        self.init_metadata()
        self.init_scripts()

    def init_scripts(self):
        # TODO(self.scripts中增加编译函数)
        pass

    def make_generic_build(self):
        with open(os.path.join(scripts_path, self.run_script), "w") as f:
            f.write("#!/usr/bin/env bash" + os.linesep*3)
            f.write("source /root/maven.sh" + os.linesep)
            self.write_build_requires(f)
            f.write("prep" + os.linesep)
            f.write("build" + os.linesep)
            f.write("install" + os.linesep)
            f.write("if [ $? -eq 0 ]; then" + os.linesep)
            f.write("  echo \"build success\"" + os.linesep)
            f.write("fi" + os.linesep)
