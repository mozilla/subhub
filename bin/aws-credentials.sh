#!/usr/bin/env bash

# NOTE: This script is used to provision both TravisCI and Jenkins, AWS credentials and configuration
# Reference AWS Environment Variables
#   https://docs.aws.amazon.com/codebuild/latest/userguide/build-env-ref-env-vars.html

mkdir -p ~/.aws

cat > ~/.aws/credentials << EOL
[default]
aws_access_key_id = ${AWS_ACCESS_KEY_ID:-fake-id}
aws_secret_access_key = ${AWS_SECRET_ACCESS_KEY:-fake-key}
EOL

cat >~/.aws/config <<-EOF
[default]
output=json
region=${AWS_DEFAULT_REGION:-us-west-2}
EOF