# SPDX-License-Identifier: MulanPSL-2.0+
# Copyright (c) 2022 Huawei Technologies Co., Ltd. All rights reserved.

import os
import shlex
import subprocess
import sys

dictionary_filename = os.path.dirname(__file__) + "/translate.dic"
dictionary = [line.strip() for line in open(dictionary_filename, 'r')]
os_paths = None


def call(command, logfile=None, check=True, **kwargs):
    """Subprocess.call convenience wrapper."""
    full_args = {
        "args": shlex.split(command),
        "universal_newlines": True,
    }
    full_args.update(kwargs)

    if logfile:
        full_args["stdout"] = open(logfile, "w")
        full_args["stderr"] = subprocess.STDOUT
        return_code = subprocess.call(**full_args)
        full_args["stdout"].close()
    else:
        return_code = subprocess.call(**full_args)

    if check and return_code != 0:
        if "/usr/bin/mock" in full_args["args"] and "--buildsrpm" in full_args["args"]:
            print(f"Error : mock command occasionally failed , {command}, return code {return_code}")
            sys.exit(1)
        raise subprocess.CalledProcessError(return_code, full_args["args"], None)

    return return_code


def list_all_file(command, file="Makefile"):
    res = os.popen(" ".join(command))
    output = res.read()
    if " " in output and file in output:
        return output.split()[0]
    elif file in output:
        return output.strip()
    return ""


def check_makefile_exist(path="", file_name="Makefile"):
    if not os.path.exists(path):
        return ''
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
