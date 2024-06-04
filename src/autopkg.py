#!/usr/bin/python
# SPDX-License-Identifier: MulanPSL-2.0+
# Copyright (c) 2022 Huawei Technologies Co., Ltd. All rights reserved.

import os
import sys
import argparse
import re
import subprocess
from src.log import logger
from src.core.source import Source
from src.core.logparser import LogParser
from src.core.common import verify_metadata
from src.transfer.writer import YamlWriter
from src.parse.cmake import CMakeParse
from src.parse.maven import MavenParse
from src.parse.python import PythonParse
from src.parse.configure import ConfigureParse
from src.parse.shell import ShellParse
from src.builder.mock_build import mock_init, save_mock_logs, Build
from src.transfer.writer import SpecWriter
from src.config.config import configuration
from src.utils.merge import merge_func
from src.utils.file_util import write_out


def check_only_one_arg(**kwargs):
    count = 0
    for arg, value in kwargs.items():
        if value is not None:
            count += 1
    return count


def package(compilations):
    compile_classes = {
        "configure": ConfigureParse,
        "cmake": CMakeParse,
        "python": PythonParse,
        "shell": ShellParse,
        "maven": MavenParse
    }
    json_list = []
    for compilation in compilations:
        package_parser = compile_classes[compilation]()
        package_parser.compilation = compilation
        package_parser.init_metadata()
        if url == "" and output == "":
            logger.warning("input no url and not repo!")
            if need_build:
                logger.info("need download repo from upstream org")
                package_parser.download_from_upstream()
        else:
            if url:
                mock_init(os.path.basename(url))
            else:
                mock_init(output)
        SpecWriter.trans_data_to_spec(source.name, configuration.download_path, package_parser.metadata)
        if need_build:
            run(source, package_parser)
        json_list.append(package_parser.metadata)
    return merge_func(json_list)


def parse_log(compilation, package_parser):
    if os.path.exists(os.path.join(configuration.download_path, "results/build.log")):
        log_parser = LogParser(package_parser.metadata, package_parser.files)
        log_parser.parse_package_info(compilation)
        return log_parser.restart
    else:
        logger.warning("build error without build.log")
        sys.exit(2)


def run(content, package_parser):
    build = Build()
    writer = SpecWriter(content.name, content.path)
    while 1:
        writer.trans_data_to_spec(package_parser.metadata)
        build.package(content)
        mock_chroot = "/var/lib/mock/openEuler-LTS-x86_64-1-{}/root/builddir/build/BUILDROOT/" \
                      "{}-{}-{}.x86_64".format(build.uniqueext,
                                               content.name,
                                               content.version,
                                               content.release)
        if package_parser.clean_directories(mock_chroot):
            # directories added to the blacklist, need to re-run
            build.package(content)
        save_mock_logs(configuration.download_path, package_parser.round)
        result = parse_log(content, package_parser)
        if result == 0 or result > 20:
            break

    # examine_abi(conf.download_path, content.name)
    if os.path.exists("/var/lib/rpm"):
        get_whatrequires(content.name, content.yum_conf)

    write_out(configuration.download_path + "/release", content.release + "\n")

    # record logcheck output
    log_check(configuration.download_path)


def log_check(pkg_loc):
    """Try to discover configuration options that were automatically switched off."""
    build_log_path = os.path.join(pkg_loc, 'results', 'build.log')
    if not os.path.exists(build_log_path):
        print('build log is missing, unable to perform logcheck.')
        return

    whitelist = []
    file_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(file_dir, 'configure_whitelist')
    with open(file_path, "r") as f:
        for line in f:
            if line.startswith("#"):
                continue
            whitelist.append(line.rstrip())

    blacklist = []
    file_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(file_dir, 'configure_blacklist')
    with open(file_path, "r") as f:
        for line in f:
            if line.startswith("#"):
                continue
            blacklist.append(line.rstrip())

    with open(build_log_path, 'r') as f:
        lines = f.readlines()

    pat = re.compile(r"^checking (?:for )?(.*?)\.\.\. no")
    misses = []
    for line in lines:
        match = None
        m = pat.search(line)
        if m:
            match = m.group(1)

        if "none required" in line:
            match = None

        if "warning: format not a string literal" in line:
            match = line

        if not match or match in whitelist:
            continue

        if match in blacklist:
            logger.error("Blacklisted configure-miss is forbidden: " + match)
            misses.append("Blacklisted configure-miss is forbidden: " + match)
            write_misses(pkg_loc, misses)
            exit(1)

        print("Configure miss: " + match)
        misses.append("Configure miss: " + match)

    if not misses:
        return

    write_misses(pkg_loc, misses)


def write_misses(pkg_loc, misses):
    """Create configure_misses file with automatically disabled configuration options."""
    write_out(os.path.join(pkg_loc, 'configure_misses'), '\n'.join(sorted(misses)))


def get_whatrequires(pkg, yum_conf):
    """
    Write list of packages.

    Write packages that require the current package to a file
    using dnf repoquery what-requires and --recursive commands.
    """
    # clean up dnf cache to avoid 'no more mirrors repo' error
    try:
        subprocess.check_output(['dnf', '--config', yum_conf,
                                 '--releasever', 'clear', 'clean', 'all'])
    except subprocess.CalledProcessError as err:
        logger.error("Unable to clean dnf repo: {}, {}".format(pkg, err))
        return

    try:
        out = subprocess.check_output(['dnf', 'repoquery',
                                       '--config', yum_conf,
                                       '--releasever', 'clear',
                                       '--archlist=src', '--recursive', '--queryformat=%{NAME}',
                                       '--whatrequires', pkg]).decode('utf-8')

    except subprocess.CalledProcessError as err:
        logger.warning("dnf repoquery whatrequires for {} failed with: {}".format(pkg, err))
        return

    write_out('whatrequires', '# This file contains recursive sources that require this package\n' + out)


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("-u", "--url", dest="url", default="",
                        help="http URL of downloading package")
    parser.add_argument("-d", "--dir", dest="directory", default="",
                        help="cloned repository of package")
    parser.add_argument("-n", "--pkg_name", dest="name", default="",
                        help="pacakge name")
    parser.add_argument("-o", "--output", dest="output", default="/tmp/autopkg/output",
                        help="Target location to create or reuse")
    parser.add_argument("-p", "--parse", dest="parse", default="true", choices=["true", "false"],
                        help="Target location to create or reuse")
    parser.add_argument("-b", "--build", dest="build", default="true", choices=["true", "false"],
                        help="Target location to create or reuse")
    parser.add_argument("-c", "--config", dest="config", action="store",
                        default="/usr/share/defaults/autospec/autospec.conf",
                        help="Set configuration file to use")
    args = parser.parse_args()
    name = args.get("name")
    url = args.get("url")
    parse_param = args.get("parse")
    need_parse = parse_param == "true"
    build_param = args.get("build")
    need_build = build_param == "true"
    directory = args.get("directory")
    output = args.get("output")
    os.makedirs(output, exist_ok=True)
    arg_result = check_only_one_arg(name=name, url=url, directory=directory)
    if arg_result != 1:
        logger.error("args error, choose one from '-u/-d/-n'")
        sys.exit(0)
    config_file = args.get("config")
    configuration.download_path = output
    source = Source(url, name, directory)
    metadata = package(source.compilations)
    spec_writer = SpecWriter(name, configuration.download_path)
    yaml_writer = YamlWriter(name, configuration.download_path)
    merge_data = verify_metadata(metadata)
    spec_writer.trans_data_to_spec(metadata)
    yaml_writer.create_yaml_package(metadata)
