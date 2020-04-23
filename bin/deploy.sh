#!/usr/bin/env bash

if [[ $TRAVIS_EVENT_TYPE == cron ]]; then
  exit 1;
fi

case "$TRAVIS_BRANCH" in
'feature/staging')
    export DEPLOY_ENV=staging
    ;;
'release/prod-test')
    export DEPLOY_ENV=prod-test
    ;;
'release/prod')
    export DEPLOY_ENV=prod
    ;;
*)
    echo "No DEPLOY_ENV to set."
    ;;
esac

if [ -z "$DEPLOY_ENV" ]; then
      echo "Not deployinng"
else
      echo "Deploying to $DEPLOY_ENV"
      doit deploy
fi