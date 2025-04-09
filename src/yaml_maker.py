# Copyright (c) [2023] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#       http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

import os
import re
import sys
import yaml
from src.core.logparser import LogParser
from src.core.source import source
from src.transfer.writer import YamlWriter
from src.parse.cmake import CMakeParse
from src.parse.maven import MavenParse
from src.parse.python import PythonParse
from src.parse.make import MakeParse
from src.parse.autogen import AutogenParse
from src.parse.autotools import AutotoolsParse
from src.parse.ruby import RubyParse
from src.parse.perl import PerlParse
from src.parse.nodejs import NodejsParse
from src.parse.meson import MesonParse
from src.parse.golang import GolangParse
from src.utils.file_util import get_sha1sum, unzip_file
from src.utils.cmd_util import has_file_type, call
from src.utils.download import do_curl, clone_code
from src.builder.epkg_build import run_docker_script, get_build_result
from src.log import logger
from src.config.config import configuration


def save_round_logs(path, iteration):
    """Save Mock build logs to <path>/results/round<iteration>-*.log."""
    basedir = os.path.join(path, "results")
    log_list = ["build", "rpm", "env"]
    for log in log_list:
        src = "{}/{}.log".format(basedir, log)
        dest = "{}/round{}-{}.log".format(basedir, iteration, log)
        os.rename(src, dest)


def get_contents(filename):
    """Get contents of filename."""
    with open(filename, "rb") as f:
        return f.read()


def generate_data(original: dict):
    data = original.copy()
    for k, v in original.items():
        if isinstance(v, set):
            data[k] = list(v)
    return data


def add_metadata_args(data):
    if configuration.maven_remove_plugins:
        data["maven_remove_plugins"] = " ".join(list(configuration.maven_disable_modules))
    if configuration.maven_disable_modules:
        data["maven_disable_modules"] = " ".join(list(configuration.maven_disable_modules))
    if configuration.maven_delete_dirs:
        data["maven_rm_dirs"] = " ".join(list(configuration.maven_delete_dirs))
    return data


def add_requires_from_yaml(info: dict, path):
    yaml_path = os.path.join(path, "package-mapping-result.yaml")
    if not os.path.exists(yaml_path):
        logger.warning("no such file: " + yaml_path)
        return info
    logger.info("start to check package-mapping-result.yaml")
    with open(yaml_path, "r") as f:
        content = f.read()
    items = yaml.safe_load(content)
    for k, build_requires in items.items():
        if isinstance(build_requires, list) and len(build_requires) > 0:
            for value in build_requires:
                info.setdefault("buildRequires", []).append(value)
    return info


class YamlMaker:
    def __init__(self, **kwargs):
        self.name = kwargs.get("name")
        self.tarball_url = kwargs.get("tarball_url")
        self.git_url = kwargs.get("git_url")
        path = kwargs.get("directory")
        version = kwargs.get("version")
        language = kwargs.get("language")
        self.version = None
        self.work_path = configuration.download_path
        self.used = False
        if self.name != "":
            source.name = self.name
            logger.info("parse language module")
            self.version = version
            source.version = version
            self.language = language
            source.language = language
        elif self.tarball_url != "":
            source.url = self.tarball_url
            logger.info("download source from url")
            self.path = unzip_file(self.check_or_get_file(self.tarball_url), self.work_path)
            source.path = self.path
        elif self.git_url != "":
            clone_code(self.work_path, self.git_url)
            source.path = self.path = os.path.join(self.work_path, os.path.basename(self.git_url.replace(".git", "")))
        else:
            self.path = path
            source.path = self.path
        self.need_build = kwargs.get("need_build")
        self.compilation = kwargs.get("compilation")
        self.parse_classes = {
            "cmake": CMakeParse,
            "autotools": AutotoolsParse,
            "meson": MesonParse,
            "maven": MavenParse,
            "autogen": AutogenParse,
            "ruby": RubyParse,
            "go": GolangParse,
            "make": MakeParse,
            "python": PythonParse,
            "perl": PerlParse,
            "javascript": NodejsParse,
            # TODO(more compilation)
        }
        self.compilations = set()
        self.pattern_strength = 0
        self.prefix = None

    def detect_api_info(self, yaml_writer):
        if self.language in ["C", "C++"]:
            logger.error("Not support inquiry C/C++ project by API")
            sys.exit(6)
        else:
            compile_type = configuration.language_for_compilation.get(self.language)
        subclass = self.parse_classes[compile_type]
        sub_object = subclass(source)
        sub_object.parse_api_info()
        yaml_writer.create_yaml_package(generate_data(sub_object.metadata))

    def create_yaml(self):
        # TODO: refactor into functions
        # 主流程
        yaml_writer = YamlWriter(self.name, configuration.download_path)
        if self.name:
            # TODO: instead of lang, detect parse_api_info() defined?
            # 根据name/version/language来获取信息的情况
            self.detect_api_info(yaml_writer)
            return
        self.double_loop_build(yaml_writer)

    def double_loop_build(self, yaml_writer):
        # 扫描源码包
        src = self.scan_source()
        for compilation, subclass in self.parse_classes.items():
            logger.info("buildSystem is " + compilation)
            if compilation in configuration.buildrequires_analysis_compilations:
                self.scan_analysis()
            sub_object = subclass(src)
            result = sub_object.check_compilation()
            if not result:
                continue
            if hasattr(sub_object, "fix_name_version"):
                sub_object.fix_name_version(self.path)

            # 循环构建，构建成功或无法自修复的失败会退出
            build_count = 0
            while self.need_build and build_count <= 10:
                logger.info("build round: " + str(build_count))
                # mv cronie-4.3 workspace
                self.rename_build_source()
                # 生成package.yaml
                sub_object.get_basic_info(compilation)
                sub_object.metadata = add_metadata_args(sub_object.metadata)
                yaml_writer.create_yaml_package(generate_data(sub_object.metadata))
                # 生成generic-build.sh
                sub_object.metadata = add_requires_from_yaml(sub_object.metadata, self.path)
                run_docker_script(compilation, sub_object.metadata, build_count)
                build_count += 1
                if not os.path.exists(os.path.join(configuration.download_path, configuration.logfile)):
                    logger.error("no such file: " + os.path.join(configuration.download_path, configuration.logfile))
                with open(os.path.join(configuration.download_path, configuration.logfile), "r") as f:
                    content = f.read()
                if configuration.build_success_echo in content:
                    sub_object.merge_phase_items(compilation)
                    get_build_result(sub_object.generate_metadata())  # 打包的脚本
                    return
                log_parser = LogParser(sub_object.metadata, sub_object.scripts, compilation=compilation)
                sub_object.metadata = log_parser.parse_build_log()
                if not log_parser.restart:
                    logger.error("build error finally")
                    break

    def rename_build_source(self):
        # 构建目录统一改为workspace
        os.system(f"rm -rf {configuration.download_path}/workspace")
        os.system(f"cp -r {self.path} {configuration.download_path}/workspace")

    def write_upstream(self, file_name, mode="w"):
        """Write the upstream hash to the upstream file."""
        with open(os.path.join(self.work_path, "upstream"), mode) as require_f:
            require_f.write(os.path.join(get_sha1sum(file_name), file_name) + "\n")

    def check_or_get_file(self, mode="w"):
        """Download tarball from url unless it is present locally."""
        tarball_path = os.path.join(self.work_path, os.path.basename(self.tarball_url))
        ret = os.system(f"wget {self.tarball_url} -P {self.work_path}")
        if ret == 0:
            return tarball_path
        if not os.path.isfile(tarball_path):
            do_curl(self.tarball_url, dest=tarball_path, is_fatal=True)
        self.write_upstream(tarball_path, mode)
        return tarball_path

    def scan_source(self):
        """
        scan name version and compilations from source
        :return:
        """
        source_obj = self.name_and_version()
        self.scan_files()
        return source_obj

    def name_and_version(self):
        """从URL中解析name和version."""
        tarfile = os.path.basename(self.tarball_url)

        name = self.name
        version = ""
        if self.path.endswith("/"):
            self.path = self.path.rstrip("/")
        if name == version == "" and "-" in tarfile:
            name, version = tarfile.rsplit("-", 1)
        elif name == version == "" and "-" in os.path.basename(self.path):
            name, version = os.path.basename(self.path).rsplit("-", 1)
        if version in ["main", "master"]:
            version = "0.0.1"

        if self.name and not version:
            # 只有name没有version时
            basename = tarfile.split(self.name)[-1]
            no_extension = os.path.splitext(basename)[0]
            if no_extension.endswith('.tar'):
                no_extension = os.path.splitext(no_extension)[0]

        # override name and version from commandline
        source.name = self.name = self.name if self.name else name
        source.version = self.version = self.version if self.version else version
        return source

    def scan_analysis(self):
        if not os.path.exists(configuration.analysis_tool_path):
            return
        if self.used:
            return
        logger.info("start to scan buildRequires...")
        call(f"/usr/bin/python3 {configuration.analysis_tool_path} mapping_file {self.path} --os-version 22.03-LTS-SP4")
        self.used = True

    def scan_files(self):
        for dir_path, _, files in os.walk(self.path):
            dir_name = dir_path.replace(self.path, "").lstrip("/")
            for file in files:
                source.files.append(os.path.join(dir_name, file))


