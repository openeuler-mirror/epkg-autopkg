import os
from src.parse.basic_parse import BasicParse
from src.log import logger


class ConfigureParse(BasicParse):
    def __init__(self, name):
        super().__init__(name)
        self.language = "C/C++"
        self.build_requires.add("gcc")
        self.build_requires.add("make")
        self.configure_file = "configure"

    def check_configure_file(self, path):
        if self.configure_file not in os.listdir(path) and f"{self.configure_file}.ac":
            logger.info("no configure file in root-dir, check it in sub-dir")
            # TODO(子目录下查找configure文件)

    def parse_metadata(self):
        self.init_metadata()
        self.init_scripts()

    def init_scripts(self):
        # TODO(self.scripts中增加编译函数)
        pass
