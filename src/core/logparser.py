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
    if "is wanted" in s:
        s = ""
    if "should be defined" in s:
        s = ""
    if "are broken" in s:
        s = ""
    if "is broken" in s:
        s = ""
    if s[0:4] == 'for ':
        s = s[4:]
    s = s.replace(" works as expected", "")
    s = s.replace(" and usability", "")
    s = s.replace(" usability", "")
    s = s.replace(" argument", "")
    s = s.replace(" environment variable", "")
    s = s.replace(" environment var", "")
    s = s.replace(" presence", "")
    s = s.replace(" support", "")
    s = s.replace(" implementation is broken", "")
    s = s.replace(" is broken", "")
    s = s.replace(" files can be found", "")
    s = s.replace(" can be found", "")
    s = s.replace(" is declared", "")
    s = s.replace("whether to build ", "")
    s = s.replace("whether ", "")
    s = s.replace("library containing ", "")
    s = s.replace("x86_64-generic-linux-gnu-", "")
    s = s.replace("i686-generic-linux-gnu-", "")
    s = s.replace("'", "")
    s = s.strip()
    return s


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

    def add_buildreq(self, req, req_type=""):
        """Add req to the global buildreqs set if req is not banned."""
        # TODO(self.metadata中的buildRequires添加依赖，根据req_type(pkgconfig/python3dist/rubygem)添加不同类型的包)
        pass

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
        if match and "requires" in self.metadata and isinstance(self.metadata["requires"], set):
            self.metadata["requires"].add(req)

    def failed_pattern(self, line, pattern, buildtool=None):
        """Check against failed patterns to restart build as needed."""
        # TODO(method better)
        pat = re.compile(pattern)
        match = pat.search(line)
        if not match:
            return
        s = match.group(1)
        # standard configure cleanups
        s = cleanup_req(s)

        if s in configuration.ignored_commands:
            return

        req = ''
        try:
            if not buildtool:
                req = get_req_by_pat(s) or configuration.failed_commands[s]
                if req:
                    self.add_buildreq(req)
                else:
                    print(f"Failed patterns to Build: {line}")
            elif buildtool in ['pkgconfig', "perl", "python3dist"]:
                self.add_buildreq(s, req_type=buildtool)
            elif buildtool == "flags":
                flags = configuration.failed_flags[s]
                if flags:
                    self.add_extra_make_flags(flags)
                else:
                    self.metadata["phase.make_params"] = ""
            elif buildtool == "cmake":
                self.failed_type = "cmake"
        except Exception as e:
            if s.strip() and s[:2] != '--':
                logger.info('req=' + req)
                logger.warning(f"Unknown pattern match: {s} {str(e)}")

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
        if self.compilation == "make":
            parse_log_function = self.parse_make_pattern
        elif self.compilation == "cmake":
            parse_log_function = self.parse_cmake_pattern
        elif self.compilation == "configure":
            parse_log_function = self.parse_configure_pattern
        else:
            parse_log_function = self.parse_other_pattern
        for line in log_lines:
            # TODO(检测语句，依赖没有找到时，输入name和编译类型，进入递归流程)
            # 检测语句，缺少补丁或者补丁应用失败时，修改补丁配置
            if patch_name_match := self.patch_name_line.search(line):
                patch_name = patch_name_match.groups()[0]
            if patch_name:
                if self.patch_fail_line.search(line):
                    self.remove_backport_patch(patch_name)
            # 检测语句，根据失败语句和编译类型，判断错误，需要是公共错误类型还是具体编译类型下的错误类型
            restart = parse_log_function(line)
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
        for pattern, req in configuration.make_failed_pats:
            pat = re.compile(pattern)
            match = pat.search(line)
            if match:
                self.add_buildreq(req)
                return True
        for pattern, flags in configuration.make_failed_flags:
            pat = re.compile(pattern)
            match = pat.search(line)
            if match:
                self.metadata.setdefault("makeFlags", flags)
                return True
        return False

    def parse_cmake_pattern(self, line):
        for pattern, req in configuration.cmake_failed_pats:
            pat = re.compile(pattern)
            match = pat.search(line)
            if match:
                self.add_buildreq(req)
                return True
        for pattern, flags in configuration.cmake_failed_flags:
            pat = re.compile(pattern)
            match = pat.search(line)
            if match:
                self.metadata.setdefault("cmakeFlags", flags)
                return True
        return False

    def parse_configure_pattern(self, line):
        for pattern, req in configuration.configure_failed_pats:
            pat = re.compile(pattern)
            match = pat.search(line)
            if match:
                self.add_buildreq(req)
                return True
        for pattern, flags in configuration.configure_failed_flags:
            pat = re.compile(pattern)
            match = pat.search(line)
            if match:
                self.metadata.setdefault("configureFlags", flags)
                return True
        return False

    def parse_other_pattern(self, line):
        return False
