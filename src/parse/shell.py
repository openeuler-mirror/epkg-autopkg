import os
from src.parse.basic_parse import BasicParse
from src.builder import scripts_path


class ShellParse(BasicParse):
    def __init__(self, name):
        super().__init__(name)
        self.language = "shell"
        self.shell_compile_files = ["autogen.sh", "build.sh", "compile.sh"]
        self.compile_type = "autogen"

    def check_compile_file(self, file):
        return file in self.shell_compile_files

    def parse_metadata(self):
        self.init_metadata()
        self.init_scripts()

    def init_scripts(self):
        # TODO(self.scripts中增加编译函数)
        pass

    def make_generic_build(self):
        with open(os.path.join(scripts_path, self.run_script), "w") as f:
            f.write("#!/usr/bin/env bash" + os.linesep*3)
            f.write(f"source /root/shell.sh" + os.linesep)
            self.write_build_requires(f)
            f.write("prep" + os.linesep)
            f.write("build" + os.linesep)
            f.write("install" + os.linesep)
            f.write("if [ $? -eq 0 ]; then" + os.linesep)
            f.write("  echo \"build success\"" + os.linesep)
            f.write("fi" + os.linesep)
