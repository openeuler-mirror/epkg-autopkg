#!/usr/bin/env bash

function prep() {
  # shellcheck disable=SC2164
  cd /root/workspace
}

function configure() {
    if [ ! -f "configure" ]; then
      autoreconf -vif
    fi
    ./configure ${configureFlags}
}

function build() {
    make -j8 ${makeFlags}
}

function install() {
    rm -rf /opt/buildroot
    mkdir /opt/buildroot
    make install DESTDIR=/opt/buildroot
}