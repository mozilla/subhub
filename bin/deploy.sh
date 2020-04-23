#!/usr/bin/env bash

unset DEPLOYED_ENV

if [[ $TRAVIS_EVENT_TYPE == cron ]]; then
  exit 1;
fi

case "$TRAVIS_BRANCH" in
'feature/staging')
    DEPLOYED_ENV="stage" doit deploy
    echo "deployed ${DEPLOYED_ENV}";
    exit 1;
    ;;
'release/prod-test')
    DEPLOY_ENV="prod-test" doit deploy
    echo "deployed ${DEPLOYED_ENV}";
    exit 1;
    ;;
'release/prod')
    DEPLOY_ENV="prod" doit deploy
    echo "deployed ${DEPLOYED_ENV}";
    exit 1;
    ;;
*)
    tox
    echo "Not deploying."
    ;;
esac