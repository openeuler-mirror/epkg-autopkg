import os
import unittest
from src.core.source import Source
from src.yaml_maker import YamlMaker
from src.config import config_path


class TestParse(unittest.TestCase):
    def setUp(self):
        self.source = Source()
        self.yaml_maker = YamlMaker(tarball_url="https://1111/BasicTS-1.0.0.tar.gz")

    def test_name_and_version(self):
        self.source.name = "requests"
        name, version = self.yaml_maker.name_and_version()
        # https://invisible-mirror.net/archives/lynx/tar/lynx2.8.9rel.1.tar.gz
        self.assertEqual(name, "BasicTS")
        self.assertEqual(version, "1.0.0")

    def test_scan_compilation(self):
        self.yaml_maker.path = os.path.relpath(os.path.relpath(config_path))
        self.yaml_maker.scan_compilations()