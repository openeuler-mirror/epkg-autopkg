# Copyright (c) [2023] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#       http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.


import subprocess
import sys
from io import BytesIO
from src.log import logger


def do_curl(url, dest=None, post=None, is_fatal=False):
    """Perform a curl operation for `url` using system curl command."""
    curl_cmd = [
        'curl', '-L', '--fail', '--max-time', '600', '--connect-timeout', '10',
        '--speed-limit', '1', '--speed-time', '10',  '--insecure', url
    ]

    if post:
        curl_cmd.extend(['--data', post])

    try:
        if dest:
            # 直接写入目标文件
            subprocess.run(curl_cmd, check=True, stdout=open(dest, 'wb'))
            return dest
        else:
            # 捕获输出到内存
            result = subprocess.run(curl_cmd, check=True, capture_output=True)
            buf = BytesIO(result.stdout)
            return buf
    except Exception as e:
        if is_fatal:
            logger.error("can't request {}: {}".format(url, e))
            sys.exit(1)
        return None


def clone_code(path, url, specific_branch="master"):
    cmd = ["git", "clone", "--depth=1", "-b", specific_branch, url, path]
    subprocess.check_call(cmd)
