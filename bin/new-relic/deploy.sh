#!/usr/bin/env bash

set -ex

source "env.sh"
source "install.sh"

function deploy_lambda(){
    if [ -d "$NR_LAMBDA_DIRECTORY" ]; then
        cd nr-lambda
        sh newrelic-cloud set-up-lambda-integration \
            --nr-account-id "${NEW_RELIC_ACCOUNT_ID}" \
            --linked-account-name "${AWS_LINKED_ACCOUNT_NAME}" \
            --nr-api-key "${NEW_RELIC_API_KEY}" \
            --regions "${AWS_REGION}"
    else
        echo "Please run install.sh first."
    fi
}

deploy_lambda