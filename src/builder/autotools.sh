#!/usr/bin/env bash

prep() {
  # shellcheck disable=SC2164
  # TODO:
  # - framework should auto cd to source code dir
  # - specific package phase script can override with pushd/popd
  cd /root/workspace
}

# TODO: rename to autotools_build()/autotools_install(), refer to /c/os/gentoo/gentoo/eclass/cmake.eclass
# TODO: add configure() phase
build() {
    if [ ! -f "configure" ]; then
        autoreconf -vif
    fi
    ./configure ${configureFlags}
    make -j8 ${makeFlags}
}

install() {
    # XXX
    rm -rf /opt/buildroot
    mkdir /opt/buildroot
    make install DESTDIR=/opt/buildroot
}
