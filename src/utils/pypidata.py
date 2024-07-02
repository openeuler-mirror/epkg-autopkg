#!/usr/bin/env python3

import os
import sys
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
