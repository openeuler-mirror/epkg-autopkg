#!/usr/bin/env bash

function prep() {
  # shellcheck disable=SC2164
  cd /root/workplace
}

function configure() {
    if [ ! -f "configure" ]; then
      autoreconf -vif
    fi
    ./configure
}

function build() {
    make -j8
}

function install() {
    rm -rf /opt/buildroot
    mkdir /opt/buildroot
    make install DESTDIR=/opt/buildroot
}