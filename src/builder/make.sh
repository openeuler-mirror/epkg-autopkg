#!/usr/bin/env bash

function prep() {
  # shellcheck disable=SC2164
  cd /root/workspace
}

function build() {
    make -j8
}

function install() {
    rm -rf /opt/buildroot
    mkdir /opt/buildroot
    make install DESTDIR=/opt/buildroot
}