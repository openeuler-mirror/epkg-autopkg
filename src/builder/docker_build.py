import os.path

from src.config import config_path
from src.utils.cmd_util import call

class DockerBuild:
    def __init__(self):
        self.success = 0
        self.round = 0
        self.must_restart = 0
        self.file_restart = 0
        self.metadata = {}
        self.dockerfile_path = "."

    def build(self):
        self.set_dockerfile_path()
        cmd = [
            "docker",
            "build",
            "-t",
            self.dockerfile_path
        ]
        call(" ".join(cmd))

    def set_dockerfile_path(self):
        if os.path.exists(os.path.join(config_path, "dockerfile_template")):
            self.dockerfile_path = os.path.join(config_path, "dockerfile_template")
