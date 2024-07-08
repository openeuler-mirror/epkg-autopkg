#!/usr/bin/env bash

docker run -dti --privileged --name=autopkg_build:20240620 autopkg:latest /bin/bash -D -e
container_id=$(docker ps -lq)
docker cp build_system.sh generic_build.sh "${container_id}":/root
docker cp /tmp/build.log .
if greq -q "build success" build.log; then
  echo "success"
else
  echo "failed"
fi