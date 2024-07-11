#!/usr/bin/env bash

function prep() {
  # shellcheck disable=SC2164
  cd /root/workspace
}

function build() {
  python3 setup.py bdist_wheel
}

function install() {
    rm -rf /opt/buildroot
    mkdir /opt/buildroot
    cp dist/*.whl /opt/buildroot
}