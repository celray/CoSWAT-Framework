#!/bin/bash 

docker buildx build --network host -t coswat --progress=plain .
