#!/usr/bin/env bash

prep() {
  # shellcheck disable=SC2164
  cd /root/workspace
}

cmake_build() {
  rm -rf build_cmake
  mkdir build_cmake
  # shellcheck disable=SC2164
  cd build_cmake
  cmake .. ${cmakeFlags}
}

build() {
    make -j8 ${makeFlags}
}

install() {
    rm -rf /opt/buildroot
    mkdir /opt/buildroot
    make install DESTDIR=/opt/buildroot
}