from src.log import logger


class BasicParse:
    def __init__(self, name, url=""):
        self.language = ""
        self.compilation = ""
        self.url = url
        self.version = ""
        self.url = ""
        self.license = ""
        self.commands = []
        self.build_requires = set()
        self.pacakge_name = name
        self.metadata = {}
        self.files = {}

    def init_metadata(self):
        if self.url == "" and self.pacakge_name:
            self.url = f"https://localhost:8080/{self.pacakge_name}-0.0.1.tar.gz"
        self.metadata.setdefault("rpmGlobal", {}).setdefault("debug_package", "%{nil}")
        self.metadata["rpmGlobal"]["__strip"] = "/bin/true"
        self.metadata.setdefault("name", self.pacakge_name)
        self.metadata.setdefault("homepage", self.url)
        self.metadata.setdefault("source", {}).setdefault("0", self.url)
        self.metadata.setdefault("release", 0)
        self.files.setdefault("files", "%default(-,root,root,-)")
