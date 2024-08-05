# SPDX-License-Identifier: MIT
# Copyright (c) 2017 Shintaro Kaneko. All rights reserved.

import os
import sys
import requests
from src.parse.basic_parse import BasicParse
from src.builder import scripts_path
from src.config.config import configuration
from src.log import logger


class MavenParse(BasicParse):
    def __init__(self, source, version=""):
        super().__init__(source)
        if source.group == "":
            logger.error("lack of groupId input")
            sys.exit(6)
        self.language = "java"
        self.build_requires.add("maven")
        self.compile_type = "maven"
        self.version = version if version != "" else source.version
        self.group = source.group
        self.__url = f"https://repo1.maven.org/maven2/{self.group}/{self.pacakge_name}/{self.version}/" \
                     f"{self.pacakge_name}-{self.version}.pom"

    def update_metadata(self):
        self.metadata.setdefault("buildRequires", self.build_requires)

    def parse_metadata(self):
        self.init_metadata()
        self.init_scripts()

    def init_scripts(self):
        # TODO(self.scripts中增加编译函数)
        pass

    def make_generic_build(self):
        with open(os.path.join(scripts_path, self.run_script), "w") as f:
            f.write("#!/usr/bin/env bash" + os.linesep*3)
            f.write("source /root/maven.sh" + os.linesep)
            self.write_build_requires(f)
            f.write("prep" + os.linesep)
            self.basic_general_build(f)

    def detect_build_system(self):
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
