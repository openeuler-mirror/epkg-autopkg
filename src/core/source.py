# SPDX-License-Identifier: MulanPSL-2.0+
# Copyright (c) 2022 Huawei Technologies Co., Ltd. All rights reserved.

import os
import sys
import re
from io import BytesIO
import pycurl
import tarfile
import zipfile
from src.log import logger
from src.utils.file_util import get_sha1sum, write_out


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
            self.path = self.check_or_get_file(url, os.path.basename(url))
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

    def write_upstream(self, sha, tarfile, mode="w"):
        """Write the upstream hash to the upstream file."""
        write_out(os.path.join(self.path, "upstream"),
                  os.path.join(sha, tarfile) + "\n", mode=mode)

    def name_and_version(self, filemanager):
        """Parse the url for the package name and version."""
        tarfile = os.path.basename(self.url)

        # If both name and version overrides are set via commandline, set the name
        # and version variables to the overrides and bail. If only one override is
        # set, continue to auto detect both name and version since the URL parsing
        # handles both. In this case, wait until the end to perform the override of
        # the one that was set. An extra conditional, that version_arg is a string
        # is added to enable a package to have multiple versions at the same time
        # for some language ecosystems.
        if self.name and self.version:
            # rawname == name in this case
            self.rawname = self.name
            self.version = convert_version(self.version, self.name)
            return

        name = self.name
        self.rawname = self.name
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
            filemanager.want_dev_split = False
            self.rawname = name
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
                self.repo = match.group(2).strip()
                if self.repo not in name:
                    # Only take the repo name as the package name if it's more descriptive
                    name = self.repo
                elif name != self.repo:
                    name = re.sub(r"release-", '', name)
                    name = re.sub(r"\d*$", '', name)
                self.rawname = name
                version = match.group(3).replace(name, '')
                if "/archive/" not in self.url:
                    version = re.sub(r"^[-_.a-zA-Z]+", "", version)
                version = convert_version(version, name)
                if not self.giturl:
                    self.giturl = "https://github.com/" + match.group(1).strip() + "/" + self.repo + ".git"

        # SQLite tarballs use 7 digit versions, e.g 3290000 = 3.29.0, 3081002 = 3.8.10.2
        if "sqlite.org" in self.url:
            major = version[0]
            minor = version[1:3].lstrip("0").zfill(1)
            patch = version[3:5].lstrip("0").zfill(1)
            build = version[5:7].lstrip("0")
            version = major + "." + minor + "." + patch + "." + build
            version = version.strip(".")

        # Construct gitlab giturl for GNOME projects, and update previous giturls
        # that pointed to the GitHub mirror.
        if "download.gnome.org" in self.url:
            if not self.giturl or "github.com/GNOME" in self.giturl or "git.gnome.org" in self.giturl:
                self.giturl = "https://gitlab.gnome.org/GNOME/{}".format(name)

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

    def download(self, dest=None, post=None, is_fatal=False):
        """
        Perform a curl operation for `url`.

        If `post` is set, a POST is performed for `url` with fields taken from the
        specified value. Otherwise a GET is performed for `url`. If `dest` is set,
        the curl response (if successful) is written to the specified path and the
        path is returned. Otherwise a successful response is returned as a BytesIO
        object. If `is_fatal` is `True` (`False` is the default), a GET failure,
        POST failure, or a failure to write to the path specified for `dest`
        results in the program exiting with an error. Otherwise, `None` is returned
        for any of those error conditions.
        """
        c = pycurl.Curl()
        c.setopt(c.URL, self.url)
        if post:
            c.setopt(c.POSTFIELDS, post)
        c.setopt(c.FOLLOWLOCATION, True)
        c.setopt(c.FAILONERROR, True)
        c.setopt(c.CONNECTTIMEOUT, 10)
        c.setopt(c.TIMEOUT, 600)
        c.setopt(c.LOW_SPEED_LIMIT, 1)
        c.setopt(c.LOW_SPEED_TIME, 10)
        c.setopt(c.SSL_VERIFYPEER, 0)
        c.setopt(c.SSL_VERIFYHOST, 0)
        buf = BytesIO()
        c.setopt(c.WRITEDATA, buf)
        try:
            c.perform()
        except pycurl.error as e:
            if is_fatal:
                logger.error("Unable to fetch {}: {}".format(self.url, e))
                sys.exit(1)
            return None
        finally:
            c.close()

        # write to dest if specified
        if dest:
            try:
                with open(dest, 'wb') as fp:
                    fp.write(buf.getvalue())
            except IOError as e:
                if os.path.exists(dest):
                    os.unlink(dest)
                if is_fatal:
                    logger.error("Unable to write to {}: {}".format(dest, e))
                    sys.exit(1)
                return None

        if dest:
            return dest
        else:
            return buf

    def check_or_get_file(self, tar_file, mode="w"):
        """Download tarball from url unless it is present locally."""
        tarball_path = os.path.join(self.path, tar_file)
        if not os.path.isfile(tarball_path):
            self.download(dest=tarball_path, is_fatal=True)
            self.write_upstream(get_sha1sum(tarball_path), tarfile, mode)
        else:
            self.write_upstream(get_sha1sum(tarball_path), tarfile, mode)
        return tarball_path

    def print_header(self):
        """Print header for autospec run."""
        logger.info("\n")
        logger.info("Processing", self.url)
        logger.info("=" * 105)
        logger.info("Prefix      :", self.prefix)

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

    def process(self, build=False):
        """
        when input url,download tarball and return source path,then scan compilation
        :param build:
        :return:
        """
        # Download and process extra sources: archives
        if self.url:
            # set global path with tarball_prefix
            self.path = os.path.join(self.path, self.prefix)
            # Now that the metadata has been collected print the header
            self.print_header()
            self.download()
        if self.path:
            self.scan_compilations()
