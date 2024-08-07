#!/usr/bin/env bash

# Check if the build_system parameter is provided
if [ -z "$1" ]; then
  echo "Usage: $0 <build_system>"
  exit 1
fi

# Set the build_system variable based on the provided argument
build_system="$1"

# Source the required scripts
source /root/skel.sh
source /root/yaml_to_vars.sh
source /root/"$build_system".sh

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