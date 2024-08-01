# -*- encoding=utf-8 -*-
# SPDX-License-Identifier: MIT
# Copyright (c) 2017 Shintaro Kaneko. All rights reserved.

import logging
from logging.handlers import TimedRotatingFileHandler, RotatingFileHandler
from threading import Lock
from pathlib import Path

"""
how to use:
    example for dag server:
        init log in dag/__init__.py,
        then import src.dag log in your file,
        you can use log.info("xxxx") output your log.
"""


class Logger:
    def __init__(self, ms, log_root_dir="/tmp/log/", console=False):
        self.mutex = Lock()
        self.console = console
        log_dir = "%s/%s/" % (log_root_dir, ms)
        log_path = Path(log_dir)

        if not log_path.is_dir():
            log_path.mkdir(parents=True)

        self.log_name = "%s/%s.log" % (log_path, ms)
        self.log_format = logging.Formatter(
                "%(asctime)s %(levelname)s %(filename)s [%(lineno)s]: %(message)s")

    def _create_logger(self):
        _logger = logging.getLogger(__name__)
        _logger.setLevel(level=logging.INFO)

        return _logger

    def _console_handler(self):
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(self.log_format)

        return console_handler

    def _time_rotate_handler(self):
        time_rotate_handler = TimedRotatingFileHandler(
                filename=self.log_name, when='MIDNIGHT', interval=1, backupCount=7)
        time_rotate_handler.setFormatter(self.log_format)

        return time_rotate_handler

    def _rotate_handler(self):
        rotate_handler = RotatingFileHandler(
                filename=self.log_name, maxBytes=200 * 1024 * 1024, backupCount=10)
        rotate_handler.setFormatter(self.log_format)

        return rotate_handler

    def get_logger(self):
        logger = self._create_logger()
        with self.mutex:
            if self.console:
                logger.addHandler(self._console_handler())
            logger.addHandler(self._rotate_handler())

        return logger

    def add_console_handle(self, logger):
        with self.mutex:
            logger.addHandler(self._console_handler())


logger = Logger("autopkg", console=True).get_logger()
