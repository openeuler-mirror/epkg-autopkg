#!/usr/bin/env bash
# TODO(重复构建，输入容器id和修改后的phase.sh)

docker_id=$1

if [ -z "$docker_id" ]; then
  echo "Error: please input docker_id"
  exit 1
fi

docker cp phase.sh "$docker_id":/root/

docker exec $docker_id /root/generic_build.sh
