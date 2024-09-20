#!/usr/bin/env bash

prep() {
    # shellcheck disable=SC2164
    cd /root/workspace
    pip install ninja
}

build() {
    arch=`uname -m`
    meson setup . "$(arch)_compile_gnu"
    meson compile -C "$(arch)_compile_gnu" -j 8 --verbose
}

install() {
    arch=`uname -m`
    DESTDIR=/opt/buildroot meson install -C "$(arch)_compile_gnu" --no-rebuild
}