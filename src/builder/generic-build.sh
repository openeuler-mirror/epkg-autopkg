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
source /root/params_parser.sh
source /root/phase.sh

# Check if the build was successful
if [ $? -eq 0 ]; then
  echo "build success"
else
  echo "build failed"
fi