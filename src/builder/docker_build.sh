#!/usr/bin/env bash

# SPDX-License-Identifier: MIT
# Copyright (c) 2017 Shintaro Kaneko. All rights reserved.

# Define variables
container_name="autopkg_build"
image_name="autopkg"
image_tag="latest"
build_system=""
download_path=""
logfile="build.log"
error_log_file="error-build.log"
scripts_path=""

# 定义选项处理函数
process_options() {
    while getopts ":b:d:s::" opt; do
        case $opt in
            b)
                build_system=$OPTARG
                ;;
            d)
                download_path=$OPTARG
                ;;
            s)
                scripts_path=$OPTARG
                ;;
            \?)
                echo "Invalid option: -$OPTARG" >&2
                exit 1
                ;;
            :)
                echo "Option -$OPTARG requires an argument." >&2
                exit 1
                ;;
        esac
    done
    shift $((OPTIND -1 ))
}

# 处理选项
process_options "$@"

# 检查必须的参数
if [ -z "$build_system" ] || [ -z "$download_path" ] || [ -z "$scripts_path" ]; then
    echo "Usage: $0 -b <build_system> -d <download_path> -s <scripts_path>"
    exit 1
fi

# Functions
remove_docker_container() {
    echo "Removing old Docker container..."
    container_id=$(docker ps -a --format "{{.ID}} {{.Names}}" | grep "$container_name" | awk '{print $1}')
    if [ -n "$container_id" ]; then
        docker rm -f "$container_id"
    fi
}

create_container() {
    echo "Creating Docker container..."
    docker run -dti --privileged --name="$container_name" "$image_name:$image_tag" /bin/bash -D -e
    container_id=$(docker ps --format "{{.ID}} {{.Names}}" | grep "$container_name" | awk '{print $1}')
    if [ -z "$container_id" ]; then
        echo "Failed to get Docker container ID."
        exit 3
    fi
    echo "Container ID: $container_id"
}

copy_source_into_container() {
    echo "Copying source code into container..."
    docker cp "$download_path/workspace" "$container_id:/root"
    docker cp "$download_path/package.yaml" "$container_id:/root"
    chmod 755 "$scripts_path"/*.sh
    docker cp "$scripts_path/$build_system.sh" "$container_id:/root"
    docker cp "$scripts_path/generic-build.sh" "$container_id:/root"
}

run_build() {
    echo "Running build in container..."
    docker exec "$container_id" /root/generic-build.sh "$build_system" > "$download_path/$logfile" 2>&1
    if [ $? -eq 0 ]; then
        echo "Build finished successfully."
    else
        echo "Build failed. Check logs for details."
    fi
}

check_build_log() {
    log_path="$download_path/$logfile"
    if [ -f "$log_path" ]; then
        if [ ! -s "$log_path" ]; then
            echo "Empty log file from Docker: $container_id"
            exit 3
        fi
    else
        echo "Log file does not exist: $log_path"
        exit 3
    fi
    echo "Build log written successfully."
}

install_buildrequires() {
    build_requires=`cat "$download_path"/package.yaml |shyaml get-value buildRequires |sed 's/^[ \t-]*//'`
    if [ "${#build_requires}" -ne 0 ]; then
        IFS=$'\n' read -rd '' -a packages <<<"$build_requires"
        docker exec -ti "$container_id" yum install ${packages[*]}
    fi
}

# Main script
docker_build() {
    remove_docker_container
    create_container
    install_buildrequires
    copy_source_into_container
    run_build
    check_build_log
}
docker_build