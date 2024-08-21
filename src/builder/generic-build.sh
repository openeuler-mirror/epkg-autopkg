#!/usr/bin/env bash

# refers:
# /c/cci/design_meeting/autopkg/design_meeting_240513/autopkg.md
# /c/cci/design_meeting/autopkg/240612/build-system.md
# /c/os/NixOS/nixpkgs/pkgs/stdenv/generic/setup.sh
# /c/os/NixOS/nixpkgs/pkgs/stdenv/generic/default-builder.sh
# /c/os/NixOS/nixpkgs/pkgs/build-support/setup-hooks/multiple-outputs.sh

# Check if the build_system parameter is provided
if [ -z "$1" ]; then
  echo "Usage: $0 <build_system>"
  exit 1
fi

# Set the build_system variable based on the provided argument
build_system="$1"

# Source the required scripts
source /root/skel.sh
source /root/"$build_system".sh
# source package/flags.sh
# source package/phase.sh
build_requires=`cat /root/package.yaml |shyaml get-value build_requires |sed 's/^[ \t-]*//'`
if [ "${#build_requires}" -ne 0 ]; then
    IFS=$'\n' read -rd '' -a packages <<<"$build_requires"
    yum install -y ${packages[*]}
fi
makeFlags=`cat /root/package.yaml |shyaml get-value makeFlags`
cmakeFlags=`cat /root/package.yaml |shyaml get-value cmakeFlags`
configureFlags=`cat /root/package.yaml |shyaml get-value configureFlags`

# Prepare the build environment
prep

# Choose the appropriate build system
if [ "$build_system" = "autotools" ]; then
  configure
elif [ "$build_system" = "cmake" ]; then
  cmake_build
else
  echo "Unsupported build system: $build_system"
  exit 1
fi

# Build and install
build
install

# Check if the build was successful
if [ $? -eq 0 ]; then
  echo "build success"
else
  echo "build failed"
fi
