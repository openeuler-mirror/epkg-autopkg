# SPDX-License-Identifier: MulanPSL-2.0+
# Copyright (c) 2022 Huawei Technologies Co., Ltd. All rights reserved.s

import os
import re
import hashlib

from src.config import config_path

dictionary_filename = config_path + "/translate.dic"
dictionary = [line.strip() for line in open(dictionary_filename, 'r')]
os_paths = None


def _file_write(self, s):
    s = s.strip()
    if not s.endswith("\n"):
        s += "\n"
    self.write(s)


def translate(package):
    """Convert terms to their alternate definition."""
    global dictionary
    for item in dictionary:
        if item.startswith(package + "="):
            return item.split("=")[1]
    return package


def do_regex(patterns, re_str):
    """Find a match in multiple patterns."""
    for p in patterns:
        match = re.search(p, re_str)
        if match:
            return match


def binary_in_path(binary):
    """Determine if the given binary exists in the provided filesystem paths."""
    global os_paths
    if not os_paths:
        os_paths = os.getenv("PATH", default="/usr/bin:/bin").split(os.pathsep)

    for path in os_paths:
        if os.path.exists(os.path.join(path, binary)):
            return True
    return False


def open_auto(*args, **kwargs):
    """Open a file with UTF-8 encoding.

    Open file with UTF-8 encoding and "surrogate" escape characters that are
    not valid UTF-8 to avoid data corruption.
    """
    # 'encoding' and 'errors' are fourth and fifth positional arguments, so
    # restrict the args tuple to (file, mode, buffering) at most
    assert len(args) <= 3
    assert 'encoding' not in kwargs
    assert 'errors' not in kwargs
    return open(*args, encoding="utf-8", errors="surrogateescape", **kwargs)


def get_contents(filename):
    """Get contents of filename."""
    with open(filename, "rb") as f:
        return f.read()


def write_out(filename, content, mode="w"):
    """File.write convenience wrapper."""
    with open_auto(filename, mode) as require_f:
        require_f.write(content)


def get_sha1sum(filename):
    """Get sha1 sum of filename."""
    sh = hashlib.sha1()
    sh.update(get_contents(filename))
    return sh.hexdigest()
