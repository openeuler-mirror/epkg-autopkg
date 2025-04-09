# Copyright (c) [2023] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#       http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.


import os
import re

default_summary = "No detailed summary available"
default_description = "No detailed description available"


def skip_line(line):
    """Skip boilerplate readme lines."""
    if line.endswith("introduction"):
        return True

    skips = ["Copyright", "Copying and distribution of", "README",
             "Free Software Foundation, Inc.", "are permitted in any",
             "notice and this notice", "-*-"]
    return any(s in line for s in skips)


def description_from_readme(readme):
    """从README文件中找到一两行用于description."""
    if not os.path.exists(readme):
        return
    with open(readme, "r", encoding="utf-8", errors="surrogateescape",) as f:
        lines = f.readlines()

    section = False
    content = ""
    for line in lines:
        if section and len(line) < 2 and len(content) > 80:
            break
        if not section and len(line) > 2:
            # Found the first paragraph
            section = True
        if section:
            # find description
            if skip_line(line) == 0 and len(line) > 2:
                content = content + line.strip() + "\n"
    return content


def description_from_spec(spec):
    """Parse any existing RPM specfiles."""
    if not os.path.exists(spec):
        return
    with open(spec, 'r', encoding="utf-8", errors="surrogateescape") as f:
        lines = f.readlines()

    desc = ""
    section = False
    for line in lines:
        if line.startswith("%"):
            section = False
        if line.startswith("#"):
            continue

        desc += line if section else ""
        if line.endswith("%description" + os.linesep):
            section = True
    return desc


def description_from_pkginfo(pkginfo):
    """Parse existing package info files."""
    if not os.path.exists(pkginfo):
        return
    with open(pkginfo, 'r', encoding="utf-8", errors="surrogateescape") as f:
        lines = f.readlines()

    desc = ""
    section = False
    for line in lines:
        if ":" in line and section:
            section = False
        desc += line if section else ""
        if line.lower().startswith("description:"):
            section = True

    if len(desc) > 10:
        return desc


def summary_from_pkgconfig(pkgfile):
    """从pkgconfig文件中读取字段"""
    if not os.path.exists(pkgfile):
        return
    with open(pkgfile, "r", encoding="utf-8", errors="surrogateescape") as pkgfd:
        lines = pkgfd.readlines()

    for line in lines:
        if line.startswith("Summary:"):
            return line[8:]


def summary_from_R(pkgfile):
    """从描述文件中抓取标题"""
    if not os.path.exists(pkgfile):
        return
    with open(pkgfile, "r", encoding="utf-8", errors="surrogateescape") as pkgfd:
        lines = pkgfd.readlines()

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
    """从spec文件中加载数据"""
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
        file_path = os.path.join(path, file)
        if os.path.isdir(file_path):
            license_files = os.listdir(file_path)
            if len(license_files) == 0:
                continue
            file_path = os.path.join(file_path, license_files[0])
        if file.lower() in targets or target_pat.search(file.lower()):
            with open(file_path, "r", encoding="utf-8", errors="surrogateescape") as f:
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
