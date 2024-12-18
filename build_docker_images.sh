#!/bin/bash

# Defining an associative array with key-value pairs
# keys are the roles and the values are the directories
declare -A build_configs=(
    ["web_server"]="Server"
    ["web_client"]="Client"
)

# Looping through the associative array
for image_tag in "${!build_configs[@]}"; do
    echo "Building docker image for ${build_configs[$image_tag]} streaming"
    docker build -t "$image_tag" --file "./${build_configs[$image_tag]}/Dockerfile.${build_configs[$image_tag]}" "./${build_configs[$image_tag]}"
done


