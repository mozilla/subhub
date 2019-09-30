#!/usr/bin/env bash

command -v git >/dev/null 2>&1 || { 
    echo >&2 "git is required not installed.  Aborting."; 
    exit 1; 
}

readonly NR_LAMBDA_DIRECTORY='nr-lambda'

function get_nr(){
    if [ -d "$NR_LAMBDA_DIRECTORY" ]; then
        cd "${NR_LAMBDA_DIRECTORY}"
        git checkout master
        git pull
    else
        git clone https://github.com/newrelic/nr-lambda-onboarding.git "${NR_LAMBDA_DIRECTORY}"
    fi

    cd "${NR_LAMBDA_DIRECTORY}"
    chmod +x newrelic-cloud
}

get_nr