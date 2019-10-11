#!/usr/bin/env bash

if [ -n "$DEBUG" ]; then
    PS4=':${LINENO}+'
    set -x
fi

source "env.sh"
source "install.sh"


function enable_streaming(){
    if [ $# -eq 0 ]; then
        echo "usage: $1, One of more function names to enable log streaming."
    fi
    if [ -d "$NR_LAMBDA_DIRECTORY" ]; then
        (cd "$NR_LAMBDA_DIRECTORY" && ./newrelic-cloud stream-lambda-logs --regions "$AWS_REGION" --functions "$@")
    else
        echo "Please run install.sh first."
    fi
}

enable_streaming "$@"
