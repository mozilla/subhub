#!/usr/bin/env bash

unset DEPLOYED_ENV

if [[ $TRAVIS_EVENT_TYPE == cron ]]; then
  exit 1;
fi

case "$TRAVIS_BRANCH" in
'feature/staging')
    DEPLOYED_ENV="stage" doit deploy
    ;;
'release/prod-test')
    DEPLOY_ENV="prod-test" doit deploy
    ;;
'release/prod')
    DEPLOY_ENV="prod" doit deploy
    ;;
*)
    echo "No DEPLOY_ENV to set."
    ;;
esac

if [ -z "$DEPLOY_ENV" ]; then
      echo "Not deployinng"
else
      echo "Deployed to $DEPLOY_ENV"
fi