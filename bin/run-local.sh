#!/usr/bin/env bash

command -v git >/dev/null 2>&1 || {
    echo >&2 "git is required not installed.  Aborting.";
    exit 1;
}

function cleanup {
  docker-compose down
}

readonly REPO_ROOT="$(git rev-parse --show-toplevel)"
readonly ENV_NAME="venv"
readonly REQUIREMENTS=("${REPO_ROOT}/automation_requirements.txt" "${REPO_ROOT}/src/app_requirements.txt" "${REPO_ROOT}/src/test_requirements.txt")
ENTRY_POINT_PATH="$1"

pushd "${REPO_ROOT}"
/usr/bin/python3.7-dbg -m venv "${ENV_NAME}"
pip3 install --upgrade pip
source "${ENV_NAME}/bin/activate"
echo "installing requirements"
for REQUIREMENT in "${REQUIREMENTS[@]}"
do
  echo "installing ${REQUIREMENT}"
  pip install -r "${REQUIREMENT}"
  echo "installed ${REQUIREMENT}"
done
echo "installed requirements"
popd

# Start a dockerized version of DynamoDB
docker-compose up -d dynamodb

# Export required non-configured variables
export BOTO_CONFIG=/dev/null
export AWS_SECRET_ACCESS_KEY=foobar_secret
export AWS_ACCESS_KEY_ID=foobar_key
export DYNALITE_URL=http://0.0.0.0:8000

# Load the environment
env $(cat ${REPO_ROOT}/.env | xargs)

# Generate AWS credentials for the boto library
sh "${REPO_ROOT}/bin/aws-credentials.sh"

pushd "${REPO_ROOT}/src"
export PYTHONPATH=.
python3 "${ENTRY_POINT_PATH}"
popd

trap cleanup EXIT
