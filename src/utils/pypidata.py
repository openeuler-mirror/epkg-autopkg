#!/usr/bin/env python3

import sys
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
    except pycurl.error as e:
        if is_fatal:
            logger.error("Unable to fetch {}: {}".format(url, e))
            sys.exit(1)
        return None
    finally:
        c.close()

    # write to dest if specified
    if dest:
        with open(dest, 'wb') as fp:
            fp.write(buf.getvalue())

    return dest if dest else buf
