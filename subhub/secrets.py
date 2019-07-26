#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

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
    os.environ.update(get_secret(f"{CFG.DEPLOYED_ENV}/{CFG.PROJECT_NAME}"))
