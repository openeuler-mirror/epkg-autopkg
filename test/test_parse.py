import unittest
from src.core.source import Source
from src.parse.python import PythonParse
from src.parse.perl import PerlParse
from src.parse.ruby import RubyParse
from src.parse.nodejs import NodejsParse
from src.parse.maven import MavenParse


class TestParse(unittest.TestCase):
    def setUp(self):
        self.source = Source()

    def test_detect_python(self):
        self.source.name = "requests"
        python_parser = PythonParse(self.source, "2.32.3")
        python_parser.parse_api_info()
        self.assertIsInstance(python_parser.metadata, dict)

    def test_detect_ruby(self):
        self.source.name = "requests"
        ruby_parser = RubyParse(self.source, "1.0.2")
        ruby_parser.parse_api_info()
        self.assertIsInstance(ruby_parser.metadata, dict)

    def test_detect_nodejs(self):
        self.source.name = "cronie"
        nodejs_parser = NodejsParse(self.source, "0.0.5")
        nodejs_parser.parse_api_info()
        self.assertIsInstance(nodejs_parser.metadata, dict)

    def test_detect_maven(self):
        self.source.group = "org.springframework"
        self.source.name = "spring-core"
        maven_parser = MavenParse(self.source, "6.1.6")
        maven_parser.parse_api_info()
        self.assertIsInstance(maven_parser.metadata, dict)

    def test_detect_perl(self):
        self.source.name = "DBI"
        perl_parser = PerlParse(self.source, "1.643")
        perl_parser.parse_api_info()
        self.assertIsInstance(perl_parser.metadata, dict)
