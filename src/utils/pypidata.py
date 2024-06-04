#!/usr/bin/env python3

import json
import os
import subprocess
import sys
import tempfile
import pycurl
from io import BytesIO
from src.log import logger


def do_curl(url, dest=None, post=None, is_fatal=False):
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
    c.setopt(c.URL, url)
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
            logger.error("Unable to fetch {}: {}".format(url, e))
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


def pip_env():
    """Generate a copy of os.environ appropriate for pip."""
    env = os.environ.copy()
    env["PYTHON_KEYRING_BACKEND"] = "keyring.backends.null.Keyring"
    return env


def pkg_search(name):
    """Query the pypi json API for name and return True if found."""
    query = f"https://pypi.org/pypi/{name}/json/"
    resp = do_curl(query)
    if resp is not None:
        return True
    else:
        return False


def get_pypi_name(name, miss=False):
    """Try and verify the pypi name for a given package name."""
    # normalize the name for matching as pypi is case insensitve for search
    name = name.lower().replace('-', '_')
    # Common case is the name and the pypi name match
    if pkg_search(name):
        return name
    # Maybe we have a prefix
    for prefix in ["pypi_", "python_"]:
        if name.startswith(prefix):
            name = name[len(prefix):]
            if pkg_search(name):
                return name
    # Some cases where search fails (Sphinx)
    # Just try the name we were given
    if miss:
        return ""
    return name


def _print_command_error(cmd, proc):
    if isinstance(cmd, list):
        cmd = " ".join(cmd)
    logger.error(f"Command `{cmd}` failed:")
    for line in proc.stderr.decode('utf-8', errors='surrogateescape').splitlines():
        logger.error(line)


def get_pypi_metadata(name):
    """Get metadata for a pypi package."""
    show = []
    # Create virtenv to do the pip install (needed for pip show)
    with tempfile.TemporaryDirectory() as tdir:
        cmd = ["virtualenv", "--no-periodic-update", tdir]
        proc = subprocess.run(cmd, capture_output=True)
        if proc.returncode != 0:
            _print_command_error(cmd, proc)
            return ""
        cmd = f"source bin/activate && pip install {name.removeprefix('pypi_')}"
        proc = subprocess.run(cmd, cwd=tdir, shell=True, capture_output=True,
                              env=pip_env())
        if proc.returncode != 0:
            _print_command_error(cmd, proc)
            return ""
        cmd = f"source bin/activate &> /dev/null && pip show {name.removeprefix('pypi_')}"
        proc = subprocess.run(cmd, cwd=tdir, shell=True, capture_output=True,
                              env=pip_env())
        if proc.returncode != 0:
            _print_command_error(cmd, proc)
            return ""
        show = proc.stdout.decode('utf-8', errors='surrogateescape').splitlines()
    # Parse pip show for relevent information
    metadata = {}
    for line in show:
        if line.startswith("Name: "):
            # 'Name: pypi-name'
            # normalize names -> lowercase and dash to underscore
            metadata["name"] = line.split()[1].lower().replace('-', '_')
        elif line.startswith("Summary: "):
            # 'Summary: <description of the package>'
            try:
                metadata["summary"] = line.split(maxsplit=1)[1]
            except IndexError:
                # No Summary (haven't seen this case before though)
                metadata["summary"] = ""
        elif line.startswith("Requires: "):
            # 'Requires: dep1, dep2
            # normalize names -> lowercase and dash to underscore
            try:
                reqs = [item.strip().lower().replace('-', '_') for item in line.split(maxsplit=1)[1].split(",")]
            except IndexError:
                # No Requires
                reqs = []
            metadata["requires"] = reqs

    return json.dumps(metadata)


def main():
    """Standalone pypi metadata query entry point."""
    pkg_name = sys.argv[1]
    pypi_name = get_pypi_name(pkg_name)
    if not pypi_name:
        print(f"Couldn't find {pkg_name} in pypi")
        sys.exit(1)
    pypi_metadata = get_pypi_metadata(pypi_name)
    print(pypi_metadata)


if __name__ == '__main__':
    main()
