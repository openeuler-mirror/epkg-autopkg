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
import re
import yaml
import requests
from lxml import etree
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
        self.pom_info = {}
        self.pom_properties = {}
        self.ns = {"ns": "http://maven.apache.org/POM/4.0.0"}
        self.spec_map = {'@groovyGroupId@': 'org.codehaus.groovy'}
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
            return True
        return False

    def check_compilation(self):
        result = self.check_compilation_file()
        if result:
            self.parse_all_pom()
        return result

    def parse_all_pom(self):
        for file in self.source.files:
            if file.endswith("pom.xml"):
                with open(os.path.join(self.source.path, file), "r") as f:
                    content = f.read().encode("utf-8")
                parser = etree.XMLParser(remove_blank_text=True)
                root = etree.from_string(content, parser)
                pom_info = self.parse_xml2dict(root)
                if "properties" in pom_info:
                    self.pom_properties = self.trans_params(pom_info["properties"])
                    pom_info = self.trans_params(pom_info)
                self.pom_info[file.replace("pom.xml", "pom_xml").replace("/", "_")] = pom_info

    def remove_plugin_config(self, name):
        self.metadata.setdefault("removePlugin", []).append(name)

    def disable_module_config(self, name):
        self.metadata.setdefault("disableModule", []).append(name)

    def parse_xml2dict(self, node):
        result = {}
        if len(node) == 0:
            return
        for child in node:
            if hasattr(child, "tag") and isinstance(child.tag, str):
                if "}" in child.tag:
                    keywords = child.tag.split("}")[-1]
                else:
                    keywords = child.tag
                value = self.parse_xml2dict(child)
                if keywords in result:
                    if not isinstance(result[keywords], list):
                        result[keywords] = [result[keywords]]
                    result[keywords].append(value)
                else:
                    result[keywords] = value
        return result

    def trans_params(self, dict_info: dict):
        tmp_dict_info = dict_info.copy()
        for k, value in tmp_dict_info.items():
            if isinstance(value, str) and re.search(r"\$\{.+}", value):
                dict_info[k] = self.change_param_value(value)
            elif isinstance(value, list):
                dict_info[k] = self.trans_params_list(value)
            elif isinstance(value, dict):
                dict_info[k] = self.trans_params(value)
        return dict_info

    def trans_params_list(self, list_info: list):
        tmp_list_info = list_info.copy()
        for i, single in enumerate(tmp_list_info):
            if isinstance(single, str) and re.search(r"\$\{.+}", single):
                list_info[i] = self.change_param_value(single)
            elif isinstance(single, dict):
                list_info[i] = self.trans_params(single)
            elif isinstance(single, list):
                list_info[i] = self.trans_params_list(single)
        return list_info

    def change_param_value(self, value: str):
        target_value = value
        params = re.findall(r"\$\{.+}", value)
        for param in params:
            base_param = param.repalce("${", "").replace("}", "")
            if base_param in self.pom_properties:
                target_value = value.replace(param, self.pom_properties[base_param])
        return target_value

