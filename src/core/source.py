# SPDX-License-Identifier: MulanPSL-2.0+
# Copyright (c) 2022 Huawei Technologies Co., Ltd. All rights reserved.

import os
import sys
import re
import tarfile
import zipfile
from src.config.config import configuration
from src.log import logger
from src.utils.file_util import get_sha1sum, write_out
from src.utils.cmd_util import call, has_file_type
from src.utils.pypidata import do_curl


def convert_version(ver_str, name):
    """Remove disallowed characters from the version."""
    # banned substrings. It is better to remove these here instead of filtering
    # them out with expensive regular expressions
    banned_subs = ["x86.64", "source", "src", "all", "bin", "release", "rh",
                   "ga", ".ce", "lcms", "onig", "linux", "gc", "sdk", "orig",
                   "jurko", "%2f", "%2F", "%20"]

    # package names may be modified in the version string by adding "lib" for
    # example. Remove these from the name before trying to remove the name from
    # the version
    name_mods = ["lib", "core", "pom", "opa-"]

    # enforce lower-case strings to make them easier to standardize
    ver_str = ver_str.lower()
    # remove the package name from the version string
    ver_str = ver_str.replace(name.lower(), '')
    # handle modified name substrings in the version string
    for mod in name_mods:
        ver_str = ver_str.replace(name.replace(mod, ""), "")

    # replace illegal characters
    ver_str = ver_str.strip().replace('-', '.').replace('_', '.')

    # remove banned substrings
    for sub in banned_subs:
        ver_str = ver_str.replace(sub, "")

    # remove consecutive '.' characters
    while ".." in ver_str:
        ver_str = ver_str.replace("..", ".")

    return ver_str.strip(".")


def do_regex(patterns, re_str):
    """Find a match in multiple patterns."""
    for p in patterns:
        match = re.search(p, re_str)
        if match:
            return match


def get_contents(filename):
    """Get contents of filename."""
    with open(filename, "rb") as f:
        return f.read()


class Source:
    """Holds data and methods for source code or archives management."""
    def __init__(self, url, name, path):
        """Set default values for source file."""
        self.url = url
        self.name = name
        self.version = ""
        self.destination = ""
        self.type = None
        self.prefix = None
        self.subdir = None
        self.compilations = set()
        self.pattern_strength = 0
        self.release = 1
        if url:
            self.work_path = configuration.download_path
            self.path = self.check_or_get_file(url)
        else:
            self.path = path
        self.set_type()
        self.set_prefix()

    def set_type(self):
        """Determine compression type."""
        if self.url.lower().endswith(('.zip', 'jar')):
            self.type = 'zip'
        else:
            self.type = 'tar'

    def set_prefix(self):
        """Determine the prefix and subdir if no prefix."""
        prefix_method = getattr(self, 'set_{}_prefix'.format(self.type))
        prefix_method()
        # When there is no prefix, create subdir
        if not self.prefix:
            self.subdir = os.path.splitext(os.path.basename(self.path))[0]

    def set_tar_prefix(self):
        """Determine prefix folder name of tar file."""
        if tarfile.is_tarfile(self.path):
            with tarfile.open(self.path, 'r') as content:
                lines = content.getnames()
                # When tarball is not empty
                if len(lines) == 0:
                    logger.error("Tar file doesn't appear to have any content")
                    sys.exit(1)
                elif len(lines) > 1:
                    self.prefix = os.path.commonpath(lines)
        else:
            logger.info("Not a valid tar file.")
            sys.exit(1)

    def set_zip_prefix(self):
        """Determine prefix folder name of zip file."""
        if zipfile.is_zipfile(self.path):
            with zipfile.ZipFile(self.path, 'r') as content:
                lines = content.namelist()
                # When zipfile is not empty
                if len(lines) > 0:
                    self.prefix = os.path.commonpath(lines)
                else:
                    logger.info("Zip file doesn't appear to have any content")
                    sys.exit(1)
        else:
            logger.info("Not a valid zip file.")
            sys.exit(1)

    def extract(self, base_path):
        """Prepare extraction path and call specific extraction method."""
        if not self.prefix:
            extraction_path = os.path.join(base_path, self.subdir)
        else:
            extraction_path = base_path

        extract_method = getattr(self, 'extract_{}'.format(self.type))
        extract_method(extraction_path)

    def extract_tar(self, extraction_path):
        """Extract tar in path."""
        with tarfile.open(self.path) as content:
            content.extractall(path=extraction_path)

    def extract_zip(self, extraction_path):
        """Extract zip in path."""
        with zipfile.ZipFile(self.path, 'r') as content:
            content.extractall(path=extraction_path)

    def write_upstream(self, sha, file_name, mode="w"):
        """Write the upstream hash to the upstream file."""
        write_out(os.path.join(self.work_path, "upstream"),
                  os.path.join(sha, file_name) + "\n", mode=mode)

    def name_and_version(self):
        """Parse the url for the package name and version."""
        tarfile = os.path.basename(self.url)

        # If both name and version overrides are set via commandline, set the name
        # and version variables to the overrides and bail. If only one override is
        # set, continue to autodetect both name and version since the URL parsing
        # handles both. In this case, wait until the end to perform the override of
        # the one that was set. An extra conditional, that version_arg is a string
        # is added to enable a package to have multiple versions at the same time
        # for some language ecosystems.
        if self.name and self.version:
            self.version = convert_version(self.version, self.name)
            return

        name = self.name
        version = ""
        # it is important for the more specific patterns to come first
        pattern_options = [
            # handle font packages with names ending in -nnndpi
            r"(.*-[0-9]+dpi)[-_]([0-9]+[a-zA-Z0-9\+_\.\-\~]*)\.(tgz|tar|zip)",
            r"(.*?)[-_][vs]?([0-9]+[a-zA-Z0-9\+_\.\-\~]*)\.(tgz|tar|zip)",
        ]
        match = do_regex(pattern_options, tarfile)
        if match:
            name = match.group(1).strip()
            version = convert_version(match.group(2), name)

        # R package
        if "cran.r-project.org" in self.url or "cran.rstudio.com" in self.url and name:
            name = "R-" + name

        if ".cpan.org/" in self.url or ".metacpan.org/" in self.url and name:
            name = "perl-" + name

        if "github.com" in self.url:
            # define regex accepted for valid packages, important for specific
            # patterns to come before general ones
            github_patterns = [r"https?://github.com/(.*)/(.*?)/archive/refs/tags/[vVrR]?(.*)\.tar",
                               r"https?://github.com/(.*)/(.*?)/archive/[v|r]?.*/(.*).tar",
                               r"https?://github.com/(.*)/(.*?)/archive/[-a-zA-Z_]*-(.*).tar",
                               r"https?://github.com/(.*)/(.*?)/archive/[vVrR]?(.*).tar",
                               r"https?://github.com/(.*)/.*-downloads/releases/download/.*?/(.*)-(.*).tar",
                               r"https?://github.com/(.*)/(.*?)/releases/download/(.*)/",
                               r"https?://github.com/(.*)/(.*?)/files/.*?/(.*).tar"]

            match = do_regex(github_patterns, self.url)
            if match:
                repo = match.group(2).strip()
                if repo not in name:
                    # Only take the repo name as the package name if it's more descriptive
                    name = repo
                elif name != repo:
                    name = re.sub(r"release-", '', name)
                    name = re.sub(r"\d*$", '', name)
                version = match.group(3).replace(name, '')
                if "/archive/" not in self.url:
                    version = re.sub(r"^[-_.a-zA-Z]+", "", version)
                version = convert_version(version, name)

        # SQLite tarballs use 7 digit versions, e.g 3290000 = 3.29.0, 3081002 = 3.8.10.2
        if "sqlite.org" in self.url:
            major = version[0]
            minor = version[1:3].lstrip("0").zfill(1)
            patch = version[3:5].lstrip("0").zfill(1)
            build = version[5:7].lstrip("0")
            version = major + "." + minor + "." + patch + "." + build
            version = version.strip(".")

        if "mirrors.kernel.org" in self.url:
            m = re.search(r".*/sourceware/(.*?)/releases/(.*?).tgz", self.url)
            if m:
                name = m.group(1).strip()
                version = convert_version(m.group(2), name)

        if "sourceforge.net" in self.url:
            scf_pats = [r"projects/.*/files/(.*?)/(.*?)/[^-]*(-src)?.tar.gz",
                        r"downloads.sourceforge.net/.*/([a-zA-Z]+)([-0-9\.]*)(-src)?.tar.gz"]
            match = do_regex(scf_pats, self.url)
            if match:
                name = match.group(1).strip()
                version = convert_version(match.group(2), name)

        if "bitbucket.org" in self.url:
            bitbucket_pats = [r"/.*/(.*?)/.*/.*v([-\.0-9a-zA-Z_]*?).(tar|zip)",
                              r"/.*/(.*?)/.*/([-\.0-9a-zA-Z_]*?).(tar|zip)"]

            match = do_regex(bitbucket_pats, self.url)
            if match:
                name = match.group(1).strip()
                version = convert_version(match.group(2), name)

        if "gitlab.com" in self.url:
            # https://gitlab.com/leanlabsio/kanban/-/archive/1.7.1/kanban-1.7.1.tar.gz
            m = re.search(r"gitlab\.com/.*/(.*)/-/archive/(?:VERSION_|[vVrR])?(.*)/", self.url)
            if m:
                name = m.group(1).strip()
                version = convert_version(m.group(2), name)

        if "git.sr.ht" in self.url:
            # https://git.sr.ht/~sircmpwn/scdoc/archive/1.9.4.tar.gz
            m = re.search(r"git\.sr\.ht/.*/(.*)/archive/(.*).tar.gz", self.url)
            if m:
                name = m.group(1).strip()
                version = convert_version(m.group(2), name)

        if "pigeonhole.dovecot.org" in self.url:
            # https://pigeonhole.dovecot.org/releases/2.3/dovecot-2.3-pigeonhole-0.5.20.tar.gz
            if m := re.search(r"pigeonhole\.dovecot\.org/releases/.*/dovecot-[\d\.]+-(\w+)-([\d\.]+)\.[^\d]", self.url):
                name = m.group(1).strip()
                version = convert_version(m.group(2), name)

        if ".ezix.org" in self.url:
            # https://www.ezix.org/software/files/lshw-B.02.19.2.tar.gz
            if m := re.search(r"(\w+)-[A-Z]\.(\d+(?:\.\d+)+)", self.url):
                name = m.group(1).strip()
                version = convert_version(m.group(2), name)

        if self.name and not version:
            # In cases where we have a name but no version
            # use what is after the name.
            # https://invisible-mirror.net/archives/lynx/tarballs/lynx2.8.9rel.1.tar.gz
            postname = tarfile.split(self.name)[-1]
            no_extension = os.path.splitext(postname)[0]
            if no_extension.endswith('.tar'):
                no_extension = os.path.splitext(no_extension)[0]
            version = convert_version(no_extension, self.name)

        # override name and version from commandline
        self.name = self.name if self.name else name
        self.version = self.version if self.version else version

    def check_or_get_file(self, url, mode="w"):
        """Download tarball from url unless it is present locally."""
        tarball_path = os.path.join(self.work_path, os.path.basename(url))
        if not os.path.isfile(tarball_path):
            do_curl(url, dest=tarball_path, is_fatal=True)
        self.write_upstream(get_sha1sum(tarball_path), tarball_path, mode)
        return tarball_path

    def print_header(self):
        """Print header for autospec run."""
        logger.info("\n")
        logger.info("Processing:" + self.url)
        logger.info("=" * 105)
        logger.info("Prefix      :" + self.prefix)

    def add_build_pattern(self, pattern, strength):
        """Set the global default pattern and pattern strength."""
        if strength <= self.pattern_strength or pattern in self.compilations:
            return
        self.compilations.add(pattern)
        self.pattern_strength = strength

    def scan_compilations(self):
        for dir_path, _, files in os.walk(self.path):
            default_score = 2 if dir_path == self.path else 1

            if "Cargo.toml" in files:
                self.add_build_pattern('cargo', default_score)

            if "CMakeLists.txt" in files and "configure.ac" not in files:
                self.add_build_pattern("cmake", default_score)

            if "configure" in files and os.access(dir_path + '/configure', os.X_OK):
                self.add_build_pattern("configure", default_score)

            if ("requirements.txt" in files and "pyproject.toml" in files) or "setup.py" in files:
                self.add_build_pattern("python", default_score)

            if "Makefile.PL" in files or "Build.PL" in files:
                self.add_build_pattern("cpan", default_score)

            if "SConstruct" in files:
                self.add_build_pattern("scons", default_score)

            if "meson.build" in files:
                self.add_build_pattern("meson", default_score)

            if "pom.xml" in files:
                self.add_build_pattern("java_pom", default_score)

            if "Makefile" in files:
                self.add_build_pattern("make", default_score)

            if "package.json" in files and has_file_type(self.path, "js"):
                self.add_build_pattern("javascript", default_score)

            if ("autogen.sh" in files or "build.sh" in files or "compile.sh" in files) and default_score == 2:
                self.add_build_pattern("shell", default_score)
            elif "Makefile.am" in files and "configure.ac" in files:
                self.add_build_pattern("autotools", default_score)

    def init_workplace(self):
        """
        when input url,change path to directory path,then scan compilation
        :return:
        """
        self.name_and_version()
        # Download and process extra sources: archives
        if os.path.isfile(self.path):
            # Now that the metadata has been collected print the header
            self.print_header()
            prefix_path = os.path.join(os.path.dirname(self.path), self.prefix)
            call(f"rm -rf {prefix_path}")
            if self.type == "tar":
                with tarfile.open(self.path) as tar:
                    tar.extractall(os.path.dirname(self.path))
            elif self.type == "zip":
                with zipfile.ZipFile(self.path) as z:
                    z.extractall(os.path.dirname(self.path))
            self.path = prefix_path
        self.scan_compilations()
