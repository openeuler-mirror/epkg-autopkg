import os
import sys
import json
import urllib
from urllib import request
from pypi_json import PyPIJSON
from src.parse.basic_parse import BasicParse
from src.log import logger


class PythonParse(BasicParse):
    def __init__(self, name, version=""):
        super().__init__(name)
        self.url_template = f'https://pypi.org/pypi/{name}/json'
        self.url_template_with_ver = f'https://pypi.org/pypi/{name}/{pkg_ver}/json'
        self.__json = None
        self.version = version
        self.__build_noarch = True
        if self.version == "":
            self.find_latest_version()

    def detect_build_system(self):
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
            self.metadata.setdefault("version", self.version)

    def download_from_upstream(self):
        if not self.version:
            url = self.url_template
        else:
            url = self.url_template_with_ver


    def get_src_url_and_depends(self, client, pkg):
        success = False
        try_num = 0
        while not success:
            try:
                self.metadata = client.get_metadata(pkg)
                success = True
            except Exception as e:
                logger.error(str(e))
                success = False
                try_num += 1
                if try_num > 20:
                    logger.warning(pkg, 'has tried 20 times.')
                    break

    def get_pypi_info(self):
        with PyPIJSON() as self.client:
            self.get_src_url_and_depends(self.client, self.pacakge_name)

    def check_compilation_conf(self, path):
        if "setup.py" not in os.listdir(path):
            self.commands.append(
                "cat >> setup.py << EOF"
                f"from setuptools import setup, find_packages{os.linesep} \
{os.linesep}\
setup({os.linesep}\
    name='{self.pacakge_name}',{os.linesep}\
    version='{self.version}',{os.linesep}\
    package=find_packages()\
    install_requires=[{os.linesep}\
        'pip_line',{os.linesep}\
    ],{os.linesep}\
    author='openEuler',{os.linesep}\
    description='A short description of your project',{os.linesep}\
    license='{self.license}',{os.linesep}\
    keywords='python example',{os.linesep}\
    url='{self.url}',{os.linesep}\
){os.linesep}\
EOF")

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
        self.init_scripts()

    def init_scripts(self):
        # TODO(self.scripts中增加编译函数)
        pass
