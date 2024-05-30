import os

from pypi_json import PyPIJSON
from src.parse.basic_parse import BasicParse
from src.log import logger


class PythonParse(BasicParse):
    def __init__(self, name):
        super().__init__(name)

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
