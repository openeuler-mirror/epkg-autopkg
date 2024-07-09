from src.parse.basic_parse import BasicParse
from src.log import logger


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
