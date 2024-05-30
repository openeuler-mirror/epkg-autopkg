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
            self.commands.insert("autoreconf -vif")
