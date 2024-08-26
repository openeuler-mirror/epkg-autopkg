import os
import subprocess
import yaml
from src.log import logger
from src.builder import scripts_path
from src.config.config import configuration
from src.config.yamls import yaml_path


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


def run_docker_script(build_system, metadata, num):
    parse_yaml_args(build_system, metadata)
    docker_run_path = os.path.join(scripts_path, "docker_build.sh")
    cmd = f"{docker_run_path} -b {build_system} -d {configuration.download_path} -s {scripts_path} -n {num}"
    result = os.popen(cmd).read()
    logger.info(result)
    return result


def run_docker_epkg():
    pass


def parse_yaml_args(build_system, info: dict):
    build_system_yaml = os.path.join(yaml_path, f"{build_system}.yaml")
    if os.path.exists(build_system_yaml):
        with open(build_system_yaml, "r") as f:
            build_system_content = f.read()
        build_system_items = yaml.safe_load(build_system_content)
        for keywords, build_system_item in build_system_items.items():
            if keywords in ["buildRequires", "requires", "provides", "conflicts"]:
                for req in build_system_item:
                    if keywords in info and req in info[keywords]:
                        continue
                    info.setdefault(keywords, []).append(req)
            elif keywords in ["makeFlags", "configureFlags", "cmakeFlags"]:
                info[keywords] += build_system_item
            else:
                info[keywords] = build_system_item
    args = []
    if "makeFlags" in info:
        args.append("makeFlags=" + info["makeFlags"].strip())
    if "cmakeFlags" in info:
        args.append("cmakeFlags=" + info["cmakeFlags"].strip())
    if "configureFlags" in info:
        args.append("configureFlags=" + info["configureFlags"].strip())
    if "buildRequires" in info:
        args.append("build_requires=\"" + " ".join(info["buildRequires"]) + "\"")
    with open(os.path.join(scripts_path, "params_parser.sh"), "w") as f:
        f.write("#!/usr/bin/env bash" + os.linesep*3)
        f.write("build_system=" + build_system + os.linesep)
        f.write(os.linesep.join(args) + os.linesep)
        f.write("source /root/.bashrc" + os.linesep)
        f.write("yum install -y $build_requires" + os.linesep)
