# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; specifically version 2 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
#
# See LICENSE for more details.
#
# Copyright: Red Hat (c) 2023 and Avocado contributors

import os


class BuildConfig:
    download_path = ""
    buildroot_path = "/opt/buildroot"
    phase_member = ["prep", "build", "configure", "install", "check", "clean"]
    language_for_compilation = {
        "python": "python",
        "ruby": "ruby",
        "java": "maven",
        "javascript": "nodejs",
        "perl": "perl",
    }
    logfile = "build.log"
    configure_failed_pats = [
        ("", "")
    ]
    build_success_echo = "build success"
    pkgconfig_pats = [
        (r"which: no qmake", "Qt"),
        (r"checking for UDEV\.\.\. no", "udev"),
        (r"XInput2 extension not found", "xi"),
        (r"checking for UDEV\.\.\. no", "libudev"),
        (r"error\: xml2-config not found", "libxml-2.0"),
        (r"XMLLINT not set and xmllint not found in path", "libxml-2.0"),
        (r"error: must install xorg-macros", "xorg-macros"),
        (r"[ ]*systemdunitdir:[ ]*$", 'systemd'),
    ]
    simple_pats = [
        (r'warning: failed to load external entity "http://docbook.sourceforge.net/release/xsl/.*"', "docbook-xml"),
        (r"gobject-introspection dependency was not found, gir cannot be generated.", "glibc-bin"),
        (r"gobject-introspection dependency was not found, gir cannot be generated.", "gobject-introspection-devel"),
        (r"Cannot find development files for any supported version of libnl", "libnl-dev"),
        (r"/<http:\/\/www.cmake.org>", "cmake"),
        (r"XInput2 extension not found", "inputproto"),
        (r"\-\- Boost libraries:", "boost-devel"),
        (r"^WARNING: could not find 'runtest'$", "dejagnu"),
        (r"^WARNING: could not find 'runtest'$", "tcl"),
        (r"^WARNING: could not find 'runtest'$", "expect"),
        (r"VignetteBuilder package required for checking but installed:", "R-knitr"),
        (r"You must have XML::Parser installed", "perl(XML::Parser)"),
        (r"checking for.*in -ljpeg... no", "libjpeg-turbo-devel"),
        (r"checking for Apache .* module support", "httpd-devel"),
        (r"\* tclsh failed", "tcl"),
        (r"checking \"location of ncurses\.h file\"", "ncurses-devel"),
        (r"\/usr\/include\/python3\.[0-9]+m\/pyconfig.h", "python3-devel"),
        (r"Can't exec \"aclocal\"", "automake"),
        (r"Can't exec \"aclocal\"", "libtool"),
        (r"configure: error: No curses header-files found", "ncurses-devel"),
        (r"configure: error: no suitable Python interpreter found", "python3-devel"),
        (r"Checking for header Python.h", "python3-devel"),
        (r" \/usr\/include\/python3\.", "python3-devel"),
        (r"testing autoconf... not found", "autoconf"),
        (r"to compile python extensions", "python3-devel"),
        (r"configure\: error\: could not find Python headers", "python3-devel"),
        (r"checking for slang.h... no", "slang-devel"),
        (r"checking for libxml libraries", "libxml2-devel"),
        (r"configure: error: no suitable Python interpreter found", "python3"),
        (r"configure: error: pcre-config for libpcre not found", "pcre"),
        (r"Unable to find the requested Boost libraries.", "boost-devel"),
        (r"checking for OpenSSL", "openssl-devel"),
        (r"libproc not found. Please configure without procps", "procps-ng-devel"),
        (r"C library 'efivar' not found", "efivar-devel"),
        (r"configure: error: glib2", "glib-devel"),
        (r"Has header \"efi.h\": NO", "gnu-efi-devel"),
        (r".*: error: HAVE_INTROSPECTION does not appear in AM_CONDITIONAL", 'gobject-introspection-devel'),
        (r"ERROR: Could not execute Vala compiler", "vala"),
        (r".*error: possibly undefined macro: AC_PROG_LIBTOOL", "libtool"),
    ]
    # failed_pattern patterns
    # contains patterns for parsing build.log for missing dependencies
    make_failed_pats = [
        r"    ([a-zA-Z]+\:\:[a-zA-Z]+) not installed",
        r"(?:-- )?(?:Could|Did) (?:NOT|not) find ([a-zA-Z0-9_-]+)",
        r" ([a-zA-Z0-9\-]*\.m4) not found",
        r" exec: ([a-zA-Z0-9\-]+): not found",
        r"([a-zA-Z0-9\-\_\.]*)\: command not found",
        r"([a-zA-Z\-]*) (?:validation )?tool not found or not executable",
        r"([a-zA-Z\-]+) [0-9\.]+ is required to configure this module; "
        r"please install it or upgrade your CPAN\/CPANPLUS shell.",
        r"-- (.*) not found.",
        r".* /usr/bin/([a-zA-Z0-9-_]*).*not found",
        r"/usr/bin/env\: (.*)\: No such file or directory",
        r"/usr/bin/python.*\: No module named (.*)",
        r"Add the installation prefix of \"(.*)\" to CMAKE_PREFIX_PATH",
        r"By not providing \"([a-zA-Z0-9]+).cmake\" in CMAKE_MODULE_PATH this project",
        r"C library '(.*)' not found",
        r"Cannot find ([a-zA-Z0-9\-_\.]*)",
        r"Checking for (.*?)\.\.\.no",
        r"Checking for (.*?)\s*: not found",
        r"Checking for (.*?)\s>=.*\s*: not found",
        r"Could not find suitable distribution for Requirement.parse\('([a-zA-Z\-\.]*)",
        r"Downloading https?://.*\.python\.org/packages/.*/.?/([A-Za-z]*)/.*",
        r"Error: Unable to find (.*)",
        r"ImportError\: ([a-zA-Z]+) module missing",
        r"ImportError\: (?:No module|cannot import) named? (.*)",
        r"No library found for -l([a-zA-Z\-])",
        r"No rule to make target `(.*)',",
        r"Program (.*) found: NO",
        r"Target '[a-zA-Z0-9\-]' can't be generated as '(.*)' could not be found",
        r"Unable to `import (.*)`",
        r"Unable to find '(.*)'",
        r"Warning\: no usable ([a-zA-Z0-9]+) found",
        r"You need ([a-zA-Z0-9\-\_]*) to build this program.",
        r"[Dd]ependency (.*) found: NO",
        r"(?:\/usr)?\/bin\/ld: cannot find (-l[a-zA-Z0-9\_]+)",
        r"^.*Could not find a package configuration file provided by \"(.*)\".*$",
        r"^.*\"(.*)\" with any of the following names.*$",
        r"[Cc]hecking for (.*) (?:support|development files|with pkg-config)?\.\.\. [Nn]o",
        r"checking (.*?)\.\.\. no",
        r"checking for (.*) in default path\.\.\. not found",
        r"checking for (.*)... configure: error",
        r"checking for (.*?)\.\.\. no",
        r"checking for [a-zA-Z0-9\_\-]+ in (.*?)\.\.\. no",
        r"checking for library containing (.*)... no",
        r"configure: error: (?:pkg-config missing|Unable to locate) (.*)",
        r"configure: error: ([a-zA-Z0-9]+) (?:is required to build|not found)",
        r"configure: error: Cannot find (.*)\. Make sure",
        r"fatal error\: (.*)\: No such file or directory",
        r"make: ([a-zA-Z0-9].+): (?:Command not found|No such file or directory)",
        r"meson\.build\:[\d]+\:[\d]+\: ERROR: C(?: shared or static)? library \'(.*)\' not found",
        r"unable to execute '([a-zA-Z\-]*)': No such file or directory",
        r"warning: failed to load external entity \"(/usr/share/sgml/docbook/xsl-stylesheets)/.*\"",
        r"which\: no ([a-zA-Z\-]*) in \(",
        r"(a-zA-Z0-9\-) not found (re-run dependencies script to install)",
        r"autoreconf: error: (\w+) failed",
    ]
    pkgconfig_failed_pats = [
        r"Native dependency '(.*)' not found",
        r"No package '([a-zA-Z0-9\-:]*)' found",
        r"Package (.*) was not found in the pkg-config search path.",
        r"Package '([a-zA-Z0-9\-:]*)', required by '.*', not found",
        r"Perhaps you should add the directory containing `([a-zA-Z0-9\-:]*)\.pc'",
        r"[Dd]ependency (.*) found: NO \(tried pkgconfig(?: and cmake)?\)",
        r"[Cc]hecking pkg-config for (.*?)\.\.\. [Nn]o"
    ]
    cmake_failed_pats = [
        r"CMake Error at cmake\/modules\/([a-zA-Z0-9]+).cmake",
        r"^.*By not providing \"Find(.*).cmake\" in CMAKE_MODULE_PATH this.*$",
    ]
    perl_failed_pats = [
        r"    !  ([a-zA-Z:]+) is not installed",
        r"Can't locate [a-zA-Z0-9_\-\/\.]+ in @INC \(you may need to install the ([a-zA-Z0-9_\-:]+) module\)",
        r"Warning: prerequisite ([a-zA-Z:]+) [0-9\.]+ not found.",
        r"checking for perl module ([a-zA-Z:]+) [0-9\.]+... no",
        r"you may need to install the ([a-zA-Z0-9_\-:\.]*) module"
    ]
    pypi_failed_pats = [
        r"Download error on https://pypi.python.org/simple/([a-zA-Z0-9\-\._:]+)/",
        r"ImportError:.* No module named '?([a-zA-Z0-9\-\._]+)'?",
        r"ModuleNotFoundError.*No module named '?(.*)'?",
        r"No (?:matching distribution|local packages or working download links) found for ([a-zA-Z0-9\-\.\_]+)",
    ]
    go_failed_pats = [
        r".*\.go:.*cannot find package \"(.*)\" in any of:",
    ]
    java_failed_pats = [
        r"Plugin ([a-zA-Z\-.:]+):([0-9.]+) or one of its dependencies could not be resolved",
        r"Unable to generate requires on unresolvable artifacts: ([a-zA-Z0-9-.:]+(, ){0,1}){1,}",
        r"Could not resolve dependencies for project ([a-zA-Z.:]+):jar:([0-9.]+): Cannot access ([a-zA-Z-]+) \("
        r"[a-zA-Z0-9.://-]+\) in offline mode and the artifact ([a-zA-Z.\-:]+):jar:([0-9.]+) has not been downloaded from it before",
    ]
    ruby_failed_pats = []
    meson_failed_pats = []
    nodejs_failed_pats = []
    make_failed_flags = [
        r"error: ([a-zA-Z\-]*)invalid attempt.*in symbol.*"
    ]
    cmake_search_failed = r"(CMake Error .* CMakeLists.txt).*"
    cmake_failed_flags = [
        r"enable .*or +disable +([-_A-Z]+)",
        r"set +([-_A-Z]+) false"
    ]
    failed_commands = {}
    ignored_commands = {}
    failed_flags = {}
    qt_modules = {}
    cmake_modules = {}
    analysis_tool_path = '/root/dependency-analysis/package_mapping.py'

    def setup_patterns(self, path=None):
        """Read each pattern configuration file and assign to the appropriate variable."""
        self.read_pattern_conf("ignored_commands", self.ignored_commands, path=path)
        self.read_pattern_conf("failed_commands", self.failed_commands, path=path)
        self.read_pattern_conf("failed_flags", self.failed_flags, path=path)
        # self.read_pattern_conf("gems", self.gems, path=path)
        self.read_pattern_conf("qt_modules", self.qt_modules, path=path)
        self.read_pattern_conf("cmake_modules", self.cmake_modules, path=path)

    def read_pattern_conf(self, file_name, param, path=None):
        if path is None:
            from src.config import config_path
            path = config_path
        config_file_path = os.path.join(path, file_name)
        with open(config_file_path, "r") as f:
            config_lists = f.readlines()
        for item in config_lists:
            if "," not in item or item.strip().startswith("#"):
                continue
            k, v = item.split(",", 1)
            value = v.strip().split() if " " in v.strip() else v
            if isinstance(param, dict):
                param[k] = value


configuration = BuildConfig()
