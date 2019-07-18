import os
import boto3
import base64
import json

from subhub.cfg import CFG
from subhub.exceptions import SecretStringMissingError


def get_secret(secret_id):
    """Fetch secret via boto3."""
    client = boto3.client(service_name="secretsmanager")
    get_secret_value_response = client.get_secret_value(SecretId=secret_id)

    if "SecretString" in get_secret_value_response:
        secret = get_secret_value_response["SecretString"]
        return json.loads(secret)
    raise SecretStringMissingError(secret)


if CFG.AWS_EXECUTION_ENV:
    os.environ.update(get_secret(f"{CFG.DEPLOY_ENV}/{CFG.PROJECT_NAME}"))
