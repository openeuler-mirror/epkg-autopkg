import os
import subprocess
from src.config.config import configuration
from src.log import logger
from src.builder import scripts_path


class DockerBuild:
    def __init__(self, build_system=""):
        self.container_name = "autopkg_build"
        self.image_name = "autopkg"
        self.image_tag = "latest"
        self.build_system = build_system
        self.container_id = ""

    def docker_build(self):
        self.remove_docker_container()
        self.container_id = self.create_container()
        self.copy_source_into_container()
        self.run_build()
        self.check_build_log()

    def remove_docker_container(self):
        # 删除原来的容器
        logger.info("remove old docker container")
        cmd = os.popen(f"docker ps |grep {self.container_name}")
        ret0 = cmd.read().strip()
        if " " in ret0:
            old_container_id = ret0.split()[0]
        else:
            return
        ret = os.system(f"docker rm {old_container_id} -f")
        if ret != 0:
            logger.info("no such docker container")

    def create_container(self):
        # 创建新的容器，假设镜像已经生成
        logger.info("create docker container")
        cmd = subprocess.Popen(["docker", "run", "-dti", "--privileged", f"--name={self.container_name}",
                                f"{self.image_name}:{self.image_tag}", "/bin/bash", "-D", "-e"], shell=False,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        ret, err = cmd.communicate()
        ret_code = cmd.returncode
        if ret_code == 0:
            content = ret.decode('utf-8').strip()
            docker_container = content.split(os.linesep)[-1]
        else:
            logger.error("cannot get docker container number")
            exit(3)
        return docker_container

    def copy_source_into_container(self):
        # 复制源码到容器中
        logger.info("copy in source code")
        cmd = subprocess.Popen(["docker", "cp", f"{configuration.download_path}/workspace",
                                f"{self.container_id}:/root"], shell=False,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        ret, err = cmd.communicate()
        ret_code = cmd.returncode
        if ret_code == 0:
            content = ret.decode('utf-8').strip()
            docker_container = content.split(os.linesep)[-1]
        else:
            logger.error("cannot copy src into docker container")
            exit(3)
        logger.info("copy in scripts")
        os.system(f"chmod 755 {scripts_path}/*.sh")
        os.system(f"docker cp {scripts_path}/{self.build_system}.sh {self.container_id}:/root")
        os.system(f"docker cp {scripts_path}/generic-build.sh {self.container_id}:/root")
        return docker_container

    def run_build(self):
        # docker容器构建，生成build log
        cmd = subprocess.Popen(["docker", "exec", f"{self.container_id}", "/root/generic-build.sh"],
                               shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        ret, err = cmd.communicate()
        ret_code = cmd.returncode
        log_path = os.path.join(configuration.download_path, configuration.logfile)
        error_log_path = os.path.join(configuration.download_path, "error-build.log")
        if ret_code == 0:
            with open(log_path, "w") as f:
                f.write(ret.decode("utf-8"))
                f.write(err.decode("utf-8"))
            logger.info("build success")
        else:
            with open(log_path, "w") as f:
                f.write(ret.decode("utf-8"))
            with open(error_log_path, "w") as f:
                f.write(err.decode("utf-8"))
            logger.warning("logger failed")
        logger.info("write build log success")

    def check_build_log(self):
        # 获取容器中的build日志文件
        log_path = os.path.join(configuration.download_path, configuration.logfile)
        if os.path.exists(log_path):
            with open(log_path, "r") as f:
                content = f.read()
            if content == "":
                logger.error("empty log file from docker:" + self.container_id)
