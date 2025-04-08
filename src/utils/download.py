# This file contains code derived from autospec (©clearlinux) under the GNU General Public License v3.0 (GPL-3.0).
# Original source: https://github.com/clearlinux/autospec
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.


import sys
import subprocess
import pycurl
from io import BytesIO
from src.log import logger


def do_curl(url, dest=None, post=None, is_fatal=False):
    """Perform a curl operation for `url`."""
    c = pycurl.Curl()
    c.setopt(c.FOLLOWLOCATION, True)
    c.setopt(c.URL, url)
    if post:
        c.setopt(c.POSTFIELDS, post)
    c.setopt(c.FAILONERROR, True)
    c.setopt(c.TIMEOUT, 600)
    c.setopt(c.CONNECTTIMEOUT, 10)
    c.setopt(c.LOW_SPEED_LIMIT, 1)
    c.setopt(c.SSL_VERIFYPEER, 0)
    c.setopt(c.LOW_SPEED_TIME, 10)
    c.setopt(c.SSL_VERIFYHOST, 0)
    buf = BytesIO()
    c.setopt(c.WRITEDATA, buf)
    try:
        c.perform()
    except Exception as e:
        if is_fatal:
            logger.error("can't request {}: {}".format(url, e))
            sys.exit(1)
        return None
    finally:
        c.close()

    # write to dest if specified
    if dest:
        with open(dest, 'wb') as fp:
            fp.write(buf.getvalue())

    return dest if dest else buf


def clone_code(path, url, specific_branch="master"):
    cmd = ["git", "clone", "--depth=1", "-b", specific_branch, url, path]
    subprocess.check_call(cmd)
