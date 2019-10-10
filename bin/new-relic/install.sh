#!/usr/bin/env bash

command -v git >/dev/null 2>&1 || {
    echo >&2 "git is required not installed.  Aborting.";
    exit 1;
}

readonly NR_LAMBDA_DIRECTORY='nr-lambda'
readonly SCRIPT_DIRECTORY="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
readonly NR_LAMBDA_PATH="${SCRIPT_DIRECTORY}/${NR_LAMBDA_DIRECTORY}"

function get_nr(){
    if [ -d "${NR_LAMBDA_PATH}" ]; then
        pushd "${NR_LAMBDA_PATH}"
        echo "updating repo at ${NR_LAMBDA_PATH}"
        git checkout master
        git fetch origin
        git reset --hard origin/master
        echo "updated repo at ${NR_LAMBDA_PATH}"
        popd

    else
        echo "cloning nr-lambda-onboarding to ${NR_LAMBDA_PATH}"
        git clone https://github.com/newrelic/nr-lambda-onboarding.git "${NR_LAMBDA_PATH}"
        echo "cloned nr-lambda-onboarding to ${NR_LAMBDA_PATH}"
    fi

    chmod +x "${NR_LAMBDA_PATH}/newrelic-cloud"
}

get_nr
