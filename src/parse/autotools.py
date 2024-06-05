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
        self.metadata.setdefault("buildRequires", set()).add("gcc")
        self.build_requires.add("gcc")
        self.metadata["buildRequires"].add("make")
        self.metadata["buildRequires"].add("automake")
        self.metadata.setdefault("phase.prep", "%autosetup")
        self.build_commands = ["autoreconf -vif", "automake", "%configure", "%{make_build}"]
        self.metadata.setdefault("phase.build", os.linesep.join(self.build_commands))
        self.install_commands = ["rm -rf %{buildroot}", "%make_install"]
        self.metadata.setdefault("phase.install", os.linesep.join(self.install_commands))
