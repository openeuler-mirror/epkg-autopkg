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
from src.config.config import configuration


def run_docker_script(build_system, metadata, num):
    write_skel_shell(metadata, build_system)
    cmd = "source /root/.bashrc && epkg build {0}/package.yaml 2>&1 | tee {0}/{1}-build.log".format(
        configuration.download_path, num)
    result = os.popen(cmd).read()
    os.system("\\cp {0}/{1}-build.log {0}/build.log".format(configuration.download_path, num))
    logger.info(result)
    return result


def get_build_result(metadata):
    with open(os.path.join(configuration.download_path, "package.yaml"), "w") as f:
        f.write(yaml.safe_dump(metadata))
    # TODO(run epkg build command)
    os.system("\cp /root/.cache/epkg/build-workspace/epkg/* " + configuration.download_path)
    pass


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
