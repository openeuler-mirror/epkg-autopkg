#!/usr/bin/env bash


build() {
  if [ "$build_system" = "autotools" ]; then
    autotools_build
  fi
  if [ "$build_system" = "cmake" ]; then
    cmake_build
  fi
  if [ "$build_system" = "meson" ]; then
    meson_build
  fi
  if [ "$build_system" = "python" ]; then
    python_build
  fi
  if [ "$build_system" = "ruby" ]; then
    ruby_build
  fi
  if [ "$build_system" = "maven" ]; then
    maven_build
  fi
  if [ "$build_system" = "go" ]; then
    go_build
  fi
  if [ "$build_system" = "autogen" ]; then
    autogen_build
  fi
}

install() {
  if [ "$build_system" = "autotools" ]; then
    autotools_install
  fi
  if [ "$build_system" = "cmake" ]; then
    cmake_install
  fi
  if [ "$build_system" = "meson" ]; then
    meson_install
  fi
  if [ "$build_system" = "python" ]; then
    python_install
  fi
  if [ "$build_system" = "ruby" ]; then
    ruby_install
  fi
  if [ "$build_system" = "maven" ]; then
    maven_install
  fi
  if [ "$build_system" = "go" ]; then
    go_install
  fi
  if [ "$build_system" = "autogen" ]; then
    autogen_install
  fi
}

prep
build
install