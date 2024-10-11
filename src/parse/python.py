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
import json
from urllib import request
from pypi_json import PyPIJSON
from src.parse.basic_parse import BasicParse
from src.log import logger
from src.builder import scripts_path
from src.config.config import configuration


class PythonParse(BasicParse):
    def __init__(self, source, version=""):
        super().__init__(source)
        name = source.name
        self.version = version if version != "" else source.version
        self.url_template = f'https://pypi.org/pypi/{name}/json'
        self.url_template_with_ver = f'https://pypi.org/pypi/{name}/{version}/json'
        self.__json = None
        self.__build_noarch = True
        if self.version == "":
            self.find_latest_version()
        self.compile_type = "python"

    def parse_api_info(self):
        if not self.version:
            url = self.url_template.format(pkg_name=self.pacakge_name)
        else:
            url = self.url_template_with_ver.format(pkg_name=self.pacakge_name, pkg_ver=self.version)

        try:
            with request.urlopen(url, timeout=30) as u:
                self.__json = json.loads(u.read().decode('utf-8'))
        except Exception as err:
            logger.error(f"The package:{self.pacakge_name} ver:{self.version} does not existed on pypi:" + str(err))
            sys.exit(5)
        if self.__json is not None:
            self.metadata.setdefault("name", self.__json["info"]["name"])
            self.metadata = {
                "name": self.__json["info"]["name"],
                "version": self.version,
                "meta": {
                    "summary": self.__json["info"]["summary"],
                    "description": self.__json["info"]["description"]
                },
                "license": self.__json["info"]["license"],
                "release": 1,
                "homepage": self.__json["info"]["package_url"],
                "source": {0: self.__json["urls"][0]["url"]},
                "buildSystem": "python"
            }
            self.metadata.setdefault("buildRequires", ["python3"])
            if "provides_extra" in self.__json["info"] and self.__json["info"]["provides_extra"]:
                self.metadata.setdefault("provides", self.__json["info"]["provides_extra"])
            if "requires_dist" in self.__json["info"] and self.__json["info"]["requires_dist"]:
                self.metadata.setdefault("requires", self.__json["info"]["requires_dist"])

    def check_compilation_conf(self, path):
        if "setup.py" not in os.listdir(path):
            with open("setup.py", "w") as f:
                f.write(
                    f"from setuptools import setup, find_packages{os.linesep} \
{os.linesep}\
setup({os.linesep}\
    name='{self.pacakge_name}',{os.linesep}\
    version='{self.version}',{os.linesep}\
    package=find_packages()\
    install_requires=[{os.linesep}\
        'pip_line',{os.linesep}\
    ],{os.linesep}\
    author='autopkg',{os.linesep}\
    description='A short description of your project',{os.linesep}\
    license='{self.license}',{os.linesep}\
    keywords='python example',{os.linesep}\
    url='{self.url}',{os.linesep}\
){os.linesep}")

    def find_latest_version(self):
        pass

    def __get_buildarch(self):
        """
        if this module has a prebuild package for amd64, then it is arch dependent.
        print BuildArch tag if needed.
        """
        rs = self.get_releases()
        for r in rs:
            if r["packagetype"] == "bdist_wheel" and "amd64" in r["url"]:
                return False
        return True

    def get_releases(self):
        """
        The https://pypi.org/pypi/{pkg}/json API contains both "releases" and "urls" keys
        The version specified https://pypi.org/pypi/{pkg}/{ver}/json API contains only "urls"
        If user specified a version, we need grab release info from "urls"
        """
        if "releases" in self.__json.keys():
            return self.__json["releases"][self.version]
        elif "urls" in self.__json.keys():
            return self.__json["urls"]
        else:
            return []

    def get_source_info(self):
        """
        return a map of source filename, md5 of source, source url
        return None in errors
        """
        rs = self.get_releases()
        for r in rs:
            if r["packagetype"] == "sdist":
                return {
                    "filename": r["filename"],
                    "md5": r["md5_digest"],
                    "url": r["url"]
                }
        return None

    def parse_metadata(self):
        self.init_metadata()
        self.metadata.setdefault("buildSystem", "make")
        self.init_scripts()

    def init_scripts(self):
        # TODO(self.scripts中增加编译函数)
        pass
