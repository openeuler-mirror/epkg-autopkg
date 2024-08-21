#!/usr/bin/env bash

prep() {
  # shellcheck disable=SC2164
  cd /root/workspace
}

build() {
    make -j8 ${makeFlags}
}

install() {
    rm -rf /opt/buildroot
    mkdir /opt/buildroot
    make install DESTDIR=/opt/buildroot
}