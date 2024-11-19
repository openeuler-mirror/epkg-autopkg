#!/usr/bin/env bash


make_build() {
  if [ -n "${makePath}" ]; then
    pushd ${makePath}
  fi
  make -j8 ${makeFlags}
  if [ $? -eq 0 ]; then
    echo "make finished"
  else
    echo "make failed"
    exit 1
  fi
}

make_install() {
  rm -rf /opt/buildroot
  mkdir /opt/buildroot
  make install DESTDIR=/opt/buildroot
}