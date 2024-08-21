# SPDX-License-Identifier: MIT
# Copyright (c) 2017 Shintaro Kaneko. All rights reserved.


import os
import re
from src.log import logger
from src.config.config import configuration
from src.utils.cmd_util import get_package_by_file, call
from src.utils.file_util import open_auto


def get_req_by_pat(s):
    file_path = s
    if s.startswith('-l'):
        file_path = '/usr/lib64/lib' + s[2:] + '.so'
    elif s.endswith('.h') or s.endswith('hpp') or s.endswith('hxx') or s.endswith('h++'):
        file_path = '/usr/include/' + s
    req = get_package_by_file(file_path)
    return req


def cleanup_req(s: str) -> str:
    """Strip unhelpful strings from requirements."""
    empty_tags = [
        "is wanted",
        "should be defined",
        "are broken",
        "is broken"
    ]
    for empty_tag in empty_tags:
        if empty_tag in s:
            return ""
    if s[0:4] == 'for ':
        s = s[4:]
    replace_texts = [
        " works as expected",
        " and usability",
        " usability",
        " argument",
        " environment variable",
        " environment var",
        " presence",
        " support",
        " implementation is broken",
        " is broken",
        " files can be found",
        " can be found",
        " is declared",
        "whether to build ",
        "whether ",
        "library containing ",
        "x86_64-generic-linux-gnu-",
        "i686-generic-linux-gnu-",
        "'",
    ]
    for replace_text in replace_texts:
        s = s.replace(replace_text, "")
    return s.strip()


class LogParser:
    def __init__(self, metadata: dict, scripts: dict, compilation=None):
        self.metadata = metadata
        self.scripts = scripts
        self.compilation = compilation
        self.name = metadata.get("name")
        self.version = metadata.get("version")
        self.release = metadata.get("release")
        self.patch_name_line = re.compile(r'^Patch #[0-9]+ \((.*)\):$')
        self.patch_fail_line = re.compile(r'^Skipping patch.$')
        self.failed_type = "other"
        self.parse_funcs = {
            "autotools": self.parse_make_pattern,
            "make": self.parse_make_pattern,
            "cmake": self.parse_make_pattern,  # 最终都会使用make命令构建的编译方式，所以用一个解析函数
            "python": self.parse_python_pattern,
            "ruby": self.parse_ruby_pattern,
            "nodejs": self.parse_nodejs_pattern,
        }
        self.searched_cmake_failed = False
        self.cmake_error_message = ""
        configuration.setup_patterns()

    def add_buildreq(self, req, req_type=""):
        """Add req to the global buildreqs set if req is not banned."""
        req = req.strip()
        # TODO(self.metadata中的buildRequires添加依赖，根据req_type(pkgconfig/python3dist/rubygem)添加不同类型的包)
        if req_type == "python":
            req = f"python3dist({req})"
        elif req_type == "rubygem":
            req = f"rubugem({req})"
        self.metadata.setdefault("buildRequires", set()).add(req)

    def add_requires(self, req, subpkg=None):
        """Add req to the requires set if it is present in buildreqs and packages and is not banned."""
        # TODO(self.metadata中的requires添加依赖，如果是子包就往子包中添加requires)
        self.metadata.setdefault("requires", set()).add(req)

    def add_provides(self, prov, subpkg=None):
        """Add prov to the provides set if it is not banned."""
        self.metadata.setdefault("requires", set()).add(prov)

    def simple_pattern_pkgconfig(self, line, pattern, req):
        """Check for pkgconfig patterns and restart build as needed."""
        pat = re.compile(pattern)
        match = pat.search(line)
        if match and "buildRequires" in self.metadata and isinstance(self.metadata["buildRequires"], set):
            self.metadata["buildRequires"].add(f"pkgconfig({req})")
        return False

    def simple_pattern(self, line, pattern, req):
        """Check for simple patterns and restart the build as needed."""
        pat = re.compile(pattern)
        match = pat.search(line)
        if match:
            self.add_buildreq(req)
            self.add_requires(req)
            return True
        return False

    def add_cmake_params(self, line):
        """add cmake params"""
        # TODO(self.scripts中添加)

    def remove_backport_patch(self, patch):
        remove = False
        num = None
        if "patchset" in self.metadata and isinstance(self.metadata["patchset"], dict):
            for num, patch_name in self.metadata["patchset"].items():
                if patch_name == patch:
                    remove = True
                    break
            if remove and num is not None:
                del self.metadata["patchset"][num]
            return True
        return False

    def parse_build_log(self, metadata=None):
        """Handle build log contents."""
        if metadata is not None:
            self.metadata = metadata
        patch_name = ""

        # Flush the build-log to disk, before reading it
        call("sync")
        build_log_path = configuration.download_path + "/build.log"
        with open_auto(build_log_path, "r") as f:
            log_lines = f.readlines()
        for line in log_lines:
            # TODO(检测语句，依赖没有找到时，输入name和编译类型，进入递归流程)
            # 检测语句，缺少补丁或者补丁应用失败时，修改补丁配置
            if patch_name_match := self.patch_name_line.search(line):
                patch_name = patch_name_match.groups()[0]
            if patch_name:
                if self.patch_fail_line.search(line):
                    self.remove_backport_patch(patch_name)
            # 检测语句，根据失败语句和编译类型，判断错误，需要是公共错误类型还是具体编译类型下的错误类型
            for pat, req in configuration.simple_pats:
                restart = self.simple_pattern(line, pat, req)
                if restart:
                    return self.metadata
            restart = self.parse_funcs[self.compilation](line)
            if restart:
                break
            if line == configuration.build_success_echo:
                break
        return self.metadata

    def add_extra_make_flags(self, line):
        """write the make flags"""
        # TODO(self.scripts中添加新增的编译选项)
        pass

    def parse_make_pattern(self, line):
        # 先判断是否是cmake构建的错误
        if re.search(configuration.cmake_search_failed, line) and self.compilation == "cmake":
            self.searched_cmake_failed = True
        if self.searched_cmake_failed:
            return self.parse_cmake_message(line)
        for pattern in configuration.make_failed_pats:
            pat = re.compile(pattern)
            match = pat.search(line)
            if match:
                req = configuration.failed_commands.get(match.group(1))
                if req is None:
                    return False
                self.add_buildreq(req)
                return True
        for pattern in configuration.make_failed_flags:
            pat = re.compile(pattern)
            match = pat.search(line)
            if match:
                self.metadata.setdefault("makeFlags", configuration.failed_flags[match.group(1)])
                return True
        return False

    def parse_cmake_message(self, line):
        self.cmake_error_message += line.strip(os.linesep)
        for pattern in configuration.cmake_failed_pats:
            pat = re.compile(pattern)
            match = pat.search(self.cmake_error_message)
            if match:
                req = configuration.cmake_modules.get(match.group(1))
                if req is None:
                    return False
                self.add_buildreq(req)
                return self.compilation == "cmake"
        for pattern in configuration.cmake_failed_flags:
            pat = re.compile(pattern)
            match = pat.search(self.cmake_error_message)
            if match:
                cmake_params = "-D" + match.group(1) + "=false"
                self.metadata.setdefault("cmakeFlags", cmake_params)
                return self.compilation == "cmake"

    def parse_python_pattern(self, line):
        for pattern, req in configuration.pypi_failed_pats:
            pat = re.compile(pattern)
            match = pat.search(line)
            if match:
                self.add_buildreq(req, req_type="python3dist")
                return True
        return False

    def parse_ruby_pattern(self, line):
        for pattern, req in configuration.ruby_failed_pats:
            pat = re.compile(pattern)
            match = pat.search(line)
            if match:
                self.add_buildreq(req, req_type="rubygem")
                return True
        return False

    def parse_nodejs_pattern(self, line):
        for pattern, req in configuration.nodejs_failed_pats:
            pat = re.compile(pattern)
            match = pat.search(line)
            if match:
                self.add_buildreq(req, req_type="npm")
                return True
        return False
