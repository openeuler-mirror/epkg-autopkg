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
import yaml

from src.log import logger
from src.builder import scripts_path
from src.config.config import configuration


def run_docker_script(build_system, metadata):
    write_skel_shell(metadata, build_system)
    parse_yaml_args(build_system, metadata)
    cmd = f"source /root/.bashrc && epkg build {configuration.download_path}/package.yaml"
    result = os.popen(cmd).read()
    logger.info(result)
    return result


def get_build_result(metadata):
    with open(os.path.join(configuration.download_path, "package.yaml"), "w") as f:
        f.write(yaml.safe_dump(metadata))
    with open(os.path.join(scripts_path, metadata["buildSystem"] + ".sh"), "r") as f:
        content = f.read()
    with open(os.path.join(configuration.download_path, "phase.sh"), "w") as f:
        f.write(content)
    # TODO(run epkg build command)
    pass


def parse_yaml_args(build_system, info: dict):
    args = []
    for param_setting in configuration.params_setting_list:
        if param_setting in info:
            args.append(f"{param_setting}={info[param_setting].strip()}")
    if "buildRequires" in info:
        args.append("build_requires=\"" + " ".join(info["buildRequires"]) + "\"")
    with open(os.path.join(scripts_path, "params_parser.sh"), "w") as f:
        f.write("#!/usr/bin/env bash" + os.linesep*3)
        f.write("build_system=" + build_system + os.linesep)
        f.write(os.linesep.join(args) + os.linesep)
        f.write("source /root/.bashrc" + os.linesep)
        f.write("yum install -y $build_requires" + os.linesep)
        if configuration.maven_remove_plugins:
            f.write("maven_remove_plugins=" + " ".join(list(configuration.maven_remove_plugins)))
        if configuration.maven_disable_modules:
            f.write("maven_disable_modules=" + " ".join(list(configuration.maven_disable_modules)))
        if configuration.maven_delete_dirs:
            f.write("maven_rm_dirs=" + " ".join(list(configuration.maven_delete_dirs)))


def write_skel_shell(metadata, build_system):
    work_space = os.path.join(configuration.download_path, "workspace")
    license_type = metadata.get("license")
    homepage = metadata.get("homepage")
    name = metadata.get("name")
    version = metadata.get("version")
    if build_system == "python" and "setup.py" not in os.listdir(work_space):
        with open(work_space + "/setup.py", "w") as f:
            f.write(f"from setuptools import setup, find_packages{os.linesep}\
{os.linesep}\
setup({os.linesep}\
    name='{name}',{os.linesep}\
    version='{version}',{os.linesep}\
    package=find_packages(),{os.linesep}\
    install_requires=[{os.linesep}\
        'pip_line',{os.linesep}\
    ],{os.linesep}\
    author='openEuler',{os.linesep}\
    description='A short description of your project',{os.linesep}\
    license='{license_type}',{os.linesep}\
    keywords='python projects',{os.linesep}\
    url='{homepage}',{os.linesep}\
){os.linesep}")
