#!/usr/bin/env bash

if [[ $TRAVIS_EVENT_TYPE == cron ]]; then
  exit 1;
fi

case "$TRAVIS_BRANCH" in
'feature/staging')
    DEPLOY_ENV=staging
    ;;
'release/prod-test')
    DEPLOY_ENV=prod-test
    doit deploy
    ;;
'release/prod')
    DEPLOY_ENV=prod
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