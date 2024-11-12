import os
import unittest
from src.yaml_maker import YamlMaker


class TestParse(unittest.TestCase):
    def setUp(self):
        pass

    def test_detect_autotools(self):
        tarball_url = "http://download.savannah.nongnu.org/releases/acl/acl-2.3.2.tar.xz"
        yaml_maker = YamlMaker(tarball_url=tarball_url)
        yaml_maker.create_yaml()
        self.assertTrue(os.path.exists("/tmp/autopkg/output/build.log"))
        with open("/tmp/autopkg/output/build.log", "r") as f:
            content = f.read()
        self.assertTrue("build success" in content)

    def test_detect_cmake(self):
        tarball_url = "https://github.com/google/leveldb/archive/1.21/leveldb-1.21.tar.gz"
        yaml_maker = YamlMaker(tarball_url=tarball_url)
        yaml_maker.create_yaml()
        self.assertTrue(os.path.exists("/tmp/autopkg/output/build.log"))
        with open("/tmp/autopkg/output/build.log", "r") as f:
            content = f.read()
        self.assertTrue("build success" in content)

    def test_detect_meson(self):
        tarball_url = "https://github.com/mpv-player/mpv/archive/v0.35.1/mpv-0.35.1.tar.gz"
        yaml_maker = YamlMaker(tarball_url=tarball_url)
        yaml_maker.create_yaml()
        self.assertTrue(os.path.exists("/tmp/autopkg/output/build.log"))
        with open("/tmp/autopkg/output/build.log", "r") as f:
            content = f.read()
        self.assertTrue("build success" in content)

    def test_detect_python(self):
        git_url = "https://gitee.com/qiu-tangke/autopkg.git"
        yaml_maker = YamlMaker(git_url=git_url)
        yaml_maker.create_yaml()
        self.assertTrue(os.path.exists("/tmp/autopkg/output/build.log"))
        with open("/tmp/autopkg/output/build.log", "r") as f:
            content = f.read()
        self.assertTrue("build success" in content)

    def test_detect_ruby(self):
        tarball_url = "https://github.com/jekyll/jekyll/archive/refs/tags/v4.3.4.tar.gz"
        yaml_maker = YamlMaker(tarball_url=tarball_url)
        yaml_maker.create_yaml()
        self.assertTrue(os.path.exists("/tmp/autopkg/output/build.log"))
        with open("/tmp/autopkg/output/build.log", "r") as f:
            content = f.read()
        self.assertTrue("build success" in content)
