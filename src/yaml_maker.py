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
from src.utils.file_util import write_out, get_sha1sum, unzip_file
from src.utils.cmd_util import has_file_type, call
from src.utils.download import do_curl, clone_code
from src.builder.docker_tool import run_docker_script, run_docker_epkg
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


def convert_version(ver_str, name):
    """Remove disallowed characters from the version."""
    # banned substrings. It is better to remove these here instead of filtering
    # them out with expensive regular expressions
    banned_subs = ["x86.64", "source", "src", "all", "bin", "release", "rh",
                   "ga", ".ce", "lcms", "onig", "linux", "gc", "sdk", "orig",
                   "jurko", "%2f", "%2F", "%20"]

    # package names may be modified in the version string by adding "lib" for
    # example. Remove these from the name before trying to remove the name from
    # the version
    name_mods = ["lib", "core", "pom", "opa-"]

    # enforce lower-case strings to make them easier to standardize
    ver_str = ver_str.lower()
    # remove the package name from the version string
    ver_str = ver_str.replace(name.lower(), '')
    # handle modified name substrings in the version string
    for mod in name_mods:
        ver_str = ver_str.replace(name.replace(mod, ""), "")

    # replace illegal characters
    ver_str = ver_str.strip().replace('-', '.').replace('_', '.')

    # remove banned substrings
    for sub in banned_subs:
        ver_str = ver_str.replace(sub, "")

    # remove consecutive '.' characters
    while ".." in ver_str:
        ver_str = ver_str.replace("..", ".")

    return ver_str.strip(".")


def do_regex(patterns, re_str):
    """Find a match in multiple patterns."""
    for p in patterns:
        match = re.search(p, re_str)
        if match:
            return match


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


def add_requires_from_yaml(info: dict, path):
    yaml_path = os.path.join(path, "package-mapping-result.yaml")
    if not os.path.exists(yaml_path):
        logger.warning("no such file: " + yaml_path)
        return info
    logger.info("start to check package-mapping-result.yaml")
    with open(yaml_path, "r") as f:
        content = f.read()
    items = yaml.safe_load(content)
    build_requires = items.get("buildRequires")
    if isinstance(build_requires, list) and build_requires:
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
            "python": PythonParse,
            "autotools": AutotoolsParse,
            "meson": MesonParse,
            "maven": MavenParse,
            "autogen": AutogenParse,
            "ruby": RubyParse,
            "make": MakeParse,
            "perl": PerlParse,
            "javascript": NodejsParse,
            "go": GolangParse,
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
                    run_docker_epkg()  # 打包的脚本
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

    def write_upstream(self, sha, file_name, mode="w"):
        """Write the upstream hash to the upstream file."""
        write_out(os.path.join(self.work_path, "upstream"),
                  os.path.join(sha, file_name) + "\n", mode=mode)

    def check_or_get_file(self, mode="w"):
        """Download tarball from url unless it is present locally."""
        tarball_path = os.path.join(self.work_path, os.path.basename(self.tarball_url))
        ret = os.system(f"wget {self.tarball_url} -P {self.work_path}")
        if ret == 0:
            return tarball_path
        if not os.path.isfile(tarball_path):
            do_curl(self.tarball_url, dest=tarball_path, is_fatal=True)
        self.write_upstream(get_sha1sum(tarball_path), tarball_path, mode)
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
        """Parse the url for the package name and version."""
        tarfile = os.path.basename(self.tarball_url)

        # If both name and version overrides are set via commandline, set the name
        # and version variables to the overrides and bail. If only one override is
        # set, continue to autodetect both name and version since the URL parsing
        # handles both. In this case, wait until the end to perform the override of
        # the one that was set. An extra conditional, that version_arg is a string
        # is added to enable a package to have multiple versions at the same time
        # for some language ecosystems.
        if self.name and self.version:
            self.version = convert_version(self.version, self.name)
            return

        name = self.name
        version = ""
        # it is important for the more specific patterns to come first
        pattern_options = [
            # handle font packages with names ending in -nnndpi
            r"(.*-[0-9]+dpi)[-_]([0-9]+[a-zA-Z0-9\+_\.\-\~]*)\.(tgz|tar|zip)",
            r"(.*?)[-_][vs]?([0-9]+[a-zA-Z0-9\+_\.\-\~]*)\.(tgz|tar|zip)",
        ]
        match = do_regex(pattern_options, tarfile)
        if match:
            name = match.group(1).strip()
            version = convert_version(match.group(2), name)

        # R package
        if "cran.r-project.org" in self.tarball_url or "cran.rstudio.com" in self.tarball_url and name:
            name = "R-" + name

        if ".cpan.org/" in self.tarball_url or ".metacpan.org/" in self.tarball_url and name:
            name = "perl-" + name

        name, version = self.extract_from_web(name, version)
        if self.path.endswith("/"):
            self.path.rstrip("/")
        if name == version == "" and "-" in tarfile:
            name, version = tarfile.split("-", -1)
        elif name == version == "" and "-" in os.path.basename(self.path) and tarfile == "":
            name, version = os.path.basename(self.path).rsplit("-", 1)

        if self.name and not version:
            # In cases where we have a name but no version
            # use what is after the name.
            # https://invisible-mirror.net/archives/lynx/tarballs/lynx2.8.9rel.1.tar.gz
            postname = tarfile.split(self.name)[-1]
            no_extension = os.path.splitext(postname)[0]
            if no_extension.endswith('.tar'):
                no_extension = os.path.splitext(no_extension)[0]
            version = convert_version(no_extension, self.name)

        # override name and version from commandline
        self.name = self.name if self.name else name
        self.version = self.version if self.version else version
        source.name = self.name
        source.version = self.version
        return source

    def extract_from_web(self, name, version):
        if "github.com" in self.tarball_url:
            # define regex accepted for valid packages, important for specific
            # patterns to come before general ones
            github_patterns = [r"https?://github.com/(.*)/(.*?)/archive/refs/tags/[vVrR]?(.*)\.tar",
                               r"https?://github.com/(.*)/(.*?)/archive/[v|r]?.*/(.*).tar",
                               r"https?://github.com/(.*)/(.*?)/archive/[-a-zA-Z_]*-(.*).tar",
                               r"https?://github.com/(.*)/(.*?)/archive/[vVrR]?(.*).tar",
                               r"https?://github.com/(.*)/.*-downloads/releases/download/.*?/(.*)-(.*).tar",
                               r"https?://github.com/(.*)/(.*?)/releases/download/(.*)/",
                               r"https?://github.com/(.*)/(.*?)/files/.*?/(.*).tar"]

            match = do_regex(github_patterns, self.tarball_url)
            if match:
                repo = match.group(2).strip()
                if repo not in name:
                    # Only take the repo name as the package name if it's more descriptive
                    name = repo
                elif name != repo:
                    name = re.sub(r"release-", '', name)
                    name = re.sub(r"\d*$", '', name)
                version = str(match.group(3)).replace(name, '')
                if "/archive/" not in self.tarball_url:
                    version = re.sub(r"^[-_.a-zA-Z]+", "", version)
                version = convert_version(version, name)

        # SQLite tarballs use 7 digit versions, e.g 3290000 = 3.29.0, 3081002 = 3.8.10.2
        if "sqlite.org" in self.tarball_url:
            major = version[0]
            minor = version[1:3].lstrip("0").zfill(1)
            patch = version[3:5].lstrip("0").zfill(1)
            build = version[5:7].lstrip("0")
            version = major + "." + minor + "." + patch + "." + build
            version = version.strip(".")

        if "mirrors.kernel.org" in self.tarball_url:
            m = re.search(r".*/sourceware/(.*?)/releases/(.*?).tgz", self.tarball_url)
            if m:
                name = m.group(1).strip()
                version = convert_version(m.group(2), name)

        if "sourceforge.net" in self.tarball_url:
            scf_pats = [r"projects/.*/files/(.*?)/(.*?)/[^-]*(-src)?.tar.gz",
                        r"downloads.sourceforge.net/.*/([a-zA-Z]+)([-0-9\.]*)(-src)?.tar.gz"]
            match = do_regex(scf_pats, self.tarball_url)
            if match:
                name = match.group(1).strip()
                version = convert_version(match.group(2), name)

        if "bitbucket.org" in self.tarball_url:
            bitbucket_pats = [r"/.*/(.*?)/.*/.*v([-\.0-9a-zA-Z_]*?).(tar|zip)",
                              r"/.*/(.*?)/.*/([-\.0-9a-zA-Z_]*?).(tar|zip)"]

            match = do_regex(bitbucket_pats, self.tarball_url)
            if match:
                name = match.group(1).strip()
                version = convert_version(match.group(2), name)

        if "gitlab.com" in self.tarball_url:
            # https://gitlab.com/leanlabsio/kanban/-/archive/1.7.1/kanban-1.7.1.tar.gz
            m = re.search(r"gitlab\.com/.*/(.*)/-/archive/(?:VERSION_|[vVrR])?(.*)/", self.tarball_url)
            if m:
                name = m.group(1).strip()
                version = convert_version(m.group(2), name)

        if "git.sr.ht" in self.tarball_url:
            # https://git.sr.ht/~sircmpwn/scdoc/archive/1.9.4.tar.gz
            m = re.search(r"git\.sr\.ht/.*/(.*)/archive/(.*).tar.gz", self.tarball_url)
            if m:
                name = m.group(1).strip()
                version = convert_version(m.group(2), name)

        if "pigeonhole.dovecot.org" in self.tarball_url:
            # https://pigeonhole.dovecot.org/releases/2.3/dovecot-2.3-pigeonhole-0.5.20.tar.gz
            if m := re.search(r"pigeonhole\.dovecot\.org/releases/.*/dovecot-[\d\.]+-(\w+)-([\d\.]+)\.[^\d]", self.tarball_url):
                name = m.group(1).strip()
                version = convert_version(m.group(2), name)

        if ".ezix.org" in self.tarball_url:
            # https://www.ezix.org/software/files/lshw-B.02.19.2.tar.gz
            if m := re.search(r"(\w+)-[A-Z]\.(\d+(?:\.\d+)+)", self.tarball_url):
                name = m.group(1).strip()
                version = convert_version(m.group(2), name)
        return name, version

    def scan_analysis(self):
        if not os.path.exists(configuration.analysis_tool_path):
            return
        if self.used:
            return
        logger.info("start to scan buildRequires...")
        call(f"python3 {configuration.analysis_tool_path} mapping_file {self.path} --os-version 22.03-LTS-SP4")
        self.used = True

    def scan_files(self):
        for dir_path, _, files in os.walk(self.path):
            dir_name = dir_path.replace(self.path, "").lstrip("/")
            for file in files:
                source.files.append(os.path.join(dir_name, file))

