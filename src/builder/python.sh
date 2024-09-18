#!/usr/bin/env bash

prep() {
  # shellcheck disable=SC2164
  cd /root/workspace
  pip install setuptools wheel
  pip install -r requirements.txt
}

build() {
  python3 setup.py bdist_wheel
}

install() {
    rm -rf /opt/buildroot
    mkdir /opt/buildroot
    cp dist/*.whl /opt/buildroot
}