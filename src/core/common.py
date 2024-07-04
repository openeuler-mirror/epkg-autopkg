import os
import requests
from src.log import logger
from src.config.config import configuration
from src.utils.cmd_util import check_makefile_exist


def verify_metadata(data):
    if "phase.build" in data:
        data["phase.build"] = merge_build_pattern(data["phase.build"])
    # TODO(列举需要合并的字段)


def merge_build_pattern(data):
    # TODO(合并多编译类型)
    return data


def download_file_from_github(repo_name, version):
    search_url = "https://api.github.com/search/repositories"

    # 设置搜索参数
    search_params = {
        'q': f"{repo_name} in:name",
        'sort': 'stars',
        'order': 'desc'
    }

    # 发送搜索请求
    response = requests.get(search_url, params=search_params)
    search_results = response.json().get('items', [])

    # 遍历搜索结果，查找包含特定版本的仓库
    for item in search_results:
        repo_url = item['url']
        tags_url = f"{repo_url}/git/matches/ref/tags/{version}"

        # 检查仓库是否包含指定版本
        tags_response = requests.get(tags_url)
        if tags_response.status_code == 200 and tags_response.json():
            owner = item['owner']['login']
            # 根据组织、仓库名和版本下载源码
            download_url = f"https://api.github.com/repos/{owner}/{repo_name}/tarball/{version}"
            response = requests.get(download_url)
            # 检查响应状态码
            if response.status_code == 200:
                # 如果请求成功，保存压缩文件
                with open(f"{repo_name}-{version}.tar.gz", "wb") as file:
                    file.write(response.content)
                logger.info(f"Downloaded {repo_name} version {version} successfully.")
                ret = os.system(f"tar -xzvf {repo_name}-{version}.tar.gz")
                if ret != 0:
                    logger.error("tar cmd failed")
                repo_path = os.path.join(configuration.download_path, f"{repo_name}-{version}")
                files = os.listdir(repo_path)
                if "CMakeLists.txt" in files:
                    return "cmake"
                elif "configure" in files or "configure.ac" in files:
                    return "autotools"
                if check_makefile_exist(path=repo_path, file_name="CMakeLists.txt"):
                    return "cmake"
                elif check_makefile_exist(path=repo_path, file_name="configure"):
                    return "autotools"
                else:
                    return "make"
            else:
                logger.error(f"Failed to download {repo_name} version {version}. Status code: {response.status_code}")
                return "make"

    logger.error("can't find out repo from github")
    return "make"
