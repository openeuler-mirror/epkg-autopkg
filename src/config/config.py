import os


def read_pattern_conf(filename, dest, list_format=False, path=None):
    """Read a fail-pattern configuration file.

    Read fail-pattern config file in the form of <pattern>, <package> and ignore lines starting with '#.'
    """
    file_repo_dir = os.path.dirname(os.path.abspath(__file__))
    file_conf_path = os.path.join(path, filename) if path else None
    file_repo_path = os.path.join(file_repo_dir, filename)
    if not os.path.isfile(file_repo_path):
        return
    if file_conf_path and os.path.isfile(file_conf_path):
        # The file_conf_path version of a pattern will be used in case of conflict
        file_path = [file_repo_path, file_conf_path]
    else:
        file_path = [file_repo_path]
    for fpath in file_path:
        with open(fpath, "r") as patfile:
            for line in patfile:
                if line.startswith("#"):
                    continue
                if line.startswith(r"\#"):
                    line = line[1:]
                # Make list format a dict for faster lookup times
                if list_format:
                    dest[line.strip()] = True
                    continue
                # split from the right a maximum of one time, since the pattern
                # string might contain ", "
                pattern, package = line.rsplit(", ", 1)
                dest[pattern] = package.rstrip()


class BuildConfig:
    download_path = ""
    phase_member = ["prep", "build", "configure", "install", "check", "clean"]
    conf_args_openmpi = '--program-prefix=  --exec-prefix=$MPI_ROOT \\\n' \
                        '--libdir=$MPI_LIB --bindir=$MPI_BIN --sbindir=$MPI_BIN --includedir=$MPI_INCLUDE \\\n' \
                        '--datarootdir=$MPI_ROOT/share --mandir=$MPI_MAN -exec-prefix=$MPI_ROOT --sysconfdir=$MPI_SYSCONFIG \\\n' \
                        '--build=x86_64-generic-linux-gnu --host=x86_64-generic-linux-gnu --target=x86_64-clr-linux-gnu '
    # defines which files to rename and copy to autospec directory,
    # used in commitmessage.py
    transforms = {
        'changes': 'ChangeLog',
        'changelog.txt': 'ChangeLog',
        'changelog': 'ChangeLog',
        'change.log': 'ChangeLog',
        'ChangeLog.md': 'ChangeLog',
        'changes.rst': 'ChangeLog',
        'changes.txt': 'ChangeLog',
        'news': 'NEWS',
        'meson_options.txt': 'meson_options.txt'
    }
    config_options = {
        "broken_c++": "extend flags with '-std=gnu++98",
        "cargo_vendor": "create vendor archive with cargo",
        "use_lto": "configure build for lto",
        "use_avx2": "configure build for avx2",
        "use_avx512": "configure build for avx512",
        "keepstatic": "do not remove static libraries",
        "asneeded": "unset %build LD_AS_NEEDED variable",
        "allow_test_failures": "allow package to build with test failures",
        "skip_tests": "Do not run test suite",
        "no_autostart": "do not require autostart subpackage",
        "optimize_size": "optimize build for size over speed",
        "funroll-loops": "optimize build for speed over size",
        "full-debug-info": "compile full (traditional) debug info",
        "fast-math": "pass -ffast-math to compiler",
        "insecure_build": "set flags to smallest -02 flags possible",
        "conservative_flags": "set conservative build flags",
        "broken_parallel_build": "disable parallelization during build",
        "pgo": "set profile for pgo",
        "use_clang": "add clang flags",
        "32bit": "build 32 bit libraries",
        "nostrip": "disable stripping binaries",
        "verify_required": "require package verification for build",
        "security_sensitive": "set flags for security-sensitive builds",
        "so_to_lib": "add .so files to the lib package instead of dev",
        "dev_requires_extras": "dev package requires the extras to be installed",
        "autoupdate": "this package is trusted enough to automatically update (used by other tools)",
        "compat": "this package is a library compatibility package and only ships versioned library files",
        "nodebug": "do not generate debuginfo for this package",
        "openmpi": "configure build also for openmpi",
        "server": "Package is only used by servers",
        "no_glob": "Do not use the replacement pattern for file matching"
    }
    # simple_pattern_pkgconfig patterns
    # contains patterns for parsing build.log for missing dependencies
    pkgconfig_pats = [
        (r"which: no qmake", "Qt"),
        (r"XInput2 extension not found", "xi"),
        (r"checking for UDEV\.\.\. no", "udev"),
        (r"checking for UDEV\.\.\. no", "libudev"),
        (r"XMLLINT not set and xmllint not found in path", "libxml-2.0"),
        (r"error\: xml2-config not found", "libxml-2.0"),
        (r"error: must install xorg-macros", "xorg-macros"),
        (r"[ ]*systemdunitdir:[ ]*$", 'systemd'),
    ]
    # simple_pattern patterns
    # contains patterns for parsing build.log for missing dependencies
    simple_pats = [
        (r'warning: failed to load external entity "http://docbook.sourceforge.net/release/xsl/.*"', "docbook-xml"),
        (r"gobject-introspection dependency was not found, gir cannot be generated.", "gobject-introspection-devel"),
        (r"gobject-introspection dependency was not found, gir cannot be generated.", "glibc-bin"),
        (r"Cannot find development files for any supported version of libnl", "libnl-dev"),
        (r"/<http:\/\/www.cmake.org>", "cmake"),
        (r"\-\- Boost libraries:", "boost-devel"),
        (r"XInput2 extension not found", "inputproto"),
        (r"^WARNING: could not find 'runtest'$", "dejagnu"),
        (r"^WARNING: could not find 'runtest'$", "expect"),
        (r"^WARNING: could not find 'runtest'$", "tcl"),
        (r"VignetteBuilder package required for checking but installed:", "R-knitr"),
        (r"You must have XML::Parser installed", "perl(XML::Parser)"),
        (r"checking for Apache .* module support", "httpd-devel"),
        (r"checking for.*in -ljpeg... no", "libjpeg-turbo-devel"),
        (r"\* tclsh failed", "tcl"),
        (r"\/usr\/include\/python3\.[0-9]+m\/pyconfig.h", "python3-devel"),
        (r"checking \"location of ncurses\.h file\"", "ncurses-devel"),
        (r"Can't exec \"aclocal\"", "automake"),
        (r"Can't exec \"aclocal\"", "libtool"),
        (r"configure: error: no suitable Python interpreter found", "python3-devel"),
        (r"Checking for header Python.h", "python3-devel"),
        (r"configure: error: No curses header-files found", "ncurses-devel"),
        (r" \/usr\/include\/python3\.", "python3-devel"),
        (r"to compile python extensions", "python3-devel"),
        (r"testing autoconf... not found", "autoconf"),
        (r"configure\: error\: could not find Python headers", "python3-devel"),
        (r"checking for libxml libraries", "libxml2-devel"),
        (r"checking for slang.h... no", "slang-devel"),
        (r"configure: error: no suitable Python interpreter found", "python3"),
        (r"configure: error: pcre-config for libpcre not found", "pcre"),
        (r"checking for OpenSSL", "openssl-devel"),
        (r"Unable to find the requested Boost libraries.", "boost-devel"),
        (r"libproc not found. Please configure without procps", "procps-ng-devel"),
        (r"configure: error: glib2", "glib-devel"),
        (r"C library 'efivar' not found", "efivar-devel"),
        (r"Has header \"efi.h\": NO", "gnu-efi-devel"),
        (r"ERROR: Could not execute Vala compiler", "vala"),
        (r".*: error: HAVE_INTROSPECTION does not appear in AM_CONDITIONAL", 'gobject-introspection-devel'),
    ]
    # failed_pattern patterns
    # contains patterns for parsing build.log for missing dependencies
    failed_pats = [
        (r"    !  ([a-zA-Z:]+) is not installed", 0, 'perl'),
        (r"    ([a-zA-Z]+\:\:[a-zA-Z]+) not installed", 1, None),
        (r"(?:-- )?(?:Could|Did) (?:NOT|not) find ([a-zA-Z0-9_-]+)", 0, None),
        (r" ([a-zA-Z0-9\-]*\.m4) not found", 0, None),
        (r" exec: ([a-zA-Z0-9\-]+): not found", 0, None),
        (r"([a-zA-Z0-9\-\_\.]*)\: command not found", 1, None),
        (r"([a-zA-Z\-]*) (?:validation )?tool not found or not executable", 0, None),
        (r"([a-zA-Z\-]+) [0-9\.]+ is required to configure this module; "
         r"please install it or upgrade your CPAN\/CPANPLUS shell.", 0, None),
        (r"-- (.*) not found.", 1, None),
        (r".* /usr/bin/([a-zA-Z0-9-_]*).*not found", 0, None),
        (r".*\.go:.*cannot find package \"(.*)\" in any of:", 0, 'go'),
        (r"/usr/bin/env\: (.*)\: No such file or directory", 0, None),
        (r"/usr/bin/python.*\: No module named (.*)", 0, None),
        (r"Add the installation prefix of \"(.*)\" to CMAKE_PREFIX_PATH", 0, None),
        (r"By not providing \"([a-zA-Z0-9]+).cmake\" in CMAKE_MODULE_PATH this project", 0, None),
        (r"C library '(.*)' not found", 0, None),
        (r"CMake Error at cmake\/modules\/([a-zA-Z0-9]+).cmake", 0, None),
        (r"Can't locate [a-zA-Z0-9_\-\/\.]+ in @INC \(you may need to install the ([a-zA-Z0-9_\-:]+) module\)", 0,
         'perl'),
        (r"Cannot find ([a-zA-Z0-9\-_\.]*)", 1, None),
        (r"Checking for (.*?)\.\.\.no", 0, None),
        (r"Checking for (.*?)\s*: not found", 0, None),
        (r"Checking for (.*?)\s>=.*\s*: not found", 0, None),
        (r"Could not find suitable distribution for Requirement.parse\('([a-zA-Z\-\.]*)", 0, None),
        (r"Download error on https://pypi.python.org/simple/([a-zA-Z0-9\-\._:]+)/", 0, 'pypi'),
        (r"Downloading https?://.*\.python\.org/packages/.*/.?/([A-Za-z]*)/.*", 0, None),
        (r"ERROR: dependencies ['‘]([a-zA-Z0-9\-\.]*)['’].* are not available for package ['‘].*['’]", 0, 'R'),
        (r"ERROR: dependencies ['‘].*['’], ['‘]([a-zA-Z0-9\-\.]*)['’],.* are not available for package ['‘].*['’]", 0,
         'R'),
        (r"ERROR: dependencies.*['‘]([a-zA-Z0-9\-\.]*)['’] are not available for package ['‘].*['’]", 0, 'R'),
        (r"ERROR: dependency ['‘]([a-zA-Z0-9\-\.]*)['’] is not available for package ['‘].*['’]", 0, 'R'),
        (r"Error: Unable to find (.*)", 0, None),
        (r"Error: package ['‘]([a-zA-Z0-9\-\.]*)['’] required by", 0, 'R'),
        (r"ImportError:.* No module named '?([a-zA-Z0-9\-\._]+)'?", 0, 'pypi'),
        (r"ImportError\: ([a-zA-Z]+) module missing", 0, None),
        (r"ImportError\: (?:No module|cannot import) named? (.*)", 0, None),
        (r"ModuleNotFoundError.*No module named '?(.*)'?", 0, 'pypi'),
        (r"Native dependency '(.*)' not found", 0, "pkgconfig"),
        (r"No library found for -l([a-zA-Z\-])", 0, None),
        (r"No (?:matching distribution|local packages or working download links) found for ([a-zA-Z0-9\-\.\_]+)", 0,
         'pypi'),
        (r"No package '([a-zA-Z0-9\-:]*)' found", 0, 'pkgconfig'),
        (r"No rule to make target `(.*)',", 0, None),
        (r"Package (.*) was not found in the pkg-config search path.", 0, 'pkgconfig'),
        (r"Package '([a-zA-Z0-9\-:]*)', required by '.*', not found", 0, 'pkgconfig'),
        (r"Package which this enhances but not available for checking: ['‘]([a-zA-Z0-9\-]*)['’]", 0, 'R'),
        (r"Perhaps you should add the directory containing `([a-zA-Z0-9\-:]*)\.pc'", 0, 'pkgconfig'),
        (r"Program (.*) found: NO", 0, None),
        (r"Target '[a-zA-Z0-9\-]' can't be generated as '(.*)' could not be found", 0, None),
        (r"Unable to `import (.*)`", 0, None),
        (r"Unable to find '(.*)'", 0, None),
        (r"Warning: prerequisite ([a-zA-Z:]+) [0-9\.]+ not found.", 0, 'perl'),
        (r"Warning\: no usable ([a-zA-Z0-9]+) found", 0, None),
        (r"You need ([a-zA-Z0-9\-\_]*) to build this program.", 1, None),
        (r"[Dd]ependency (.*) found: NO \(tried pkgconfig(?: and cmake)?\)", 0, 'pkgconfig'),
        (r"[Dd]ependency (.*) found: NO", 0, None),
        (r"(?:\/usr)?\/bin\/ld: cannot find (-l[a-zA-Z0-9\_]+)", 0, None),
        (r"^.*By not providing \"Find(.*).cmake\" in CMAKE_MODULE_PATH this.*$", 0, None),
        (r"^.*Could not find a package configuration file provided by \"(.*)\".*$", 0, None),
        (r"^.*\"(.*)\" with any of the following names.*$", 0, None),
        (r"[Cc]hecking for (.*) (?:support|development files|with pkg-config)?\.\.\. [Nn]o", 0, None),
        (r"[Cc]hecking pkg-config for (.*?)\.\.\. [Nn]o", 0, 'pkgconfig'),
        (r"checking (.*?)\.\.\. no", 0, None),
        (r"checking for (.*) in default path\.\.\. not found", 0, None),
        (r"checking for (.*)... configure: error", 0, None),
        (r"checking for (.*?)\.\.\. no", 0, None),
        (r"checking for [a-zA-Z0-9\_\-]+ in (.*?)\.\.\. no", 0, None),
        (r"checking for library containing (.*)... no", 0, None),
        (r"checking for perl module ([a-zA-Z:]+) [0-9\.]+... no", 0, 'perl'),
        (r"configure: error: (?:pkg-config missing|Unable to locate) (.*)", 0, None),
        (r"configure: error: ([a-zA-Z0-9]+) (?:is required to build|not found)", 0, None),
        (r"configure: error: Cannot find (.*)\. Make sure", 0, None),
        (r"fatal error\: (.*)\: No such file or directory", 0, None),
        (r"make: ([a-zA-Z0-9].+): (?:Command not found|No such file or directory)", 0, None),
        (r"meson\.build\:[\d]+\:[\d]+\: ERROR: C(?: shared or static)? library \'(.*)\' not found", 0, None),
        (r"there is no package called ['‘]([a-zA-Z0-9\-\.]*)['’]", 0, 'R'),
        (r"unable to execute '([a-zA-Z\-]*)': No such file or directory", 0, None),
        (r"warning: failed to load external entity \"(/usr/share/sgml/docbook/xsl-stylesheets)/.*\"", 0, None),
        (r"which\: no ([a-zA-Z\-]*) in \(", 0, None),
        (r"you may need to install the ([a-zA-Z0-9_\-:\.]*) module", 0, 'perl'),
        (r"(a-zA-Z0-9\-) not found (re-run dependencies script to install)", 0, None),
        (r"error: ([a-zA-Z\-]*)invalid attempt.*in symbol.*", 0, "flags"),
        (r"(CMake Error .* CMakeLists.txt).*", 0, "cmake"),
        (r"Plugin ([a-zA-Z\-.:]+):([0-9.]+) or one of its dependencies could not be resolved", 0, 'java-plugin'),
        (r"Unable to generate requires on unresolvable artifacts: ([a-zA-Z0-9-.:]+(, ){0,1}){1,}", 0, 'java-plugins'),
        (r"Could not resolve dependencies for project ([a-zA-Z.:]+):jar:([0-9.]+): Cannot access ([a-zA-Z-]+)"
         r" \([a-zA-Z0-9.://-]+\) in offline mode and the artifact ([a-zA-Z.\-:]+):jar:([0-9.]+) has not been"
         r" downloaded from it before", 0, 'java-jar'),
    ]
    cmake_params = [
        r"enable .*or +disable +([-_A-Z]+)",
        r"set +([-_A-Z]+) false"
    ]

    patterns = [
        # Patterns for matching files, format is a tuple as follows:
        # (<raw pattern>, <package>, <optional replacement>, <optional prefix>)
        # order matters, first match wins!
        (r"^/usr/share/package-licenses/.{1,}/.{1,}", "license"),
        (r"^/usr/share/man/man2", "dev"),
        (r"^/usr/share/man/man3", "dev"),
        (r"^/usr/share/man/", "man"),
        (r"^/usr/share/pkgconfig/32.*\.pc$", "dev32"),
        (r"^/usr/share/pkgconfig/", "dev"),
        (r"^/usr/share/info/", "info"),
        (r"^/usr/share/abi/", "abi"),
        (r"^/usr/share/qt5/examples/", "examples"),
        (r"^/usr/share/omf", "main", "/usr/share/omf/*"),
        (r"^/usr/share/installed-tests/", "tests"),
        (r"^/usr/libexec/installed-tests/", "tests"),
        (r"^/usr/lib/rustlib/x86_64-unknown-linux-gnu/lib/[a-zA-Z0-9._+-]+\.rlib", "lib",
         "/usr/lib/rustlib/x86_64-unknown-linux-gnu/lib/*.rlib"),
        (r"^/usr/lib/rustlib/x86_64-unknown-linux-gnu/analysis/[a-zA-Z0-9._+-]+\.json", "lib",
         "/usr/lib/rustlib/x86_64-unknown-linux-gnu/analysis/*.json"),
        (r"^/usr/share/clear/optimized-elf/bin", "bin", "/usr/share/clear/optimized-elf/bin*"),
        (r"^/usr/share/clear/optimized-elf/exec", "libexec", "/usr/share/clear/optimized-elf/exec*"),
        (r"^/usr/share/clear/optimized-elf/lib", "lib", "/usr/share/clear/optimized-elf/lib*"),
        (r"^/usr/share/clear/optimized-elf/other", "lib", "/usr/share/clear/optimized-elf/other*"),
        (r"^/usr/share/clear/optimized-elf/test", "tests", "/usr/share/clear/optimized-elf/test*"),
        (r"^/usr/share/clear/optimized-elf/", "lib"),
        (r"^/usr/share/clear/filemap/", "filemap"),
        (r"^/usr/lib64/openmpi/bin/", "openmpi"),
        (r"^/usr/lib64/openmpi/share", "openmpi"),
        (r"^/usr/lib64/openmpi/include/", "dev"),
        (r"^/usr/lib64/openmpi/lib/[a-zA-Z0-9._+-]*\.so$", so_dest_ompi),
        (r"^/usr/lib64/openmpi/lib/[a-zA-Z0-9._+-]*\.a$", "staticdev"),
        (r"^/usr/lib64/openmpi/lib/[a-zA-Z0-9._+-]*\.so\.", "openmpi"),
        (r"^/usr/lib64/openmpi/lib/python3.*/", "openmpi"),
        (r"^/usr/lib64/openmpi/lib/", "dev"),
        (r"^/usr/lib/[a-zA-Z0-9._+-]*\.so\.", "plugins"),
        (r"^/usr/lib64/[a-zA-Z0-9._+-]*\.so\.", "lib"),
        (r"^/usr/lib32/[a-zA-Z0-9._+-]*\.so\.", "lib32"),
        (r"^/usr/lib64/lib(asm|dw|elf)-[0-9.]+\.so", "lib"),
        (r"^/usr/lib64/libkdeinit5", "lib"),
        (r"^/usr/lib32/lib(asm|dw|elf)-[0-9.]+\.so", "lib32"),
        (r"^/usr/lib64/haswell/[a-zA-Z0-9._+-]*\.so\.", "lib"),
        (r"^/usr/lib64/gobject-introspection/", "lib"),
        (r"^/usr/libexec/", "libexec"),
        (r"^/usr/share/gir-[0-9\.]+/[a-zA-Z0-9._+-]*\.gir", "data", "/usr/share/gir-1.0/*.gir"),
        (r"^/usr/share/cmake/", "data", "/usr/share/cmake/*"),
        (r"^/usr/share/cmake-3.1/", "data", "/usr/share/cmake-3.1/*"),
        (r"^/usr/share/cmake-3.7/", "data", "/usr/share/cmake-3.7/*"),
        (r"^/usr/share/cmake-3.8/", "data", "/usr/share/cmake-3.8/*"),
        (r"^/usr/share/cmake-3.6/", "data", "/usr/share/cmake-3.6/*"),
        (r"^/usr/share/girepository-1\.0/.*\.typelib\$", "data", "/usr/share/girepository-1.0/*.typelib"),
        (r"^/usr/include/", "dev"),
        (r"^/usr/lib64/girepository-1.0/", "data"),
        (r"^/usr/share/cmake/", "dev"),
        (r"^/usr/lib/cmake/", "dev"),
        (r"^/usr/lib64/cmake/", "dev"),
        (r"^/usr/lib32/cmake/", "dev32"),
        (r"^/usr/lib/qt5/mkspecs/", "dev"),
        (r"^/usr/lib64/qt5/mkspecs/", "dev"),
        (r"^/usr/lib32/qt5/mkspecs/", "dev32"),
        (r"^/usr/lib/qt5/", "lib"),
        (r"^/usr/lib64/qt5/", "lib"),
        (r"^/usr/lib32/qt5/", "lib32"),
        (r"^/usr/lib/[a-zA-Z0-9._+-]*\.so$", so_dest),
        (r"^/usr/lib64/libkdeinit5_[a-zA-Z0-9._+-]*\.so$", "lib"),
        (r"^/usr/lib32/libkdeinit5_[a-zA-Z0-9._+-]*\.so$", "lib32"),
        (r"^/usr/lib64/[a-zA-Z0-9._+-]*\.so$", so_dest),
        (r"^/usr/lib32/[a-zA-Z0-9._+-]*\.so$", so_dest + '32'),
        (r"^/usr/lib64/glibc-hwcaps/x86-64-v[0-9]+/[a-zA-Z0-9._+-]*\.so$", so_dest),
        (r"^/usr/lib64/haswell/avx512_1/[a-zA-Z0-9._+-]*\.so$", so_dest),
        (r"^/usr/lib64/haswell/[a-zA-Z0-9._+-]*\.so$", so_dest),
        (r"^/usr/lib64/haswell/avx512_1/[a-zA-Z0-9._+-]*\.so$", so_dest),
        (r"^/usr/lib/[a-zA-Z0-9._+-]*\.a$", "staticdev"),
        (r"^/usr/lib64/[a-zA-Z0-9._+-]*\.a$", "staticdev"),
        (r"^/usr/lib32/[a-zA-Z0-9._+-]*\.a$", "staticdev32"),
        (r"^/usr/lib/haswell/[a-zA-Z0-9._+-]*\.a$", "staticdev"),
        (r"^/usr/lib64/glibc-hwcaps/x86-64-v[0-9]+/[a-zA-Z0-9._+-]*\.a$", "staticdev"),
        (r"^/usr/lib64/haswell/[a-zA-Z0-9._+-]*\.a$", "staticdev"),
        (r"^/usr/lib64/haswell/avx512_1/[a-zA-Z0-9._+-]*\.a$", "staticdev"),
        (r"^/usr/lib32/haswell/[a-zA-Z0-9._+-]*\.a$", "staticdev32"),
        (r"^/usr/lib/pkgconfig/[a-zA-Z0-9._+-]*\.pc$", "dev"),
        (r"^/usr/lib64/pkgconfig/[a-zA-Z0-9._+-]*\.pc$", "dev"),
        (r"^/usr/lib32/pkgconfig/[a-zA-Z0-9._+-]*\.pc$", "dev32"),
        (r"^/usr/lib64/glibc-hwcaps/x86-64-v[0-9]+/[a-zA-Z0-9._+-]*\.pc$", "dev"),
        (r"^/usr/lib64/haswell/pkgconfig/[a-zA-Z0-9._+-]*\.pc$", "dev"),
        (r"^/usr/lib64/haswell/avx512_1/pkgconfig/[a-zA-Z0-9._+-]*\.pc$", "dev"),
        (r"^/usr/lib/[a-zA-Z0-9._+-]*\.la$", "dev"),
        (r"^/usr/lib64/[a-zA-Z0-9._+-]*\.la$", "dev"),
        (r"^/usr/lib32/[a-zA-Z0-9._+-]*\.la$", "dev32"),
        (r"^/usr/lib/[a-zA-Z0-9._+-]*\.prl$", "dev"),
        (r"^/usr/lib64/[a-zA-Z0-9._+-]*\.prl$", "dev"),
        (r"^/usr/lib32/[a-zA-Z0-9._+-]*\.prl$", "dev32"),
        (r"^/usr/share/aclocal/[a-zA-Z0-9._+-]*\.ac$", "dev", "/usr/share/aclocal/*.ac"),
        (r"^/usr/share/aclocal/[a-zA-Z0-9._+-]*\.m4$", "dev", "/usr/share/aclocal/*.m4"),
        (r"^/usr/share/aclocal-1.[0-9]+/[a-zA-Z0-9._+-]*\.ac$", "dev", "/usr/share/aclocal-1.*/*.ac"),
        (r"^/usr/share/aclocal-1.[0-9]+/[a-zA-Z0-9._+-]*\.m4$", "dev", "/usr/share/aclocal-1.*/*.m4"),
        (r"^/usr/share/doc/" + re.escape(pkg_name) + "/", "doc", "/usr/share/doc/" + re.escape(pkg_name) + "/*"),
        (r"^/usr/share/doc/", "doc"),
        (r"^/usr/share/gtk-doc/html", "doc"),
        (r"^/usr/share/help", "doc"),
        (r"^/usr/share/info/", "doc", "/usr/share/info/*"),
        # now a set of catch-all rules
        (r"^/lib/systemd/system/", "services"),
        (r"^/lib/systemd/user/", "services"),
        (r"^/usr/lib/systemd/system/", "services"),
        (r"^/usr/lib/systemd/user/", "services"),
        (r"^/usr/lib/udev/rules.d", "config"),
        (r"^/usr/lib/modules-load.d", "config"),
        (r"^/usr/lib/tmpfiles.d", "config"),
        (r"^/usr/lib/sysusers.d", "config"),
        (r"^/usr/lib/sysctl.d", "config"),
        (r"^/usr/share/", "data"),
        (r"^/usr/lib/perl5/", "perl", "/usr/lib/perl5/*"),
        # finally move any dynamically loadable plugins (not
        # perl/python/etc.. extensions) into lib package
        (r"^/usr/lib/.*/[a-zA-Z0-9._+-]*\.so", "lib"),
        (r"^/usr/lib64/.*/[a-zA-Z0-9._+-]*\.so", "lib"),
        (r"^/usr/lib32/.*/[a-zA-Z0-9._+-]*\.so", "lib32"),
        # locale data gets picked up via file_is_locale
        (r"^/usr/share/locale/", "ignore")]

    def __init__(self):
        self.failed_commands = {}
        self.failed_flags = {}
        self.ignored_commands = {}
        self.gems = {}
        self.qt_modules = {}
        self.cmake_modules = {}

    def setup_patterns(self, path=None):
        """Read each pattern configuration file and assign to the appropriate variable."""
        read_pattern_conf("ignored_commands", self.ignored_commands, list_format=True, path=path)
        read_pattern_conf("failed_commands", self.failed_commands, path=path)
        read_pattern_conf("failed_flags", self.failed_flags, path=path)
        read_pattern_conf("gems", self.gems, path=path)
        read_pattern_conf("qt_modules", self.qt_modules, path=path)
        read_pattern_conf("cmake_modules", self.cmake_modules, path=path)


configuration = BuildConfig()
