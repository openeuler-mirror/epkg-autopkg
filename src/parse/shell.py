from src.parse.basic_parse import BasicParse
from src.log import logger


class ShellParse(BasicParse):
    def __init__(self, name):
        super().__init__(name)
        self.language = "shell"
        self.shell_compile_files = ["autogen.sh", "build.sh", "compile.sh"]

    def check_compile_file(self, file):
        return file in self.shell_compile_files

    def parse_metadata(self):
        self.init_metadata()
        self.init_scripts()

    def init_scripts(self):
        # TODO(self.scripts中增加编译函数)
        pass
