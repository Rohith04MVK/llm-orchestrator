#!/bin/bash

for dir in *-service/; do
    image_name="${dir%-service}" 
    image_name="${image_name//\//}"
    echo "Building $image_name from $dir..."
    (cd "$dir" && docker build -t "$image_name" .)
    echo "Finished building $image_name."
done