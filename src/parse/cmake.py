import os
from src.parse.basic_parse import BasicParse
from src.utils.cmd_util import check_makefile_exist
from src.log import logger


class CMakeParse(BasicParse):
    def __init__(self, name):
        super().__init__(name)
        self.language = "C/C++"
        self.compile_path = ""

    def check_configure_file(self, path):
        if "CMakeLists.txt" not in os.listdir(path):
            self.compile_path = check_makefile_exist(path)
