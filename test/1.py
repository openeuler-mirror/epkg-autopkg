# -*- coding: utf-8 -*-
import datetime
import os
import stat
import shutil
import logging
import subprocess
import argparse
from copy import copy
from logging import handlers
from xlrd import open_workbook
import xlwt
from xlutils.copy import copy
import requests as requests
import pandas as pd
from func_timeout import func_set_timeout


def excel2txt(excel_path):
    txt_path = excel_path.replace(".xlsx", ".txt")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    modes = stat.S_IWUSR | stat.S_IRUSR
    with os.fdopen(os.open(txt_path, flags, modes), "w") as fe:
        sheet = open_workbook(excel_path).sheet_by_name("Sheet1")
        for i in range(1, sheet.nrows):
            line = sheet.cell(i, 1).value
            fe.write(line + "\n")
    fe.close()
    return txt_path


def create_excel():
    xls = xlwt.Workbook()
    sheet = xls.add_sheet(SHEET_NAME)
    col_list = ["repo", "spec", "source", "branch"]
    for index_col, col in enumerate(col_list):
        sheet.write(0, index_col, col)
    xls.save(OUTPUT_FILE)


def write_excel(info):
    file = open_workbook(OUTPUT_FILE)
    excel = copy(file)
    sheet = excel.get_sheet(0)
    if info.repo:
        row_list = [info.repo, info.spec, info.source_url, info.branch]
        nrow = sheet.rows.__len__()
        for i, row in enumerate(row_list):
            sheet.write(nrow, i, row)
        remove_repo_code(info.repo)
        excel.save(OUTPUT_FILE)


class PackageInfo:
    def __init__(self):
        self.repo = ""
        self.spec = "https://gitee.com/src-openeuler/{0}/{1}"
        self.source_url = ""
        self.branch = BRANCH


def modify_excel(info: PackageInfo, excel_file):
    ef = open_workbook(excel_file)
    index = ef.sheet_names()[0]
    sheet = ef.sheet_by_name(index)
    nrows = sheet.nrows
    for i in range(nrows):
        item_value = sheet.row_values(i)
        if item_value[0] == info.repo:
            for j, member in enumerate(item_value):
                sheet["{1}{0}".format(i, chr(ord(str(j))+49))] = member


DEBUG = logging.DEBUG
INFO = logging.INFO
WARN = logging.WARNING
ERROR = logging.ERROR
CRITICAL = logging.CRITICAL

LOG_LEVEL = DEBUG

if os.getenv('CI_BUILD_DEBUG') != 'True':
    LOG_LEVEL = INFO
count = 0


class LogInfo:
    def __init__(self, ):
        pass

    @staticmethod
    def header(component=None, action=None, stage=None, func=None, file_line=None):
        log_info = "====>[component: {}]--[action: {}]--[stage: {}]<====->func: {}--file_line: {}".format(
            component, action, stage, func, file_line
        )
        return log_info


class Logger(object):
    def __init__(self, name, clevel=LOG_LEVEL,
                 log_file_path=None):
        fmt = logging.Formatter("%(asctime)s - [%(levelname)s] : %(message)s")

        ch = logging.StreamHandler()
        ch.setLevel(clevel)
        ch.setFormatter(fmt)
        self.logger = logging.getLogger(name)
        self.logger.setLevel(DEBUG)
        self.logger.addHandler(ch)
        if log_file_path:
            time_file_handler = handlers.TimedRotatingFileHandler(filename=log_file_path, when='D')
            time_file_handler.setLevel(logging.DEBUG)
            time_file_handler.setFormatter(fmt)
            self.logger.addHandler(time_file_handler)

    def debug(self, message):
        self.logger.debug(message)

    def info(self, message):
        self.logger.info(message)

    def warn(self, message):
        self.logger.warning(message)

    def error(self, message):
        self.logger.error(message)

    def critical(self, message):
        self.logger.critical(message)


@func_set_timeout(10)
def find_local_file(repo):
    destination = os.getcwd() + os.path.sep + "src_code" + os.path.sep + repo
    if not os.path.exists(destination):
        os.makedirs(destination, exist_ok=True)
    remote_name = os.popen("ls -S {0} | grep -v .spec | grep -v .yaml | grep -v .patch | grep -v .md | head -n 1"
                           .format(os.getcwd() + os.path.sep + "gitee_code" + os.path.sep + repo)).read().strip()
    if remote_name == "":
        return ""
    return os.getcwd() + os.path.sep + "gitee_code" + os.path.sep + repo + os.path.sep + remote_name


def remove_repo_code(repo):
    if os.path.exists(os.getcwd() + os.path.sep + "gitee_code" + os.path.sep + repo):
        try:
            shutil.rmtree(os.getcwd() + os.path.sep + "gitee_code" + os.path.sep + repo)
        except Exception:
            logger.info("fail to delete repo " + repo)
    if os.path.exists(os.getcwd() + os.path.sep + "src_code" + os.path.sep + repo):
        try:
            shutil.rmtree(os.getcwd() + os.path.sep + "src_code" + os.path.sep + repo)
        except Exception:
            logger.info("fail to delete src " + repo)


def find_file(repo):
    info = PackageInfo()
    url = get_spec_url(repo)
    if not url:
        info.source_url = '--error--'
        info.repo = repo
        info.spec = "--error: no spec file--"
        return info
    elif url == "IndexError":
        info.source_url = '--error--'
        info.repo = repo
        info.spec = "no effective source value"
        return info
    remote_name = os.path.basename(url)
    spec_path = os.getcwd() + os.path.sep + "gitee_code" + os.path.sep + repo + os.path.sep + repo + ".spec"
    tarball_path = os.getcwd() + os.path.sep + "gitee_code" + os.path.sep + repo + os.path.sep + remote_name
    if not os.path.exists(tarball_path):
        tarball_path = find_local_file(repo)
    if os.path.exists(spec_path):
        spec_url = f"https://gitee.com/src-openeuler/{repo}/blob/{BRANCH}/{repo}.spec"
    else:
        name = get_spec_name(os.getcwd() + os.path.sep + "gitee_code" + os.path.sep + repo, repo)
        spec_url = f"https://gitee.com/src-openeuler/{repo}/blob/{BRANCH}/{name}"
    source_path = decompress_tarball(tarball_path)
    info.source_url = url
    info.spec = spec_url
    info.repo = repo
    if os.path.exists(source_path):
        result = check_file(source_path)
        if result:
            write_excel(info)
            with open("result.txt", "a") as f:
                f.write(info.repo + " " + info.spec + " " + info.source_url + " " + os.linesep)
        result1 = check_file(source_path, name="meson.build")
        if result1:
            with open("meson_result.txt", "a") as f:
                f.write(info.repo + " " + info.spec + " " + info.source_url + " " + os.linesep)
    return info


def decompress_tarball(path):
    pwd = os.getcwd()
    src_path = os.path.dirname(path)
    os.chdir(src_path)
    name = os.path.basename(path)
    base_name = name
    if name.endswith(".zip"):
        os.system("unzip " + name)
        base_name = name.replace(".zip", "")
    elif name.endswith(".tar.xz"):
        os.system("tar -xvf " + name)
        base_name = name.replace(".tar.xz", "")
    elif name.endswith(".tar.gz"):
        os.system("tar -xzvf " + name)
        base_name = name.replace(".tar.gz", "")
    os.chdir(pwd)
    if "." not in name:
        return os.path.join(src_path, base_name)
    return os.path.join(src_path, base_name)


def check_file(path, name=""):
    if name == "":
        name = CHECKED_FILE
    if name == "configure":
        logger.info("don't check in cmake project")
        ret0 = os.popen(f"find {path} -name CMakeLists.txt").read()
        if ret0.strip() != "":
            return False
    logger.info("find file:" + name)
    ret = os.popen(f"find {path} -name {name}").read()
    return ret.strip() != ""


def get_spec_name(path, repo):
    files = os.listdir(path)
    names = []
    for file in files:
        if file.endswith(".spec"):
            names.append(file)
    if len(names) == 1:
        return names[0]
    else:
        return find_similar_file(names, repo)


def get_spec_url(repo):
    """
    linux解析spec
    :param repo:
    :return:
    """
    spec_file = os.getcwd() + os.path.sep + "gitee_code" + os.path.sep + repo + os.path.sep + "{0}.spec".format(
            repo)
    if not os.path.exists(spec_file):
        temp_file_list = os.listdir(os.getcwd() + os.path.sep + "gitee_code" + os.path.sep + repo)
        spec_file_list = []
        for temp_file in temp_file_list:
            if temp_file.endswith(".spec"):
                spec_file_list.append(temp_file)
        if len(spec_file_list) == 1:
            spec_file = os.getcwd() + os.path.sep + "gitee_code" + os.path.sep + repo + os.path.sep + spec_file_list[0]
        elif len(spec_file_list) > 1:
            spec_file = find_similar_file(spec_file_list, repo)
        else:
            return ""
    source_path = "/root/rpmbuild/SOURCES"
    os.makedirs(source_path, exist_ok=True)
    os.system(f"cp {os.path.dirname(spec_file)}/* {source_path}")
    ret0 = os.system(f"rpmspec -P {spec_file} > tmp_{os.path.basename(spec_file)}")
    if ret0 != 0:
        logger.info("cannot parse this spec file")
    else:
        os.system(f"mv tmp_{os.path.basename(spec_file)} {spec_file} -f")
    content = os.popen("spectool -S {0}".format(spec_file)).read().strip()
    source0 = content.split(os.linesep)[0].strip() if os.linesep in content else content.strip()
    if ":" in source0:
        source0 = ":".join(source0.split(":")[1:]).strip()
    elif "No such file or directory" in source0:
        return ""
    else:
        return "IndexError"
    return source0


def find_similar_file(file_list, pkg):
    for s_file in file_list:
        if pkg in s_file or s_file in pkg:
            spec_file = os.getcwd() + os.path.sep + "gitee_code" + os.path.sep + pkg + os.path.sep + s_file
            return spec_file
    return ""


def request_code(repo):
    url = "https://gitee.com/api/v5/repos/{0}/{1}/branches/{2}".format(OWNER, repo, BRANCH)
    params = {'repo': repo, 'branch': BRANCH, 'access_token': ACCESS_TOKEN, 'owner': OWNER}
    return try_clone_code(url, repo, params)


def try_clone_code(web, pkg, params):
    if requests.get(web, params=params).ok:
        path = os.getcwd() + os.path.sep + "gitee_code" + os.path.sep + pkg
        if not os.path.exists(path):
            os.makedirs(path, exist_ok=True)
            try:
                clone_code(path, pkg, BRANCH)
            except Exception as e:
                logger.error("clone code error:" + str(e))
                return False
        return True
    return False


def run_git(*args):
    return subprocess.check_call(['git'] + list(args), timeout=100)


def clone_code(path, repo, specific_branch):
    url = "https://toscode.gitee.com/src-openeuler/{0}.git".format(repo)
    run_git("clone", "--depth=1", "-b", specific_branch, url, path)


def get_ret_pages(params, url="https://gitee.com/api/v5/orgs/src-openeuler/repos"):
    return requests.get(url, params=params).headers.get('total_page')


def get_ret_url(params, url="https://gitee.com/api/v5/orgs/src-openeuler/repos"):
    if "page" in params and isinstance(params["page"], int):
        params["page"] = params["page"] - 1
    rets = requests.get(url, params=params).json()
    for ret in rets:
        global count
        count += 1
        if count < 2663:
            continue
        repo = ret['name']
        logger.info("================>>" + str(count))
        result = request_code(repo)
        logger.info(f"git clone {repo} code successful")
        if result:
            info = find_file(repo)
            logger.info(info.spec)


def remove_duplicate():
    excel = pd.read_excel(OUTPUT_FILE, SHEET_NAME)
    df = pd.DataFrame(excel)
    dd = df.drop_duplicates(keep='last')
    dd.to_excel(OUTPUT_FILE)


ACCESS_TOKEN = '6d159d65b4fe80c7b1ba1bad0fdb8191'
DB = ''
BRANCH = ''
OWNER = 'src-openeuler'
SHEET_NAME = 'Sheet1'
package_all_count = {}
finished_count = {}

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-o', '--output',
        dest='res_path',
        default='output.xls',
        help='output report'
    )
    parser.add_argument(
        '-b', '--branch',
        dest='branch',
        default='master',
        help='target branch'
    )
    parser.add_argument(
        '-f', '--file',
        dest='file',
        default='configure.ac',
        help='target checked file'
    )
    parser.add_argument(
        '-l', '--log_name',
        dest='log_name',
        default='default.log',
        help='log name'
    )
    input_args = parser.parse_args()
    BRANCH = input_args.branch
    CHECKED_FILE = input_args.file
    OUTPUT_FILE = input_args.res_path
    log_name = input_args.log_name
    if log_name == "default.log":
        log_name = "source_check.log"
        logger = Logger("build", log_file_path=os.path.join(os.getcwd(), log_name))
    else:
        logger = Logger("build", log_file_path=os.path.join(os.getcwd(), log_name))
    # Unified log format，change WARNING to WARN
    logging.addLevelName(WARN, 'WARN')
    if os.path.exists(OUTPUT_FILE):
        os.remove(OUTPUT_FILE)
    try:
        create_excel()
    except Exception as ex:
        logger.error("exception :{0}".format(str(ex)))
        exit()

    PAGE = 0
    PER_PAGE = 100
    pages = get_ret_pages({"access_token": ACCESS_TOKEN, "page": 1, "per_page": PER_PAGE})
    while PAGE <= int(pages):
        PAGE += 1
        param = {"access_token": ACCESS_TOKEN, "page": PAGE, "per_page": PER_PAGE}
        get_ret_url(param)
    logger.info("====>source check finished.")
