# Copyright (c) [2023] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#       http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

import os
import sys
import yaml
from bs4 import BeautifulSoup
import requests
from src.parse.basic_parse import BasicParse
from src.log import logger
from src.utils.cmd_util import has_file_type
from src.config.config import configuration


class GolangParse(BasicParse):
    def __init__(self, source, version=""):
        super().__init__(source)
        name = source.name
        self.version = version if version != "" else source.version
        self.url_template = "https://pkg.go.dev/"
        self.url_template_with_ver = f'https://pkg.go.dev/{name}/{version}/json'
        self.go_path = ""
        self.build_system = "go"
        with open(os.path.join(configuration.yaml_path, f"{self.build_system}.yaml"), "r") as f:
            yaml_text = f.read()
        self.source = source
        self.metadata = yaml.safe_load(yaml_text)

    def parse_api_info(self):
        if not self.version:
            url = self.url_template.format(pkg_name=self.pacakge_name)
        else:
            url = self.url_template_with_ver.format(pkg_name=self.pacakge_name, pkg_ver=self.version)

        response = requests.get(url)
        if response.status_code != 200:
            logger.error(f"Failed to fetch package info: {response.status_code}")
            sys.exit(6)
        soup = BeautifulSoup(response.content, 'html.parser')
        license_tag = soup.find('span', {'class': 'License'})
        # URL
        url_tag = soup.find('a', {'class': 'RepoURL'})
        # Description
        description_tag = soup.find('div', {'class': 'Doc'})
        # Summary
        summary_tag = soup.find('div', {'class': 'Summary'})
        self.metadata = {
            "name": self.source.name,
            "version": self.version,
            "meta": {
                "summary": summary_tag.text.strip(),
                "description": description_tag.text.strip()
            },
            "license": license_tag.text.strip(),
            "release": 1,
            "homepage": url_tag['href'],
            "sources": {0: url_tag['href']},
            "buildSystem": "golang"
        }

    def check_compilation_file(self):
        if has_file_type(self.source.path, "go"):
            has_mod = False
            has_sum = False
            m = 0
            n = 0
            for file in self.source.files:
                if "/" not in file and file.endswith(".mod"):
                    has_mod = True
                    m += 1
                if "/" not in file and file.endswith(".sum"):
                    has_sum = True
                    n += 1
            if m > 1 or n > 1:
                return False
            return has_mod and has_sum
        return False

    def check_compilation(self):
        return self.check_compilation_file()
