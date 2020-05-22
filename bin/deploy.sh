#!/usr/bin/env bash

if [[ $TRAVIS_EVENT_TYPE == cron ]]; then
  exit 1;
fi

case "$TRAVIS_BRANCH" in
'release/prod-test')
    SKIP_TEST=true DEPLOYED_ENV=prod-test doit deploy
    ;;
'release/prod')
    SKIP_TEST=true DEPLOYED_ENV=prod doit deploy
    ;;
*)
    echo "No DEPLOY_ENV to set."
    ;;
esac
