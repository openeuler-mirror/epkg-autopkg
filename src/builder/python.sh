#!/usr/bin/env bash

function prep() {
  # shellcheck disable=SC2164
  cd /root/workplace
}

function build() {
  if [ ! -f "setup.py" ]; then
    cat >> setup.py << EOF
from setuptools import find_packages()
EOF
  fi
  python3 setup.py bdist_wheel
}

function install() {
    rm -rf /opt/buildroot
    mkdir /opt/buildroot
    cp dist/*.whl /opt/buildroot
}