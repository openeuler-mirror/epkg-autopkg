import os
import subprocess
import src.builder
from src.log import logger
from src.config.config import configuration


def get_docker_container(name="autopkg_build"):
    cmd = subprocess.Popen(["docker", "ps", "-f", f"name={name}"], shell=False, stdout=subprocess.PIPE,
                     stderr=subprocess.PIPE)
    ret, err = cmd.communicate()
    ret_code = cmd.returncode
    if ret_code == 0:
        content = ret.decode("utf-8").strip()
        docker_container_info = content.split(os.linesep)[-1].strip()
        if docker_container_info == "" or " " not in docker_container_info:
            logger.error("can't get docker container info")
        return docker_container_info.split()[0]


def run_docker_script(build_system):
    docker_run_path = os.path.join(src.builder.scripts_path, "docker_build.sh")
    cmd = f"{docker_run_path} -b {build_system} -d {configuration.download_path} -s {src.builder.scripts_path}"
    result = os.popen(cmd).read()
    logger.info(result)
    return result


def run_docker_epkg():
    pass
