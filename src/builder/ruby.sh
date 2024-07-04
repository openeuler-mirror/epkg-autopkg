#!/usr/bin/env bash


function prep() {
    cd  /root/workspace
}

function build() {
    if [ -f *.gemspec ]; then
      gem build *.gemspec
    fi
    gem install
}

function install() {
    rm -rf /opt/buildroot
    mkdir /opt/buildroot
    cp -r usr/ /opt/buildroot
}