#!/bin/true

# %description
# Summary
# Group
# %description <subpackage>
#

import os
import re

from src.utils.file_util import open_auto

default_summary = "No detailed summary available"
default_description = "No detailed description available"


def skip_line(line):
    """Skip boilerplate readme lines."""
    if line.endswith("introduction"):
        return True

    skips = ["Copyright",
             "Free Software Foundation, Inc.",
             "Copying and distribution of",
             "are permitted in any",
             "notice and this notice",
             "README",
             "-*-"]
    return any(s in line for s in skips)


def description_from_readme(readme):
    """Try to pick the first paragraph or two from the readme file."""
    try:
        with open_auto(readme, "r") as f:
            lines = f.readlines()
    except FileNotFoundError:
        return

    section = False
    desc = ""
    for line in lines:
        if section and len(line) < 2 and len(desc) > 80:
            # If we are in a section and encounter a new line, break as long as
            # we already have a description > 80 characters.
            break
        if not section and len(line) > 2:
            # Found the first paragraph hopefully
            section = True
        if section:
            # Copy all non-empty lines into the description
            if skip_line(line) == 0 and len(line) > 2:
                desc = desc + line.strip() + "\n"
    return desc


def description_from_spec(spec):
    """Parse any existing RPM specfiles."""
    try:
        with open_auto(spec, 'r') as f:
            lines = f.readlines()
    except FileNotFoundError:
        return

    desc = ""
    section = False
    for line in lines:
        if line.startswith("#"):
            continue

        if line.startswith("%"):
            section = False

        desc += line if section else ""
        # Check for %description after assigning the line to specdesc so the
        # %description string is not included
        if line.endswith("%description\n"):
            section = True
    return desc


def description_from_pkginfo(pkginfo):
    """Parse existing package info files."""
    try:
        with open_auto(pkginfo, 'r') as f:
            lines = f.readlines()
    except FileNotFoundError:
        return

    desc = ""
    section = False
    for line in lines:
        if ":" in line and section:
            section = False
        desc += line if section else ""
        if line.startswith("Description:"):
            section = True

    if len(desc) > 10:
        return desc


def scan_for_description(dirn):
    """Scan the project directory for things we can use to guess a description and summary."""
    test_pat = re.compile(r"tests?")
    dirpath_seen = ""
    description = default_description
    for dirpath, dirnames, files in os.walk(dirn):
        if dirpath_seen != dirpath:
            dirpath_seen = dirpath
            dirnames[:] = [d for d in dirnames if not re.match(test_pat, d)]
        for name in files:
            if name.lower().endswith(".pdf"):
                continue
            if name.lower().endswith(".spec"):
                description_from_spec(os.path.join(dirpath, name))
            if name.lower().endswith("pkg-info"):
                description_from_pkginfo(os.path.join(dirpath, name))
            if name.lower().endswith("meta.yml"):
                description_from_pkginfo(os.path.join(dirpath, name))
            if name.lower().endswith("description"):
                description_from_pkginfo(os.path.join(dirpath, name))
            if name.lower().startswith("readme"):
                description_from_readme(os.path.join(dirpath, name))
    return description


def load_specfile(specfile, description, summary):
    """Load specfile with parse results."""
    if description:
        specfile.default_desc = "\n".join(description)
    else:
        specfile.default_desc = default_description
    if summary:
        specfile.default_sum = summary[0]
    else:
        specfile.default_sum = default_summary
