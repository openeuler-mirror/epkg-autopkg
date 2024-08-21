#!/usr/bin/env bash


prep() {
    cd /root/workspace
}

build() {
    if [ -f *.gemspec ]; then
      gem build *.gemspec
    fi
    gem install
}

install() {
    rm -rf /opt/buildroot
    mkdir /opt/buildroot
    cp -r usr/ /opt/buildroot
}