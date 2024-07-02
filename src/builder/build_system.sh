#!/usr/bin/env bash

function prep() {
  cd /root/*/
}

function configure() {
    autoreconf -vif
    ./configure
}

function build() {
    ./configure
}