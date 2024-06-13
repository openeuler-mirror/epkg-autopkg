import os
import re
from src.log import logger
from src.config.config import configuration
from src.utils.cmd_util import get_package_by_file, call
from src.utils.file_util import translate, open_auto


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
    def __init__(self, metadata: dict):
        self.restart = 0
        self.metadata = metadata
        self.name = metadata.get("name")
        self.version = metadata.get("version")
        self.release = metadata.get("release")
        self.buildreqs_cache = set()
        self.verbose = False
        self.pypi_provides = None
        self.setuid = []
        self.attrs = {}
        self.locales = []
        self.excludes = []
        self.files = {
            "files": set()
        }
        self.build_log_path = os.path.join(configuration.download_path, "results", "build.log")
        self.banned_requires = {
            None: {"futures", "configparser", "typing", "ipaddress"}
        }
        self.banned_provides = {None: set()}
        self.banned_buildreqs = {"llvm-devel", "gcj", "pkgconfig(dnl)", "pkgconfig(hal)", "tslib-0.0",
                                 "pkgconfig(parallels-sdk)", "oslo-python", "libxml2No-python", "futures",
                                 "configparser", "setuptools_scm[toml]", "typing", "ipaddress"}
        self.patch_name_line = re.compile(r'^Patch #[0-9]+ \((.*)\):$')
        self.patch_fail_line = re.compile(r'^Skipping patch.$')
        self.files_blacklist = set()
        self.failed_type = "other"
        self.want_dev_split = True

    def add_buildreq(self, req, cache=False):
        """Add req to the global buildreqs set if req is not banned."""
        new = True
        if not req:
            return False
        req.strip()
        if req in self.banned_buildreqs:
            return False
        if "buildRequires" in self.metadata and req in self.metadata["buildRequires"]:
            new = False
        if self.verbose and new:
            logger.info("  Adding buildreq:", req)
        self.metadata.setdefault("buildRequires", set()).add(req)
        if cache and new:
            self.buildreqs_cache.add(req)
        return new

    def ban_requires(self, ban, subpkg=None):
        """Add ban to the banned set (and remove it from requires if it was added)."""
        ban = ban.strip()
        if (requires := self.metadata["requires"].get(subpkg)) is None:
            requires = self.metadata[f"subpackages.{subpkg}"]["requires"] = set()
        if (banned_requires := self.banned_requires.get(subpkg)) is None:
            banned_requires = self.banned_requires[subpkg] = set()
        requires.discard(ban)
        banned_requires.add(ban)

    def add_requires(self, req, packages, override=False, subpkg=None):
        """Add req to the requires set if it is present in buildreqs and packages and is not banned."""
        new = True
        req = req.strip()
        if (requires := self.metadata.get("requires").get(subpkg)) is None:
            requires = self.metadata[f"subpackages.{subpkg}"][["requires"]] = set()
        if req in requires:
            new = False
        if (banned_requires := self.banned_requires.get(subpkg)) is None:
            banned_requires = self.banned_requires[subpkg] = set()
        if req in banned_requires:
            return False

        if req not in self.metadata.get("buildRequires") and req not in packages and not override:
            if req:
                print("requirement '{}' not found in buildreqs or os_packages, skipping".format(req))
            return False
        if new:
            # print("Adding requirement:", req)
            self.metadata.setdefault("requires", set()).add(req)
        return new

    def ban_provides(self, ban, subpkg=None):
        """Add ban to the banned set (and remove it from provides if it was added)."""
        ban = ban.strip()
        if (provides := self.metadata.get("provides").get(subpkg)) is None:
            provides = self.metadata[f"subpackages.{subpkg}"]["provides"] = set()
        if (banned_provides := self.banned_provides.get(subpkg)) is None:
            banned_provides = self.banned_provides[subpkg] = set()
        provides.discard(ban)
        banned_provides.add(ban)

    def add_provides(self, prov, subpkg=None):
        """Add prov to the provides set if it is not banned."""
        new = True
        prov = prov.strip()
        if (provides := self.metadata.get("provides").get(subpkg)) is None:
            provides = self.metadata[f"subpackages.{subpkg}"]["provides"] = set()
        if prov in provides:
            new = False
        if (banned_provides := self.banned_provides.get(subpkg)) is None:
            banned_provides = self.banned_provides[subpkg] = set()
        if prov in banned_provides:
            return False
        if new:
            provides.add(prov)
        return new

    def add_pkgconfig_buildreq(self, preq, cache=False):
        """Format preq as pkgconfig req and add to buildreqs."""
        req = "pkgconfig(" + preq + ")"
        return self.add_buildreq(req, cache)

    def simple_pattern_pkgconfig(self, line, pattern):
        """Check for pkgconfig patterns and restart build as needed."""
        pat = re.compile(pattern)
        match = pat.search(line)
        if match and "buildRequires" in self.metadata and isinstance(self.metadata["buildRequires"], set):
            self.restart += self.metadata["buildRequires"].add(f"pkgconfig({pattern})")
        return False

    def simple_pattern(self, line, pattern):
        """Check for simple patterns and restart the build as needed."""
        pat = re.compile(pattern)
        match = pat.search(line)
        if match and "requires" in self.metadata and isinstance(self.metadata["requires"], set):
            self.restart += self.metadata["requires"].add(pattern)

    def failed_pattern(self, line, pattern, buildtool=None):
        """Check against failed patterns to restart build as needed."""
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
                    self.restart += self.add_buildreq(req, cache=True)
                else:
                    print(f"Failed patterns to Build: {line}")
            elif buildtool == 'pkgconfig':
                self.restart += self.add_pkgconfig_buildreq(s, cache=True)
            elif buildtool == 'R':
                if self.add_buildreq("R-" + s, cache=True) > 0:
                    self.restart += 1
            elif buildtool == 'perl':
                s = s.replace('inc::', '')
                self.restart += self.add_buildreq('perl(%s)' % s, cache=True)
            elif buildtool == 'pypi':
                s = translate(s)
                if not s:
                    return
                self.restart += self.add_buildreq(f"pypi({s.lower().replace('-', '_')})", cache=True)
            elif buildtool == 'catkin':
                self.restart += self.add_pkgconfig_buildreq(s, cache=True)
                self.restart += self.add_buildreq(s, cache=True)
            elif buildtool == "flags":
                flags = configuration.failed_flags[s]
                if flags:
                    self.restart += self.add_extra_make_flags(flags)
                else:
                    self.metadata["phase.make_params"] = ""
            elif buildtool == "cmake":
                self.failed_type = "cmake"
            # elif buildtool == 'java-plugin':
            #     self.failed_pattern_update_by_java_plugin(s, line)
            # elif buildtool == 'java-plugins':
            #     self.failed_pattern_update_by_java_plugins(line)
            # elif buildtool == 'java-jar':
            #     self.failed_pattern_update_by_java_jar(s, line)
        except Exception as e:
            if s.strip() and s[:2] != '--':
                logger.info('req=' + req)
                logger.warning(f"Unknown pattern match: {s} {str(e)}")

    def cmake_pattern(self, line):
        for pattern in configuration.cmake_params:
            if re.search(pattern, line):
                self.restart += self.add_cmake_params(line)
                break

    def add_cmake_params(self, line):
        """add cmake params"""
        if "phase.cmake" not in self.metadata:
            return False
        for pattern in configuration.cmake_params:
            ret = re.findall(pattern, line)
            if ret:
                target = "-D" + ret[0] + "=false"
                if "phase.cmake_params" in self.metadata:
                    self.metadata["phase.cmake_params"] = " " + target
                else:
                    self.metadata["phase.cmake_params"] = " " + target
                return True
        logger.info("cannot find useful cmake params")
        return False

    def parse_buildroot_log(self, filename, return_code):
        """Handle buildroot log contents."""
        if return_code == 0:
            return True
        self.restart = 0
        is_clean = True
        call("sync")
        with open_auto(filename, "r") as f:
            log_lines = f.readlines()
        missing_pat = re.compile(r"^.*No matching package to install: '(.*)'$")
        for line in log_lines:
            match = missing_pat.match(line)
            if match is not None:
                logger.error("Cannot resolve dependency name: {}".format(match.group(1)))
                is_clean = False
        return is_clean

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

    def parse_package_info(self, compilation, metadata=None):
        """Handle build log contents."""
        self.metadata = metadata
        infiles = 0
        flag = True
        patch_name = ""
        cmake_error_message = ""

        # Flush the build-log to disk, before reading it
        call("sync")
        with open_auto(self.build_log_path, "r") as f:
            log_lines = f.readlines()
        for line in log_lines:
            if patch_name_match := self.patch_name_line.search(line):
                patch_name = patch_name_match.groups()[0]
            if patch_name:
                if self.patch_fail_line.search(line):
                    self.restart += self.remove_backport_patch(patch_name)
            for pat in configuration.pkgconfig_pats:
                self.simple_pattern_pkgconfig(line, *pat)

            for pat in configuration.simple_pats:
                self.simple_pattern(line, *pat)

            for pat in configuration.failed_pats:
                self.failed_pattern(line, compilation, *pat)

            if self.failed_type == "cmake":
                cmake_error_message += line.strip(os.linesep)
                self.cmake_pattern(cmake_error_message)

            if infiles == 1:
                for search in ["RPM build errors", "Childreturncodewas",
                               "Child returncode", "Empty %files file"]:
                    if search in line:
                        infiles = 2
                        self.divide_files()
                        if search in ["RPM build errors", "Empty %files file"]:
                            print(f"Search files to add: {line}")
                for start in ["Building", "Child return code was"]:
                    if line.startswith(start):
                        infiles = 2
                        self.divide_files()

            if infiles == 0 and "Installed (but unpackaged) file(s) found:" in line:
                infiles = 1
                self.restart += 1
            elif infiles == 1 and "not matching the package arch" not in line:
                # exclude blank lines from consideration...
                file = line.strip()
                if file and file[0] == "/":
                    self.push_file(file)

            if line.startswith("Sorry: TabError: inconsistent use of tabs and spaces in indentation"):
                logger.info(line)

            match_bad = r"Bad exit status from (.*)"
            if re.findall(match_bad, line):
                logger.info(line)

            match_cmd = r"(.*) command not found"
            if re.findall(match_cmd, line):
                logger.info(line)

            if line.startswith("EXCEPTION: [Error()]"):
                if log_lines[log_lines.index(line) + 1].startswith("Traceback"):
                    logger.info("Mock command exception.")

            nvr = f"{self.name}-{self.version}-{self.release}"
            match = f"File not found: /builddir/build/BUILDROOT/{nvr}.x86_64/"
            if match in line:
                missing_file = "/" + line.split(match)[1].strip()
                self.remove_file(missing_file)
            if line.startswith("Executing(%clean"):
                logger.info("RPM build successful")
                self.restart = 0
                flag = False

        if flag:
            logger.info(f"There is no line startinf with 'Executing(%clean' in the build log,and returncode={returncode}")
        self.metadata.update(self.files)
        return metadata

    def update_metadata(self):
        for sub_name, sub_files in self.files.items():
            # 将集合类型转换为数组类型
            if sub_name == "files":
                self.metadata.setdefault("files", os.linesep.join(list(sub_files)))
                continue
            # 如果子包files存在但没有子包定义的，加上子包定义（summary/description）
            if f"subpackage.{sub_name}" not in self.metadata:
                self.metadata.setdefault(f"subpackage.{sub_name}", {}).setdefault(
                    "meta", {"summary": "%{summary}.", "description": "%description"})
            if f"subpackage.{sub_name}.files" not in self.metadata:
                self.metadata.setdefault(f"subpackage.{sub_name}.files",
                                         os.linesep.join(list(sub_files)))
        return self.metadata

    def add_extra_make_flags(self, line):
        """write the make flags"""
        if "phase.make_params" in self.metadata:
            self.metadata["phase.make_params"] += " " + f"CFLAGS=\"$CFLAGS {line}\" CXXFLAGS=\"$CXXFLAGS {line}\""
        else:
            self.metadata["phase.make_params"] = " " + f"CFLAGS=\"$CFLAGS {line}\" CXXFLAGS=\"$CXXFLAGS {line}\""
        self.failed_type = "make"
        return True

    def remove_file(self, filename):
        """Remove filename from local file list."""
        hit = False
        files_dict = self.files.copy()
        for subpackage, values in files_dict.items():
            if filename in values:
                self.files[subpackage].remove(filename)
                logger.info("File no longer present: {}".format(filename))
                hit = True
        if hit:
            self.files_blacklist.add(filename)
            self.restart += 1

    def push_file(self, filename):
        """Perform a number of checks against the filename and push the filename if appropriate."""
        if filename in self.files_blacklist:
            return
        for sub_name, sub_files in self.files.items():
            if filename in sub_files:
                return

        self.files["files"].add(filename)
        if self.file_is_locale(filename):
            return

        # Explicit file packaging
        for k, v in self.files.items():
            for match_name in v:
                match = re.search(r"^/(V3|V4)", filename)
                norm_filename = filename if not match else filename.removeprefix(match.group())
                if isinstance(match_name, str):
                    if norm_filename == match_name:
                        self.push_package_file(filename, k)
                        return
                elif len('/'.join(match_name)) <= (len(norm_filename) + 1):
                    # the match name may be 1 longer due to a glob
                    # being able to match an empty string
                    if self.globlike_match(norm_filename, match_name):
                        path_prefix = '/' if not match else match.group()
                        self.push_package_file(os.path.join(path_prefix, *match_name), k)
                        return

        if filename in self.setuid:
            if filename in self.attrs:
                mod = self.attrs[filename][0]
                u = self.attrs[filename][1]
                g = self.attrs[filename][2]
                newfn = "%attr({0},{1},{2}) {3}".format(mod, u, g, filename)
            else:
                newfn = "%attr(4755, root, root) " + filename
            self.push_package_file(newfn, "setuid")
            return

        # autostart
        part = re.compile(r"^/usr/lib/systemd/system/.+\.target\.wants/.+")
        if part.search(filename) and 'update-triggers.target.wants' not in filename:
            if filename not in self.excludes:
                self.push_package_file(filename, "autostart")
                self.push_package_file("%exclude " + filename, "services")
                return

        if self.want_dev_split and self.file_pat_match(filename, r"^/usr/.*/include/.*\.h$", "dev"):
            return

        # if configured to do so, add .so files to the lib package instead of
        # the dev package. THis is useful for packages with a plugin
        # architecture like elfutils and mesa.
        so_dest = so_dest_ompi = 'dev'

        for pat_args in configuration.patterns:
            if self.file_pat_match(filename, *pat_args):
                return

        if filename in self.excludes:
            return

        self.push_package_file(filename)

    def push_package_file(self, filename, package=""):
        """Add found %file and indicate to build module that we must restart the build."""
        if package not in self.files:
            self.files[package] = set()

        # if FileManager.banned_path(filename):
        #     util.print_warning(f"  Content {filename} found in banned path, skipping")
        #     self.has_banned = True
        #     return

        # prepend the %attr macro if file defined in 'attrs' control file
        if filename in self.attrs:
            mod = self.attrs[filename][0]
            u = self.attrs[filename][1]
            g = self.attrs[filename][2]
            filename = "%attr({0},{1},{2}) {3}".format(mod, u, g, filename)
        self.files[package].add(filename)
        print("  New %files content found: " + filename)

    def file_is_locale(self, filename):
        """If a file is a locale, appends to self.locales and returns True, returns False otherwise."""
        pat = re.compile(r"^/usr/share/locale/.*/(.*)\.mo")
        match = pat.search(filename)
        if match:
            lang = match.group(1)
            if lang not in self.locales:
                self.locales.append(lang)
                print("  New locale:", lang)
                self.restart += 1
                if "locales" not in self.files:
                    self.files["locales"] = set()
            return True
        else:
            return False

    def globlike_match(self, filename, match_name):
        """Compare the filename to the match_name in a way that simulates the shell glob '*'."""
        fsplit = filename.split('/')
        if len(fsplit) != len(match_name):
            return False
        match = True
        for fpart, mpart in zip(fsplit, match_name):
            if fpart != mpart:
                if '*' not in mpart:
                    match = False
                    break
                if len(mpart) > len(fpart) + 1:
                    match = False
                    break
                mpl, mpr = mpart.split('*')
                try:
                    if fpart.index(mpl) != 0:
                        match = False
                        break
                    if fpart.rindex(mpr) != len(fpart) - len(mpr):
                        match = False
                        break
                except ValueError:
                    match = False
                    break
        return match

    def file_pat_match(self, filename, pattern, package, replacement=""):
        """Search for pattern in filename.

        Attempt to find pattern in filename, if pattern matches push package file.
        If that file is also in the excludes list, don't push the file.
        Returns True if a file was pushed, False otherwise.
        """
        if not replacement:
            replacement = filename

        # compat files should always be excluded
        if self.compat_exclude(filename):
            self.excludes.append(filename)
            return True

        # All patterns at this time and should always be prefixed by '^'
        # but just in case add the following to strip just the '^'
        pattern = pattern if not pattern.startswith('^') else pattern[1:]
        pat = re.compile(r"^(/V3|/V4)?" + pattern)
        match = pat.search(filename)
        if match:
            if len(match.groups()) > 0 and match.groups()[0] in ['/V3', '/V4']:
                norm_filename = filename.removeprefix(match.groups()[0])
                if replacement != filename:
                    replacement = match.groups()[0] + replacement
            else:
                norm_filename = filename
            if norm_filename in self.excludes:
                return True

            self.push_package_file(replacement, package)
            return True

        return False

    def compat_exclude(self, filename):
        """Exclude non-library files if the package is for compatability."""
        patterns = [
            r"/usr/lib/[a-zA-Z0-9\.\_\-\+]*\.so\.",
            r"/usr/lib64/[a-zA-Z0-9\.\_\-\+]*\.so\.",
            r"/usr/lib32/[a-zA-Z0-9\.\_\-\+]*\.so\.",
            r"/usr/lib64/lib(asm|dw|elf)-[0-9.]+\.so",
            r"/usr/lib32/lib(asm|dw|elf)-[0-9.]+\.so",
            r"/usr/lib64/haswell/[a-zA-Z0-9\.\_\-\+]*\.so\.",
            r"/usr/share/package-licenses/"]

        exclude = True
        for pat in patterns:
            pat = re.compile(r"^(/V3|/V4)?" + pat)
            if pat.search(filename):
                exclude = False
                break

        return exclude

    def divide_files(self):
        pass
