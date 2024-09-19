from setuptools import setup, find_packages

setup(
    name="openEulerTransition",
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
    ],
    data_files=[
        ("", ["src/../autopkg.py"]),
    ],
)
