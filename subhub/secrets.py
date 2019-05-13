import os
import boto3
import base64
import json

from subhub.cfg import CFG


def get_secret(secret_id):
    """Fetch secret via boto3."""
    client = boto3.client(service_name="secretsmanager")
    get_secret_value_response = client.get_secret_value(SecretId=secret_id)

    if "SecretString" in get_secret_value_response:
        secret = get_secret_value_response["SecretString"]
        return json.loads(secret)
    else:
        decoded_binary_secret = base64.b64decode(
            get_secret_value_response["SecretBinary"]
        )
        return decoded_binary_secret

if CFG("AWS_EXECUTION_ENV", None):
    os.environ.update(get_secret(f'{CFG.APP_DEPENV}/{CFG.APP_PROJNAME}'))
