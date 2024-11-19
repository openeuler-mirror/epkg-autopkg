# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; specifically version 2 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
#
# See LICENSE for more details.
#
# Copyright: Red Hat (c) 2023 and Avocado contributors

import os
import sys
import yaml
import requests
from src.parse.basic_parse import BasicParse
from src.utils.cmd_util import check_makefile_exist
from src.config.yamls import yaml_path
from src.log import logger


class MavenParse(BasicParse):
    def __init__(self, source, version=""):
        super().__init__(source)
        if source.group == "" and source.path == "":
            logger.error("lack of groupId input")
            sys.exit(6)
        self.build_system = "maven"
        self.maven_path = ""
        with open(os.path.join(yaml_path, f"{self.build_system}.yaml"), "r") as f:
            yaml_text = f.read()
        self.metadata = yaml.safe_load(yaml_text)
        self.version = version if version != "" else source.version
        self.group = source.group
        self.source = source
        self.__url = f"https://repo1.maven.org/maven2/{self.group}/{self.pacakge_name}/{self.version}/" \
                     f"{self.pacakge_name}-{self.version}.pom"

    def parse_api_info(self):
        # 指定 groupId, artifactId 和 version

        # 构造请求的 URL 和参数
        url = "https://search.maven.org/solrsearch/select"
        params = {
            'q': f'g:"{self.group}" AND a:"{self.pacakge_name}" AND v:"{self.version}"',
            'rows': '20',
            'wt': 'json'
        }

        # 发送 GET 请求
        response = requests.get(url, params=params)

        # 检查响应状态码是否为200
        if response.status_code == 200:
            # 解析 JSON 数据
            data = response.json()
            # 遍历并打印结果
            for doc in data['response']['docs']:
                print(f"GroupId: {doc['g']}, ArtifactId: {doc['a']}, Version: {doc['v']}")
        else:
            print("Error:", response.status_code)

    def check_compilation_file(self):
        if "autopkg" in self.metadata and "buildSystemFiles" in self.metadata["autopkg"]:
            build_system_file = self.metadata["autopkg"]["buildSystemFiles"]
            if build_system_file not in self.source.files:
                self.maven_path = check_makefile_exist(self.source.files, file_name="pom.xml")
                return self.maven_path != ""
        return False

    def check_compilation(self):
        return self.check_compilation_file()

    def remove_plugin_config(self, name):
        self.metadata.setdefault("removePlugin", []).append(name)

    def disable_module_config(self, name):
        self.metadata.setdefault("disableModule", []).append(name)
