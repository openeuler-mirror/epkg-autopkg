import os
import re
from src.log import logger
from src.utils.scanner import scan_for_meta, scan_for_license


class BasicParse:
    def __init__(self, source):
        self.language = ""
        self.compilation = ""
        self.url = source.url
        self.dirn = source.path
        self.version = source.version
        self.license = ""
        self.release = source.release
        self.build_commands = []
        self.install_commands = []
        self.build_requires = set()
        self.pacakge_name = source.name
        self.metadata = {}
        self.files = {}
        self.files_blacklist = set()

    def init_metadata(self):
        if self.url == "" and self.pacakge_name:
            self.url = f"https://localhost:8080/{self.pacakge_name}-0.0.1.tar.gz"
        self.metadata.setdefault("rpmGlobal", {}).setdefault("debug_package", "%{nil}")
        self.metadata["rpmGlobal"]["__strip"] = "/bin/true"
        self.metadata.setdefault("meta", scan_for_meta(self.dirn))
        self.metadata.setdefault("name", self.pacakge_name)
        self.metadata.setdefault("version", self.version)
        self.metadata.setdefault("homepage", self.url)
        self.metadata.setdefault("license", scan_for_license(self.dirn))
        self.metadata.setdefault("source", {}).setdefault("0", self.url)
        self.metadata.setdefault("release", self.release)
        self.files.setdefault("files", set())

    def clean_directories(self, root):
        """Remove directories from file list."""
        removed = False
        for pkg in self.metadata:
            if not pkg.startswith("subpackage."):
                continue
            self.files[pkg], _rem = self._clean_dirs(root, self.files[pkg])
            if _rem:
                removed = True

        return removed

    def _clean_dirs(self, root, files):
        """Do the work to remove the directories from the files list."""
        res = set()
        removed = False

        directive_re = re.compile(r"(%\w+(\([^\)]*\))?\s+)(.*)")
        for f in files:
            # skip the files with directives at the beginning, including %doc
            # and %dir directives.
            # autospec does not currently support adding empty directories to
            # the file list by prefixing "%dir". Regardless, skip these entries
            # because if they exist at this point it is intentional (i.e.
            # support was added).
            if directive_re.match(f):
                res.add(f)
                continue

            path = os.path.join(root, f.lstrip("/"))
            if os.path.isdir(path) and not os.path.islink(path):
                logger.warning("Removing directory {} from file list".format(f))
                self.files_blacklist.add(f)
                removed = True
            else:
                res.add(f)

        return res, removed

    def merge_files(self):
        self.metadata.update(self.files)
