# SPDX-License-Identifier: MIT
# Copyright (c) 2017 Shintaro Kaneko. All rights reserved.

import os
import re
import sys
import src.builder
from src.core.logparser import LogParser
from src.core.source import source
from src.transfer.writer import YamlWriter
from src.parse.cmake import CMakeParse
from src.parse.maven import MavenParse
from src.parse.python import PythonParse
from src.parse.make import MakeParse
from src.parse.shell import ShellParse
from src.parse.autotools import AutotoolsParse
from src.parse.ruby import RubyParse
from src.parse.perl import PerlParse
from src.parse.nodejs import NodejsParse
from src.utils.merge import merge_func
from src.utils.file_util import write_out, get_sha1sum, unzip_file
from src.utils.cmd_util import has_file_type
from src.utils.pypidata import do_curl
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


class YamlMaker:
    def __init__(self, **kwargs):
        self.name = kwargs.get("name")
        self.tarball_url = kwargs.get("tarball_url")
        self.git_url = kwargs.get("git_url")
        path = kwargs.get("directory")
        version = kwargs.get("version")
        language = kwargs.get("language")
        self.version = None
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
            self.work_path = configuration.download_path
            self.path = unzip_file(self.check_or_get_file(self.tarball_url), self.work_path)
            source.path = self.path
        else:
            self.path = path
            source.path = self.path
        self.need_build = kwargs.get("need_build")
        self.compilation = kwargs.get("compilation")
        self.compile_classes = {
            "make": MakeParse,
            "cmake": CMakeParse,
            "python": PythonParse,
            "shell": ShellParse,
            "java": MavenParse,
            "autotools": AutotoolsParse,
            "ruby": RubyParse,
            "perl": PerlParse,
            "javascript": NodejsParse
            # TODO(more compilation)
        }
        self.compilations = set()
        self.pattern_strength = 0
        self.prefix = None

    def create_yaml(self):
        # 主流程
        yaml_writer = YamlWriter(self.name, configuration.download_path)
        if self.name:
            # 根据name/version/language来获取信息的情况
            if self.language in ["C", "C++"]:
                logger.error("Not support inquiry C/C++ project by API")
                sys.exit(6)
            else:
                compile_type = configuration.language_for_compilation.get(self.language)
            subclass = self.compile_classes[compile_type]
            sub_object = subclass(source)
            sub_object.parse_api_info()
            yaml_writer.create_yaml_package(sub_object.metadata)
            return
        if self.tarball_url:
            self.check_or_get_file()
            if not (os.path.exists(self.path) and os.listdir(self.path)):
                logger.error("download url failed")
                sys.exit(2)
        # 扫描源码包
        self.scan_source()

        # 多种编译类型尝试
        for compilation in self.compilations:
            # 选择编译类型对应的类
            subclass = self.compile_classes[compilation]
            sub_object = subclass(source)
            sub_object.parse_metadata()
            build_count = 0
            while self.need_build and build_count <= 10:
                logger.info("build round: " + str(build_count))
                # mv cronie-4.3 build_source
                self.rename_build_source()
                # 生成generic-build.sh
                yaml_writer.create_yaml(sub_object.metadata)
                run_docker_script(compilation)
                build_count += 1
                if not os.path.exists(os.path.join(configuration.download_path, configuration.logfile)):
                    logger.error("no such file: " + os.path.join(configuration.download_path, configuration.logfile))
                with open(os.path.join(configuration.download_path, configuration.logfile), "r") as f:
                    content = f.read()
                if configuration.build_success_echo in content:
                    run_docker_epkg()  # 打包的脚本
                    yaml_writer.create_yaml_package(sub_object.metadata)
                    break
                log_parser = LogParser(sub_object.metadata, sub_object.scripts, compilation=compilation)
                sub_object.metadata = log_parser.parse_build_log()

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
        if not os.path.isfile(tarball_path):
            do_curl(self.tarball_url, dest=tarball_path, is_fatal=True)
        self.write_upstream(get_sha1sum(tarball_path), tarball_path, mode)
        return tarball_path

    def scan_source(self):
        """
        scan name version and compilations from source
        :return:
        """
        self.name_and_version()
        self.scan_compilations()

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
        if name == version == "" and "-" in tarfile:
            name, version = tarfile.split("-", -1)

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

    def scan_compilations(self):
        # TODO(better method)
        for dir_path, _, files in os.walk(self.path):
            default_score = 2 if dir_path == self.path else 1

            if "Cargo.toml" in files:
                self.add_build_pattern('cargo', default_score)

            if "CMakeLists.txt" in files and "configure.ac" not in files:
                self.add_build_pattern("cmake", default_score)

            if "configure" in files and os.access(dir_path + '/configure', os.X_OK):
                self.add_build_pattern("configure", default_score)

            if ("requirements.txt" in files and "pyproject.toml" in files) or "setup.py" in files:
                self.add_build_pattern("python", default_score)

            if "Makefile.PL" in files or "Build.PL" in files:
                self.add_build_pattern("cpan", default_score)

            if "SConstruct" in files:
                self.add_build_pattern("scons", default_score)

            if "meson.build" in files:
                self.add_build_pattern("meson", default_score)

            if "pom.xml" in files:
                self.add_build_pattern("java_pom", default_score)

            if "Makefile" in files:
                self.add_build_pattern("make", default_score)

            if "package.json" in files and has_file_type(self.path, "js"):
                self.add_build_pattern("javascript", default_score)

            if ("autogen.sh" in files or "build.sh" in files or "compile.sh" in files) and default_score == 2:
                self.add_build_pattern("shell", default_score)
            elif "Makefile.am" in files and "configure.ac" in files:
                self.add_build_pattern("autotools", default_score)

    def add_build_pattern(self, pattern, strength):
        """Set the global default pattern and pattern strength."""
        if strength <= self.pattern_strength or pattern in self.compilations:
            return
        self.compilations.add(pattern)
        self.pattern_strength = strength
