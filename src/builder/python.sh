#!/usr/bin/env bash

prep() {
  # shellcheck disable=SC2164
  cd /root/workspace
}

build() {
  python3 setup.py bdist_wheel
}

install() {
    rm -rf /opt/buildroot
    mkdir /opt/buildroot
    cp dist/*.whl /opt/buildroot
}