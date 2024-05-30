import os
import sys
import re
import shutil
import subprocess
from src.utils.cmd_util import call
from src.utils.file_util import translate, open_auto, write_out
from src.log import logger
from src.transfer.writer import SpecWriter
from src.config.config import BuildConfig
from src.config import config_path


def get_mock_cmd():
    """Set mock command to use sudo as needed."""
    # Some distributions (e.g. Fedora) use consolehelper to run mock,
    # while others (e.g. Clear Linux) expect the user run it via sudo.
    if os.path.basename(os.path.realpath('/usr/bin/mock')) == 'consolehelper':
        return '/usr/bin/mock'
    return 'sudo /usr/bin/mock'


def get_mock_opts():
    return ""


def save_mock_logs(path, iteration):
    """Save Mock build logs to <path>/results/round<iteration>-*.log."""
    basedir = os.path.join(path, "results")
    loglist = ["build", "root", "srpm-build", "srpm-root", "mock_srpm", "mock_build"]
    for log in loglist:
        src = "{}/{}.log".format(basedir, log)
        dest = "{}/round{}-{}.log".format(basedir, iteration, log)
        os.rename(src, dest)


class Build(object):
    """Manage package builds."""

    def __init__(self):
        """Initialize default build settings."""
        self.success = 0
        self.round = 0
        self.must_restart = 0
        self.file_restart = 0
        self.uniqueext = ''
        self.warned_about = set()
        self.cmake_failed = False
        self.patch_name_line = re.compile(r'^Patch #[0-9]+ \((.*)\):$')
        self.patch_fail_line = re.compile(r'^Skipping patch.$')
        self.language_round = 1
        self.build_log_path = ""
        self.mock_config_path = os.path.join(config_path, "clear.cfg")

    def simple_pattern_pkgconfig(self, line, pattern, pkgconfig, conf32, requirements):
        """Check for pkgconfig patterns and restart build as needed."""
        pat = re.compile(pattern)
        match = pat.search(line)
        if match:
            self.must_restart += requirements.add_pkgconfig_buildreq(pkgconfig, conf32, cache=True)

    def simple_pattern(self, line, pattern, req, requirements):
        """Check for simple patterns and restart the build as needed."""
        pat = re.compile(pattern)
        match = pat.search(line)
        if match:
            self.must_restart += requirements.add_buildreq(req, cache=True)

    def get_package_by_file(self, file_name):
        pkg = ''
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

    def get_req_by_pat(self, s):
        file_path = s
        if s.startswith('-l'):
            file_path = '/usr/lib64/lib' + s[2:] + '.so'
        elif s.endswith('.h') or s.endswith('hpp') or s.endswith('hxx') or s.endswith('h++'):
            file_path = '/usr/include/' + s
        req = self.get_package_by_file(file_path)
        return req

    def failed_pattern(self, line, config, requirements, content, pattern, verbose, buildtool=None):
        """Check against failed patterns to restart build as needed."""
        pat = re.compile(pattern)
        match = pat.search(line)
        if not match:
            return
        s = match.group(1)
        # standard configure cleanups
        s = cleanup_req(s)

        if s in config.ignored_commands:
            return

        req = ''
        try:
            if not buildtool:
                req = self.get_req_by_pat(s) or config.failed_commands[s]
                if req:
                    self.must_restart += requirements.add_buildreq(req, cache=True)
                else:
                    print(f"Failed patterns to Build: {line}")
            elif buildtool == 'pkgconfig':
                self.must_restart += requirements.add_pkgconfig_buildreq(s, config.config_opts.get('32bit'), cache=True)
            elif buildtool == 'R':
                if requirements.add_buildreq("R-" + s, cache=True) > 0:
                    self.must_restart += 1
            elif buildtool == 'perl':
                s = s.replace('inc::', '')
                self.must_restart += requirements.add_buildreq('perl(%s)' % s, cache=True)
            elif buildtool == 'pypi':
                s = translate(s)
                if not s:
                    return
                self.must_restart += requirements.add_buildreq(f"pypi({s.lower().replace('-', '_')})", cache=True)
            elif buildtool == 'catkin':
                self.must_restart += requirements.add_pkgconfig_buildreq(s, config.config_opts.get('32bit'), cache=True)
                self.must_restart += requirements.add_buildreq(s, cache=True)
            elif buildtool == "flags":
                flags = config.failed_flags[s]
                if flags:
                    self.must_restart += config.add_extra_make_flags(flags)
                else:
                    config.extra_make = ""
            elif buildtool == "cmake":
                self.cmake_failed = True
            elif buildtool == 'java-plugin':
                self.failed_pattern_update_by_java_plugin(s, requirements, line, content)
            elif buildtool == 'java-plugins':
                self.failed_pattern_update_by_java_plugins(requirements, line)
            elif buildtool == 'java-jar':
                self.failed_pattern_update_by_java_jar(s, requirements, line, content)
        except Exception:
            if s.strip() and s not in self.warned_about and s[:2] != '--':
                logger.info('req=' + req)
                logger.warning(f"Unknown pattern match: {s}")
                self.warned_about.add(s)

    def cmake_pattern(self, line, config):
        for pattern in config.cmake_params:
            if re.search(pattern, line):
                self.cmake_failed = False
                self.must_restart += config.add_cmake_params(line)
                break

    def parse_buildroot_log(self, filename, returncode):
        """Handle buildroot log contents."""
        if returncode == 0:
            return True
        self.must_restart = 0
        self.file_restart = 0
        is_clean = True
        call("sync")
        with open_auto(filename, "r") as rootlog:
            loglines = rootlog.readlines()
        missing_pat = re.compile(r"^.*No matching package to install: '(.*)'$")
        for line in loglines:
            match = missing_pat.match(line)
            if match is not None:
                logger.error("Cannot resolve dependency name: {}".format(match.group(1)))
                is_clean = False
        return is_clean

    def parse_package_info(self, compilation, metadata):
        """Handle build log contents."""
        self.must_restart = 0
        self.file_restart = 0
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
                    self.must_restart += BuildConfig.remove_backport_patch(patch_name)
            for pat in BuildConfig.pkgconfig_pats:
                self.simple_pattern_pkgconfig(line, *pat, config.config_opts.get('32bit'), requirements)

            for pat in BuildConfig.simple_pats:
                self.simple_pattern(line, *pat, requirements)

            for pat in BuildConfig.failed_pats:
                self.failed_pattern(line, config, requirements, content, *pat)

            if self.cmake_failed:
                cmake_error_message += line.strip(os.linesep)
                self.cmake_pattern(cmake_error_message, config)

            if infiles == 1:
                for search in ["RPM build errors", "Childreturncodewas",
                               "Child returncode", "Empty %files file"]:
                    if search in line:
                        infiles = 2
                        if search in ["RPM build errors", "Empty %files file"]:
                            print(f"Search files to add: {line}")
                for start in ["Building", "Child return code was"]:
                    if line.startswith(start):
                        infiles = 2

            if infiles == 0 and "Installed (but unpackaged) file(s) found:" in line:
                infiles = 1
            elif infiles == 1 and "not matching the package arch" not in line:
                # exclude blank lines from consideration...
                file = line.strip()
                if file and file[0] == "/":
                    filemanager.push_file(file, content.name)

            if line.startswith("Sorry: TabError: inconsistent use of tabs and spaces in indentation"):
                print(line)
                returncode = 99

            match_bad = r"Bad exit status from (.*)"
            if re.findall(match_bad, line):
                print(line)

            match_cmd = r"(.*) command not found"
            if re.findall(match_cmd, line):
                print(line)

            if line.startswith("EXCEPTION: [Error()]"):
                if loglines[loglines.index(line ) +1].startswith("Traceback"):
                    print("Mock command exception.")

            nvr = f"{content.name}-{content.version}-{content.release}"
            match = f"File not found: /builddir/build/BUILDROOT/{nvr}.x86_64/"
            if match in line:
                missing_file = "/" + line.split(match)[1].strip()
                filemanager.remove_file(missing_file)
            if line.startswith("Executing(%clean") and returncode == 0:
                print("RPM build successful")
                self.success = 1
                flag = False

        if flag:
            logger.info(f"There is no line startinf with 'Executing(%clean' in the build log,and returncode={returncode}")
        return metadata

    def package(self, params, cleanup=False):
        """Run main package build routine."""
        self.round += 1
        self.success = 0
        mock_cmd = get_mock_cmd()
        mock_opts = get_mock_opts()
        self.mock_config_path = os.path.join(config_path, "clear.cfg")
        logger.info("Building package " + params.name + " round", self.round)

        self.uniqueext = params.name

        if cleanup:
            cleanup_flag = "--cleanup-after"
        else:
            cleanup_flag = "--no-cleanup-after"

        print("{} mock chroot at /var/lib/mock/clear-{}".format(params.name, self.uniqueext))

        if self.round == 1:
            os.chdir(BuildConfig.download_path)
            results_dirs_to_delete = [d for d in os.listdir() if re.match(r'^results.*', d) and os.path.isdir(d)]
            for d in results_dirs_to_delete:
                shutil.rmtree(d, ignore_errors=True)
            os.makedirs('{}/results'.format(BuildConfig.download_path))

        cmd_args = [
            mock_cmd,
            f"--root={self.mock_config_path}",
            "--buildsrpm",
            "--sources=./",
            f"--spec={params.name}.spec",
            f"--uniqueext={self.uniqueext}-src",
            "--result=results/",
            cleanup_flag,
            mock_opts,
        ]

        fulleuler_rootfs ='/mnt/merged'
        if os.path.exists(fulleuler_rootfs):
            fulleuler_rootfs_opt = ['--no-clean', f'--rootdir={fulleuler_rootfs}']
            cmd_args.extend(fulleuler_rootfs_opt)
        call(" ".join(cmd_args),
             logfile=f"{BuildConfig.download_path}/results/mock_srpm.log",
             cwd=BuildConfig.download_path)

        # back up srpm mock logs
        call("mv results/root.log results/srpm-root.log", cwd=BuildConfig.download_path)
        call("mv results/build.log results/srpm-build.log", cwd=BuildConfig.download_path)

        # copy dns config
        cmd_args = [
            mock_cmd,
            f"--root={self.mock_config_path}",
            "--copyin",
            "/etc/resolv.conf",
            "/etc",
            f"--uniqueext={self.uniqueext}",
            "--no-cleanup-after",
            mock_opts,
        ]

        if os.path.exists(fulleuler_rootfs):
            fulleuler_rootfs_opt = ['--no-clean', f'--rootdir={fulleuler_rootfs}']
            cmd_args.extend(fulleuler_rootfs_opt)

        ret = call(" ".join(cmd_args),
                   logfile=f"{BuildConfig.download_path}/results/mock_build.log",
                   check=False,
                   cwd=BuildConfig.download_path)

        # python import requires
        if params.compilation in ["pyproject"]:
            add_python_requires_cmd = "\"python3 -m pip install --upgrade build wheel\""

            cmd_args = [
                mock_cmd,
                f"--root={self.mock_config_path}",
                "shell exec",
                add_python_requires_cmd,
                f"--uniqueext={self.uniqueext}",
                "--no-cleanup-after",
                mock_opts,
            ]

            if os.path.exists(fulleuler_rootfs):
                fulleuler_rootfs_opt = ['--no-clean' ,f'--rootdir={fulleuler_rootfs}']
                cmd_args.extend(fulleuler_rootfs_opt)
            ret = call(" ".join(cmd_args),
                       logfile=f"{BuildConfig.download_path}/results/mock_build.log",
                       check=False,
                       cwd=BuildConfig.download_path)

        file_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        macros_file_path = os.path.join(file_dir, 'tools', '.rpmmacros')

        srcrpm = f"results/{params.name}-{params.version}-{params.release}.src.rpm"

        cmd_args = [
            mock_cmd,
            f"--root={self.mock_config_path}",
            "--result=results/",
            srcrpm,
            f"--macro-file={macros_file_path}",
            "--enable-plugin=ccache",
            f"--uniqueext={self.uniqueext}",
            cleanup_flag,
            mock_opts,
        ]

        if os.path.exists(fulleuler_rootfs):
            fulleuler_rootfs_opt = [f'--rootdir={fulleuler_rootfs}']
            cmd_args.extend(fulleuler_rootfs_opt)
        # if not cleanup and self.must_restart == 0 and self.file_restart > 0 and set(filemanager.excludes) == set(filemanager.manual_excludes):
        cmd_args.append("--no-clean")
        # cmd_args.append("--short-circuit=binary")

        ret = call(" ".join(cmd_args),
                   logfile=f"{BuildConfig.download_path}/results/mock_build.log",
                   check=False,
                   cwd=BuildConfig.download_path)

        # sanity check the build log
        self.build_log_path = BuildConfig.download_path + "/results/build.log"
        if not os.path.exists(self.build_log_path):
            logger.error("Mock command failed, results log does not exist. User may not have correct permissions.")
            exit(1)

        if not self.parse_buildroot_log(BuildConfig.download_path + "/results/root.log", ret):
            return

    def failed_pattern_update_by_java_plugin(self, pluginFullName, requirements, line, content):
        pluginName = pluginFullName.split(":")[1]
        if "org.apache.maven.plugins" in pluginFullName:
            self.must_restart += requirements.add_java_remove_plugins(pluginName, cache=True)
        else:
            if self.test_req_by_yum(pluginFullName):
                self.must_restart += requirements.add_buildreq("mvn({})".format(pluginFullName), cache=True)
            else:
                self.add_pom_disable_module(line, requirements, content)

    def test_req_by_yum(self, pluginFullName):
        download_result = self.get_output("yum download \"mvn({})\"".format(pluginFullName))
        return "rpm" in download_result

    def add_pom_disable_module(self, line, requirements, content):
        pattern = "and the artifact ([a-zA-Z.\-:]+):jar:([0-9.]+) has not been downloaded from it before"
        pat = re.compile(pattern)
        match = pat.search(line)
        if not match:
            return
        jarFullName = match.group(1)
        jarName = jarFullName.split(":")[1]
        mock_os_root = self.get_output \
            ("grep \"config_opts\['root'\]\" {} | awk -F \"'\"".format(self.mock_config_path) + " \'{print $4}\'")
        module_with_artifactId = self.get_output \
            ("grep artifactId `grep -rl \"{}\" /var/lib/mock/{}-{}/root/builddir/build/BUILD/{}*/*` | head -1".format
                (jarName, mock_os_root, content.name, content.name))

        pattern = "<artifactId>([a-z0-9.]+)</artifactId>"
        pat = re.compile(pattern)
        match = pat.search(module_with_artifactId)
        moduleName = match.group(1)
        self.must_restart += requirements.add_java_disable_modules(moduleName)

    def get_output(self, cmdstr):
        result = subprocess.run(cmdstr, shell=True, stdout=subprocess.PIPE)
        output = result.stdout.decode('utf-8').strip()
        return output

    def failed_pattern_update_by_java_jar(self, moduleFullName, requirements, line, content):
        moduleName = moduleFullName.split(":")[1]
        pattern = "and the artifact ([a-zA-Z.\-:]+):jar:([0-9.]+) has not been downloaded from it before"
        pat = re.compile(pattern)
        match = pat.search(line)
        if not match:
            return
        jarFullName = match.group(1)
        self.must_restart += requirements.add_java_remove_deps("{} {}/pom.xml".format(jarFullName, moduleName))

    def failed_pattern_update_by_java_plugins(self, requirements, line):
        artifacts = line.split(": ")[2].split(", ")
        for pluginFullName in artifacts:
            pluginName = pluginFullName.split(":")[1]
            self.must_restart += requirements.add_java_remove_plugins(pluginName, cache=True)

    def mock_clean(self, cwd):
        cmd_args = [
            get_mock_cmd(),
            f"--root={config_path}/clear.cfg",
            f"--uniqueext={self.uniqueext}",
            "clean",
        ]
        call(" ".join(cmd_args), None, cwd=cwd)


def run(source, target):
    package = Build()
    writer = SpecWriter(source.name, source.path)
    # TODO(编译类型扫描，多语言循环)
    for compile_type in source.compilations:
        while 1:
            metadata = package.parse_package_info(compile_type, target)
            writer.trans_data_to_spec(metadata)
            package.package(source)
            mock_chroot = "/var/lib/mock/openEuler-LTS-x86_64-1-{}/root/builddir/build/BUILDROOT/" \
                          "{}-{}-{}.x86_64".format(package.uniqueext,
                                                   source.name,
                                                   source.version,
                                                   source.release)
            if source.clean_directories(mock_chroot):
                # directories added to the blacklist, need to re-run
                package.must_restart += 1

            if package.round > 20 or (package.must_restart == 0 and package.file_restart == 0):
                break

            save_mock_logs(BuildConfig.download_path, package.round)
        if package.success == 0:
            logger.error("Build failed, aborting")
            sys.exit(1)
        elif os.path.isfile("README.clear"):
            print("\nREADME.clear CONTENTS")
            print("*********************")
            with open("README.clear", "r") as readme_f:
                print(readme_f.read())

            print("*********************\n")

        #check.check_regression(conf.download_path, conf.config_opts['skip_tests'], package.round - 1)

        # examine_abi(conf.download_path, content.name)
        if os.path.exists("/var/lib/rpm"):
            get_whatrequires(source.name, source.yum_conf)

        write_out(BuildConfig.download_path + "/release", source.release + "\n")

        # record logcheck output
        log_check(BuildConfig.download_path)


def log_check(pkg_loc):
    """Try to discover configuration options that were automatically switched off."""
    build_log_path = os.path.join(pkg_loc, 'results', 'build.log')
    if not os.path.exists(build_log_path):
        print('build log is missing, unable to perform logcheck.')
        return

    whitelist = []
    file_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(file_dir, 'configure_whitelist')
    with open(file_path, "r") as f:
        for line in f:
            if line.startswith("#"):
                continue
            whitelist.append(line.rstrip())

    blacklist = []
    file_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(file_dir, 'configure_blacklist')
    with open(file_path, "r") as f:
        for line in f:
            if line.startswith("#"):
                continue
            blacklist.append(line.rstrip())

    with open(build_log_path, 'r') as f:
        lines = f.readlines()

    pat = re.compile(r"^checking (?:for )?(.*?)\.\.\. no")
    misses = []
    for line in lines:
        match = None
        m = pat.search(line)
        if m:
            match = m.group(1)

        if "none required" in line:
            match = None

        if "warning: format not a string literal" in line:
            match = line

        if not match or match in whitelist:
            continue

        if match in blacklist:
            logger.error("Blacklisted configure-miss is forbidden: " + match)
            misses.append("Blacklisted configure-miss is forbidden: " + match)
            write_misses(pkg_loc, misses)
            exit(1)

        print("Configure miss: " + match)
        misses.append("Configure miss: " + match)

    if not misses:
        return

    write_misses(pkg_loc, misses)


def write_misses(pkg_loc, misses):
    """Create configure_misses file with automatically disabled configuration options."""
    write_out(os.path.join(pkg_loc, 'configure_misses'), '\n'.join(sorted(misses)))


def get_whatrequires(pkg, yum_conf):
    """
    Write list of packages.

    Write packages that require the current package to a file
    using dnf repoquery what-requires and --recursive commands.
    """
    # clean up dnf cache to avoid 'no more mirrors repo' error
    try:
        subprocess.check_output(['dnf', '--config', yum_conf,
                                 '--releasever', 'clear', 'clean', 'all'])
    except subprocess.CalledProcessError as err:
        logger.error("Unable to clean dnf repo: {}, {}".format(pkg, err))
        return

    try:
        out = subprocess.check_output(['dnf', 'repoquery',
                                       '--config', yum_conf,
                                       '--releasever', 'clear',
                                       '--archlist=src', '--recursive', '--queryformat=%{NAME}',
                                       '--whatrequires', pkg]).decode('utf-8')

    except subprocess.CalledProcessError as err:
        logger.warning("dnf repoquery whatrequires for {} failed with: {}".format(pkg, err))
        return

    write_out('whatrequires', '# This file contains recursive sources that require this package\n' + out)


def mock_init(tarball):
    os.chdir(BuildConfig.download_path)
    # init tar file
    if ".tar" in tarball or ".zip" in tarball:
        cmd = f"cp -y {tarball} ."
    elif os.path.isdir(tarball):
        cmd = f"tar -xzvf {os.path.basename(tarball)}.tar.gz {tarball}/"
    else:
        logger.error("unsupported source file type")
        return
    call(cmd)
