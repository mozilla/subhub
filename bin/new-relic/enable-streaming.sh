#!/usr/bin/env bash

set -ex

source "env.sh"
source "install.sh"


function enable_streaming(){
    if [ $# -eq 0 ]; then
        echo "usage: $1, One of more function names to enable log streaming."
    fi
    if [ -d "$NR_LAMBDA_DIRECTORY" ]; then
        cd nr-lambda
        sh newrelic-cloud stream-lambda-logs $1
    else
        echo "Please run install.sh first."
    fi
}

enable_streaming "$@"
