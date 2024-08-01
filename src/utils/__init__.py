# SPDX-License-Identifier: MIT
# Copyright (c) 2017 Shintaro Kaneko. All rights reserved.


from src.config import config_path

dictionary_filename = config_path + "/translate.dic"
dictionary = [line.strip() for line in open(dictionary_filename, 'r')]
os_paths = None