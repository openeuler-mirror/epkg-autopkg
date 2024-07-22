import os
import unittest
from src.core.source import Source
from src.parse.python import PythonParse
from src.parse.perl import PerlParse
from src.parse.ruby import RubyParse
from src.parse.nodejs import NodejsParse
from src.parse.autotools import AutotoolsParse
from src.parse.maven import MavenParse
from src.parse.cmake import CMakeParse


class TestParse(unittest.TestCase):
    def setUp(self):
        self.source = Source()

    def test_detect_python(self):
        self.source.name = "requests"
        python_parser = PythonParse(self.source, "2.32.3")
        python_parser.detect_build_system()
        self.assertIsInstance(python_parser.metadata, dict)

    def test_detect_ruby(self):
        self.source.name = "requests"
        ruby_parser = RubyParse(self.source, "1.0.2")
        ruby_parser.detect_build_system()
        self.assertIsInstance(ruby_parser.metadata, dict)

    def test_detect_nodejs(self):
        self.source.name = "cronie"
        nodejs_parser = NodejsParse(self.source, "0.0.5")
        nodejs_parser.detect_build_system()
        self.assertIsInstance(nodejs_parser.metadata, dict)

    def test_detect_maven(self):
        self.source.name = "cronie"
        maven_parser = MavenParse(self.source, "0.0.5")
        maven_parser.detect_build_system()
        self.assertIsInstance(maven_parser.metadata, dict)

    def test_detect_perl(self):
        self.source.name = "DBI"
        perl_parser = PerlParse(self.source, "1.643")
        perl_parser.detect_build_system()
        self.assertIsInstance(perl_parser.metadata, dict)
