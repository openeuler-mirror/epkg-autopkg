import os
import subprocess
from src.log import logger


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



def run_docker_script(script_path):
    container_id = get_docker_container()
    ret1 = os.system(f"docker cp {script_path} {container_id}:/root")
    if ret1 != 0:
        return
    script_docker_path = os.path.join("/root", os.path.basename(script_path))
    result = os.popen(f"docker exec -ti {container_id} {script_docker_path}")
    return result
