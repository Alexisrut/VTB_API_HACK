#!/bin/bash

# Wrapper script for unified Docker management
# This script calls the main docker.sh script in the docker/ directory

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
"$SCRIPT_DIR/docker/docker.sh" "$@"

