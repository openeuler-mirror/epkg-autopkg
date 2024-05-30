from src.parse.basic_parse import BasicParse
from src.log import logger


class MavenParse(BasicParse):
    def __init__(self, name):
        super().__init__(name)
        self.language = "java"
        self.build_requires.add("maven")

    def update_metadata(self):
        self.metadata.setdefault("buildRequires", self.build_requires)
