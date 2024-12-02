# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; specifically version 2 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
#
# See LICENSE for more details.
#
# Copyright: Red Hat (c) 2023 and Avocado contributors

import os
import shlex
import subprocess
from collections import Counter
from src.log import logger


def call(command, **kwargs):
    """命令套件"""
    full_args = {
        "args": shlex.split(command),
        "universal_newlines": True,
    }
    full_args.update(kwargs)

    return_code = subprocess.call(**full_args)
    logger.info(command + ": " + return_code)

    return return_code


def list_all_file(command, file="Makefile"):
    res = os.popen(" ".join(command))
    output = res.read()
    if " " in output and file in output:
        return output.split()[0]
    elif file in output:
        return output.strip()
    return ""


def check_makefile_exist(files, path="", file_name="Makefile", ):
    if path == "":
        # 在文件列表中查找文件
        result = []
        for file in files:
            if file.endswith(file_name):
                result.append(file)
        return result[0] if result else ""
    if not os.path.exists(path):
        return ''
    # 在目录中用命令查找文件
    result = list_all_file(['ls', f'{path}/*/{file_name}'], file_name)
    if not result:
        return list_all_file(['ls', f'{path}/*/*/{file_name}'], file_name)
    return result


def has_file_type(path, _type):
    res = os.popen(f"find {path} -name \*.{_type}")
    output = res.read()
    if output and f"{_type}" in output:
        return True
    return False


def get_package_by_file(file_name):
    p = subprocess.Popen(['dnf', 'provides', file_name], shell=False, stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE)
    ret, err = p.communicate()
    retcode = p.returncode
    if retcode == 0:
        content = ret.decode('utf-8')
        pkg_line = content.split('\n')[1]
        pkg0 = pkg_line.split()[0]
        pkg1 = pkg0.split('-')[:-2]
        pkg = '-'.join(pkg1)
    else:
        pkg = ''
    return pkg


def infer_language(file_list):
    language_map = {
        '.py': 'python',
        '.rb': 'ruby',
        '.c': 'c/c++',
        '.cpp': 'c/c++',
        '.cc': 'c/c++',  # 另一个常见的 C++ 扩展名
        '.cxx': 'c/c++',  # 另一个常见的 C++ 扩展名
        '.h': 'c/c++',  # 头文件通常与 C++ 关联
        '.hpp': 'c/c++',  # 头文件通常与 C++ 关联
        '.java': 'java',
        '.go': 'go',
        '.sh': 'shell',
        '.pl': 'perl',
        '.js': 'nodejs',
        '.ts': 'nodejs',
    }
    # 提取文件扩展名
    extensions = [os.path.splitext(file)[1].lower() for file in file_list]

    # 统计扩展名出现次数
    extension_counts = Counter(extensions)

    # 合并 C/C++ 的头文件和源文件
    c_cpp_count = sum(extension_counts.pop(ext, 0) for ext in ['.c','.cpp', '.cc', '.cxx', '.h', '.hpp'])

    # 将合并后的计数重新加入到计数器中
    extension_counts['.cpp'] = c_cpp_count

    # 过滤掉不在语言映射中的扩展名
    filtered_counts = {ext: count for ext, count in extension_counts.items() if ext in language_map}

    if not filtered_counts:
        return "Unknown"

    # 找到最常见的扩展名
    most_common_extension = max(filtered_counts, key=filtered_counts.get)

    # 返回对应的编程语言
    return language_map.get(most_common_extension, "Unknown")
