import os
import sys
import requests
from src.parse.basic_parse import BasicParse
from src.builder import scripts_path
from src.log import logger
from src.config.config import configuration


class PerlParse(BasicParse):
    def __init__(self, source, version=""):
        super().__init__(source)
        self.language = "perl"
        self.build_requires.add("perl")
        self.version = version if version != "" else source.version
        self.__url = f"https://fastapi.metacpan.org/v1/pod/{self.pacakge_name}"  # Moose
        self.compile_type = "perl"

    def parse_metadata(self):
        self.init_metadata()
        self.init_scripts()

    def init_scripts(self):
        # TODO(self.scripts中增加编译函数)
        pass

    def detect_build_system(self):
        params = {
            "content-type": "application/json"
        }
        response = requests.get(self.__url, params=params)
        if response.status_code != 200:
            logger.error("can't requests the info of " + self.pacakge_name)
            sys.exit(5)
        else:
            content = response.text  # perl接口请求只有纯文本数据类型
        self.metadata = {
            "name": self.pacakge_name,
            "version": self.version,
            "meta": {
                "summary": self.get_summary_from_content(content),
                "description": self.get_description_from_content(content)
            }
        }

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

    def get_summary_from_content(self, text):
        return ""

    def get_description_from_content(self, text):
        return ""
