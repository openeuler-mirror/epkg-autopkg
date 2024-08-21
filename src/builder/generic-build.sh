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
source /root/"$build_system".sh
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

# Build and install
build
install

# Check if the build was successful
if [ $? -eq 0 ]; then
  echo "build success"
else
  echo "build failed"
fi