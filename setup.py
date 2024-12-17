import os
from setuptools import setup, find_packages
from src.config import config_path

data_files = []
target_dirs = {
    "src/config": config_path,
}

def get_file_paths(prefix, directory):
    for name in os.listdir(directory):
        if os.path.isdir(os.path.join(directory, name)):
            get_file_paths(os.path.join(prefix, name), os.path.join(directory, name))
        elif name.endswith(".py"):
            continue
        else:
            data_files.append(os.path.join(prefix, name))

for rel_path, target_dir in target_dirs.items():
    get_file_paths(rel_path, target_dir)
data_files.append("src/../autopkg.py")

setup(
    name="autopkg",
    version="0.1.0",
    packages=find_packages(),
    description="...",
    license="GPL-2.0",
    author="",
    entry_points={
        "console_scripts": [
            'autopkg = autopkg:main'
        ]
    },
    include_package_data=True,
    install_requires=[
        "requests>=2.22.0",
        "pycurl>=7.45.0",
        "PyYAML>=6.0",
        "pypi_json>=0.3.0",
        "lxml>=5.2.2",
        "bs4>=0.0.2",
    ],
    data_files=[
        ("", data_files),
    ],
)
