import os
from src.parse.basic_parse import BasicParse
from src.log import logger


class AutotoolsParse(BasicParse):
    def __init__(self, source):
        super().__init__(source)
        self.language = "C/C++"
        self.configure_file = "configure"

    def parse_metadata(self):
        self.init_metadata()
        self.init_scripts()

    def init_scripts(self):
        # TODO(self.scripts中增加编译函数)
        pass

    def parse_info_from_upstream(self):
        pass
