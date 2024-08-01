# SPDX-License-Identifier: MIT
# Copyright (c) 2017 Shintaro Kaneko

import os
import re
import hashlib


def do_regex(patterns, re_str):
    """Find first match in multiple patterns."""
    for p in patterns:
        match = re.search(p, re_str)
        if match:
            return match


def translate(package):
    """Convert terms to their alternate definition."""
    from src.utils import dictionary
    for item in dictionary:
        if item.startswith(package + "="):
            return item.split("=")[1]
    return package


def binary_in_path(binary):
    """Determine if the given binary exists in the provided filesystem paths."""
    from src.utils import os_paths
    if not os_paths:
        path_env = os.getenv("PATH", default="/usr/bin:/bin")
        if path_env:
            os_paths = path_env.split(os.pathsep)
    for path in os_paths:
        target_path = os.path.join(path, binary)
        if os.path.exists(target_path):
            return True
    return False


def open_auto(*args, **kwargs):
    """Open a file with UTF-8 encoding."""
    assert len(args) <= 3
    assert 'errors' not in kwargs
    assert 'encoding' not in kwargs
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
