import os
import requests
from src.parse.basic_parse import BasicParse
from src.log import logger


class MakeParse(BasicParse):
    def __init__(self, name):
        super().__init__(name)
        self.language = "C/C++"
        self.build_requires.add("gcc")
        self.build_requires.add("make")

    def parse_metadata(self):
        self.init_metadata()
        self.init_scripts()

    def init_scripts(self):
        # TODO(self.scripts中增加编译函数)
        pass

    def detect_build_system(self):
        url = "https://api.pkgs.org/v1/search"
        params = {"query": self.pacakge_name}
        info = requests.get(url, params=params).json()
        self.metadata.setdefault("name", self.pacakge_name)
        self.metadata.setdefault("version", self.version)
