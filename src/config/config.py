# Copyright (c) [2023] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#       http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

import json
import inspect
import requests
from src.log import logger


class EsClient:
    def __init__(self):
        self.common_path_prefix = '/proxy/es'

    def url(self):
        url_with_ip_and_port = 'http://172.168.131.2:8801'
        previous_frame = inspect.currentframe().f_back
        method_name = previous_frame.f_code.co_name
        return f"{url_with_ip_and_port}{self.common_path_prefix}/{method_name}"

    def create_index(self, index_name):
        response = requests.post(self.url(), params={"index_name": index_name})
        json_response = json.loads(response.content)
        return json_response['message']

    def delete_index(self, index_name):
        response = requests.delete(self.url(), params={"index_name": index_name})
        json_response = json.loads(response.content)
        return json_response['message']

    def insert_record(self, index_name, rpm_name, files, provides, resources):
        record = {"index_name": index_name, "rpm_name": rpm_name, "files": files, "provides": provides,
                  "resources": resources}
        headers = {'Content-Type': 'application/json'}
        response = requests.post(self.url(), headers=headers, data=json.dumps(record))
        json_response = json.loads(response.content)
        return json_response['message']

    def query_by_size_all(self, index_name, size, *query_fields):
        response = requests.get(self.url(),
                                params={"index_name": index_name, "size": size, "query_fields": query_fields})
        json_response = json.loads(response.content)
        return json_response['data']

    def list_indexes(self):
        response = requests.get(self.url())
        json_response = json.loads(response.content)
        return json_response['data']

    def query_exact_match(self, index_name, cond_field, keyword, query_field):
        response = requests.get(self.url(),
                                params={"index_name": index_name, "cond_field": cond_field, "keyword": keyword,
                                        "query_field": query_field})
        json_response = json.loads(response.content)
        return json_response['data']

    def query_wildcard_match_term(self, index_name, cond_field, keyword, query_field):
        response = requests.get(self.url(),
                                params={"index_name": index_name, "cond_field": cond_field, "keyword": keyword,
                                        "query_field": query_field})
        json_response = json.loads(response.content)
        return json_response['data']

    def query_whole_index(self, index_name, size):
        response = requests.get(self.url(), params={"index_name": index_name, "size": size})
        json_response = json.loads(response.content)
        return json_response['data']

    def query_by_wildcards(self, index_name, cond_field, wildcard_patterns, *query_fields):
        response = requests.get(self.url(), params={"index_name": index_name, "cond_field": cond_field,
                                                    "wildcard_patterns": ','.join(wildcard_patterns),
                                                    "query_fields": ','.join(query_fields)})
        json_response = json.loads(response.content)
        return json_response['data']

    def query_by_single_wildcard(self, index_name, cond_field, keyword, query_field):
        response = requests.get(self.url(),
                                params={"index_name": index_name, "cond_field": cond_field, "keyword": keyword,
                                        "query_field": query_field})
        json_response = json.loads(response.content)
        return json_response['data']


class BuildConfig:
    download_path = ""
    buildroot_path = "/opt/buildroot"
    phase_member = ["prep", "build", "configure", "install", "check", "clean"]
    language_for_compilation = {
        "python": "python",
        "ruby": "ruby",
        "java": "maven",
        "javascript": "nodejs",
        "perl": "perl",
    }
    logfile = "build.log"
    configure_failed_pats = [
        ("", "")
    ]
    build_success_echo = "Compress success"
    pkgconfig_pats = {}
    simple_pats = {}
    make_failed_pats = []
    pkgconfig_failed_pats = []
    cmake_failed_pats = [
        r"CMake Error at cmake/.*/(\w+).cmake",
        r'^.*By not providing "Find(.*).cmake" in CMAKE_MODULE_PATH this.*$',
    ]
    perl_failed_pats = [
        r"    !  ([a-zA-Z:]+) is not installed",
        r"Can't locate [\w\-\/\.]+ in @INC \(you may need to install the ([\w\-:]+) module\)",
        r"Warning: prerequisite ([a-zA-Z:]+) [\d\.]+ not found.",
        r"checking for perl module ([a-zA-Z:]+) [\d\.]+... no",
        r"you may need to install the ([\w-:\.]*) module"
    ]
    pypi_failed_pats = [
        r"Download error on https://pypi.python.org/simple/([\w-\.:]+)/",
        r"ImportError:.* No module named '?([\w-\.]+)'?",
        r"ModuleNotFoundError.*No module named '?(.*)'?",
    ]
    go_failed_pats = [
        r".*\.go:.*cannot find package \"(.*)\" in any of:",
    ]
    ruby_failed_pats = []
    meson_failed_pats = []
    nodejs_failed_pats = []
    make_failed_flags = [
        r"error: ([a-zA-Z\-]*)invalid attempt.*in symbol.*"
    ]
    cmake_search_failed = r"(CMake Error .* CMakeLists.txt).*"
    cmake_failed_flags = [
        r"enable .*or +disable +([-_A-Z]+)",
        r"set +([-_A-Z]+) false"
    ]
    failed_commands = {}
    failed_flags = {}
    qt_modules = {}
    cmake_modules = {}
    yaml_path = "/root/.epkg/build/build-system"
    analysis_tool_path = '/root/dependency-analysis/package_mapping.py'
    maven_remove_plugins = set()
    maven_disable_modules = set()
    maven_delete_dirs = set()
    buildrequires_analysis_compilations = ["autotools", "cmake", "maven", "meson"]

    def setup_patterns(self):
        """Read each pattern configuration file and assign to the appropriate variable."""
        self.read_pattern_conf("failed_commands", self.failed_commands)
        self.read_pattern_conf("failed_flags", self.failed_flags)
        # self.read_pattern_conf("gems", self.gems)
        self.read_pattern_conf("qt_modules", self.qt_modules)
        self.read_pattern_conf("cmake_modules", self.cmake_modules)
        self.read_pattern_conf("pkgconfig_patterns", self.pkgconfig_pats)
        self.read_pattern_conf("simple_patterns", self.simple_pats)
        self.read_pattern_conf("make_failed_patterns", self.make_failed_pats)
        self.read_pattern_conf("pkgconfig_failed_patterns", self.pkgconfig_failed_pats)

        for k, v in self.qt_modules.items():
            self.qt_modules[k] = "Qt5" + v

    def read_pattern_conf(self, file_name, param):
        esclient = EsClient()
        index_name = f"autopkg_openeuler_2403_{file_name}"
        result = esclient.query_whole_index(index_name, 1500)
        if not isinstance(result, list):
            logger.error(f"can't parse database table {index_name}!")
            return
        if len(result) != 2:
            logger.error(f"no data in database table {index_name}!")
            return
        mappings = result[1]
        for item in mappings:
            if not isinstance(item, list):
                continue
            if isinstance(param, dict) and len(item) > 2 and item[1] != "":
                param[item[0]] = item[1]
            elif isinstance(param, list):
                param.append(item[0])


configuration = BuildConfig()
