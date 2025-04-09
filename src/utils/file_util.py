# Copyright (c) [2023] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#       http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

import os
import re
import hashlib
from src.log import logger


def get_sha1sum(filename):
    """获得文件的sha1值"""
    sh = hashlib.sha1()
    with open(filename, "rb") as f:
        content = f.read()
    sh.update(content)
    return sh.hexdigest()


def unzip_file(filename: str, output=""):
    if output == "":
        output = os.getcwd()
    if filename.endswith(".tar.gz"):
        ret = os.popen(f"tar -xzvf {filename} -C {output}").read()
        first_line = ret.split(os.linesep)[0]
        target_name = first_line.split(os.sep)[0]
        return os.path.join(output, target_name)
    elif filename.endswith(".tar.xz"):
        ret = os.popen(f"tar -xvf {filename} -C {output}").read()
        first_line = ret.split(os.linesep)[0]
        target_name = first_line.split(os.sep)[0]
        return os.path.join(output, target_name)
    elif filename.endswith(".tar.bz2"):
        ret = os.popen(f"tar -xjf {filename} -C {output}").read()
        first_line = ret.split(os.linesep)[0]
        target_name = first_line.split(os.sep)[0]
        return os.path.join(output, target_name)
    elif filename.endswith(".zip"):
        ret = os.popen(f"unzip -o {filename} -d {output}").read()
        first_line = ret.split(os.linesep)[0]
        target_name = first_line.split(os.sep)[0]
        return os.path.join(output, target_name)
    else:
        try:
            ret = os.popen(f"tar -xzvf {filename} -C {output}").read()
            first_line = ret.split(os.linesep)[0]
            target_name = first_line.split(os.sep)[0]
            return os.path.join(output, target_name)
        except Exception as e:
            logger.error("unknown src type: " + str(e))
            exit(11)

