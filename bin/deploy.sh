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
    SKIP_TESTS=true
    DEPLOYED_ENV=prod
    DEPLOY_ENV=prod
    doit deploy
    ;;
*)
    echo "No DEPLOY_ENV to set."
    ;;
esac
