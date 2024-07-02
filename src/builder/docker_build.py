import os
import subprocess
from src.config.config import configuration
from src.log import logger


class DockerBuild:
    def __init__(self):
        self.contain_name = "autopkg_build"
        self.image_name = "autopkg"
        self.image_tag = "latest"

    def docker_build(self):
        self.remove_docker_contain()
        self.create_contain()
        self.run_build()
        self.get_build_log()

    def remove_docker_contain(self):
        ret = os.system(f"docker rm {self.contain_name} -f")
        if ret != 0:
            logger.info("no such docker contain")

    def create_contain(self):
        cmd = subprocess.Popen(["docker", "run", "-dti", "--privileged", f"--name={self.contain_name}",
                                f"{self.image_name}:{self.image_tag}", "/bin/bash", "-D", "-e"], shell=False,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        ret, err = cmd.communicate()
        ret_code = cmd.returncode
        if ret_code == 0:
            content = ret.decode('utf-8').strip()
            docker_contain = content.split(os.linesep)[-1]
        else:
            logger.error("cannot get docker contain number")
            exit(3)
        return docker_contain

    def run_build(self):
        cmd = subprocess.Popen(["docker", "exec", "-ti", f"{self.contain_name}", "/root/build.sh"],
                               shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        ret, err = cmd.communicate()
        ret_code = cmd.returncode
        if ret_code == 0:
            content = ret.decode('utf-8').strip()
            if "build success" in content:
                logger.info("build success")
        else:
            logger.warning("logger failed")

    def get_build_log(self):
        ret1 = os.system(f"docker cp {self.contain_name}:/root/result {configuration.download_path}")
        if ret1 != 0:
            logger.error("no log file in container")
            exit(4)
