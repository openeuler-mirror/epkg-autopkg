import os
import sys
import requests
from src.parse.basic_parse import BasicParse
from src.builder import scripts_path
from src.log import logger
from src.config.config import configuration


class RubyParse(BasicParse):
    def __init__(self, source):
        super().__init__(source)
        self.language = "ruby"
        self.build_requires.add("ruby")
        self.build_requires.add("rubygems-devel")
        self.build_requires.add("ruby-devel")
        self.__url_v1 = f"https://rubygems.org/api/v1/gems/{self.pacakge_name}.json"
        self.__url_v2 = f"https://rubygems.org/api/v2/rubygems/{self.pacakge_name}/versions/{self.version}.json"
        self.compile_type = "ruby"

    def parse_metadata(self):
        self.init_metadata()
        self.init_scripts()

    def init_scripts(self):
        # TODO(self.scripts中增加编译函数)
        pass

    def parse_info_from_upstream(self):
        response = requests.get(self.__url_v1)
        if response.status_code != 200:
            logger.error("can't requests the info of " + self.pacakge_name)
            sys.exit(5)
        else:
            data = response.json()
            self.metadata.setdefault("name", data['name'])
            self.metadata.setdefault("version", data['version'])
            self.metadata.setdefault("meta", {}).setdefault("summary", data['summary'])
            self.metadata.setdefault("meta", {}).setdefault("description", data['description'])

    def make_generic_build(self):
        with open(os.path.join(scripts_path, self.run_script), "w") as f:
            f.write("#!/usr/bin/env bash" + os.linesep*3)
            f.write("source /root/ruby.sh" + os.linesep)
            self.write_build_requires(f)
            f.write("prep" + os.linesep)
            f.write("build" + os.linesep)
            f.write("install" + os.linesep)
            f.write("if [ $? -eq 0 ]; then" + os.linesep)
            f.write(f"  echo \"{configuration.build_success_echo}\"{os.linesep}")
            f.write("fi" + os.linesep)
