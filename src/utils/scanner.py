# SPDX-License-Identifier: MIT
# Copyright (c) 2017 Shintaro Kaneko. All rights reserved.


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
             "Copying and distribution of",
             "Free Software Foundation, Inc.",
             "are permitted in any",
             "README",
             "notice and this notice",
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
            # description > 80 characters.
            break
        if not section and len(line) > 2:
            # Found the first paragraph
            section = True
        if section:
            # find description
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
        if line.startswith("%"):
            section = False
        if line.startswith("#"):
            continue

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


def summary_from_pkgconfig(pkgfile):
    """Parse pkgconfig files for Description: lines."""
    try:
        with open_auto(pkgfile, "r") as pkgfd:
            lines = pkgfd.readlines()
    except FileNotFoundError:
        return

    for line in lines:
        if line.startswith("Summary:"):
            return line[8:]


def summary_from_R(pkgfile):
    """Parse DESCRIPTION file for Title: lines."""
    try:
        with open_auto(pkgfile, "r") as pkgfd:
            lines = pkgfd.readlines()
    except FileNotFoundError:
        return

    for line in lines:
        if line.startswith("Title:"):
            return line[7:]


def scan_for_meta(dirn):
    """Scan the project directory for things we can use to guess a description and summary."""
    description = default_description
    summary = default_summary
    for name in os.listdir(dirn):
        file_path = os.path.join(dirn, name)
        if os.path.isdir(file_path):
            continue
        if name.lower().endswith(".pdf"):
            continue
        if name.lower().endswith(".spec"):
            description = description_from_spec(os.path.join(dirn, name))
        elif name.lower().endswith("pkg-info"):
            description = description_from_pkginfo(os.path.join(dirn, name))
        elif name.lower().endswith("meta.yml"):
            description = description_from_pkginfo(os.path.join(dirn, name))
        elif name.lower().endswith("description"):
            description = description_from_pkginfo(os.path.join(dirn, name))
        elif name.lower().startswith("readme"):
            description = description_from_readme(os.path.join(dirn, name))
        if name.lower().endswith(".pc") or name.lower().endswith(".spec"):
            summary = summary_from_pkgconfig(os.path.join(dirn, name))
        elif name.startswith("DESCRIPTION"):
            summary = summary_from_R(os.path.join(dirn, name))
        elif name.lower().endswith(".pc.in"):
            summary = summary_from_pkgconfig(os.path.join(dirn, name))
    if "doc" in os.listdir(dirn) and (description == default_description or summary == default_summary):
        return scan_for_meta(os.path.join(dirn, "doc"))
    return {"summary": summary, "description": description}


def load_specfile(specfile, description, summary):
    """Load specfile with parse results."""
    specfile.default_desc = "\n".join(description) if description else default_description
    specfile.default_sum = summary[0] if summary else default_summary


def scan_for_license(path):
    # TODO(method better)
    result = "MIT"
    targets = ["copyright",
               "copyright.txt",
               "apache-2.0",
               "artistic.txt",
               "libcurllicense",
               "gpl.txt",
               "gpl2.txt",
               "gplv2.txt",
               "notice",
               "copyrights",
               "about_bsd.txt"]
    target_pat = re.compile(r"^((copying)|(licen[cs]e)|(e[dp]l-v\d+))|(licen[cs]e)(\.(txt|xml))?$")
    files = os.listdir(path)
    for file in files:
        if file.lower() in targets or target_pat.search(file.lower()):
            with open_auto(os.path.join(path, file)) as f:
                content = f.read().replace(os.linesep, "").lower()
            if "lesser general public license" in content:
                base_license = "LGPL"
            elif "general public license" in content:
                base_license = "GPL"
            elif "apache license" in content:
                base_license = "Apache"
            elif "mit license" in content:
                base_license = "MIT"
            else:
                base_license = "BSD"
            if "version 2.0" in content:
                version = "-2.0"
            elif "version 3.0" in content:
                version = "-3.0"
            else:
                version = ""
            result = f"{base_license}{version}"
    return result
