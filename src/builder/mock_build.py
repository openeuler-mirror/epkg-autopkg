import os
import sys
import re
import shutil
import subprocess
from src.utils.cmd_util import call
from src.utils.file_util import translate, open_auto, write_out
from src.log import logger
from src.transfer.writer import SpecWriter
from src.config.config import configuration
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
        self.build_log_path = ""
        self.mock_config_path = os.path.join(config_path, "clear.cfg")
        self.metadata = {}

    def package(self, source, cleanup=False):
        """Run main package build routine."""
        self.round += 1
        self.success = 0
        mock_cmd = get_mock_cmd()
        mock_opts = get_mock_opts()
        self.mock_config_path = os.path.join(config_path, "clear.cfg")
        logger.info("Building package " + source.name + " round", self.round)

        self.uniqueext = source.name

        if cleanup:
            cleanup_flag = "--cleanup-after"
        else:
            cleanup_flag = "--no-cleanup-after"

        print("{} mock chroot at /var/lib/mock/clear-{}".format(source.name, self.uniqueext))

        if self.round == 1:
            os.chdir(configuration.download_path)
            results_dirs_to_delete = [d for d in os.listdir() if re.match(r'^results.*', d) and os.path.isdir(d)]
            for d in results_dirs_to_delete:
                shutil.rmtree(d, ignore_errors=True)
            os.makedirs('{}/results'.format(configuration.download_path))

        cmd_args = [
            mock_cmd,
            f"--root={self.mock_config_path}",
            "--buildsrpm",
            "--sources=./",
            f"--spec={source.name}.spec",
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
             logfile=f"{configuration.download_path}/results/mock_srpm.log",
             cwd=configuration.download_path)

        # back up srpm mock logs
        call("mv results/root.log results/srpm-root.log", cwd=configuration.download_path)
        call("mv results/build.log results/srpm-build.log", cwd=configuration.download_path)

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
                   logfile=f"{configuration.download_path}/results/mock_build.log",
                   check=False,
                   cwd=configuration.download_path)

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
                       logfile=f"{configuration.download_path}/results/mock_build.log",
                       check=False,
                       cwd=configuration.download_path)

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
                   logfile=f"{configuration.download_path}/results/mock_build.log",
                   check=False,
                   cwd=configuration.download_path)

        # sanity check the build log
        self.build_log_path = configuration.download_path + "/results/build.log"
        if not os.path.exists(self.build_log_path):
            logger.error("Mock command failed, results log does not exist. User may not have correct permissions.")
            exit(1)

        if not self.parse_buildroot_log(configuration.download_path + "/results/root.log", ret):
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


def mock_init(tarball):
    os.chdir(configuration.download_path)
    # init tar file
    if ".tar" in tarball or ".zip" in tarball:
        cmd = f"cp -y {tarball} ."
    elif os.path.isdir(tarball):
        cmd = f"tar -xzvf {os.path.basename(tarball)}.tar.gz {tarball}/"
    else:
        logger.error("unsupported source file type")
        return
    call(cmd)
